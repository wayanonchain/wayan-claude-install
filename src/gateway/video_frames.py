"""Keyframe extraction from videos via ffmpeg, for Claude vision analysis.

Design constraints (low-RAM VPS, minimal-storage policy):
- A small number of frames (VIDEO_FRAMES, default 5) is extracted per video.
- Each frame is grabbed with its own short `ffmpeg -ss <t> -i <file>` call
  (fast seek, decodes a single frame) so peak memory stays tiny regardless of
  video size.
- Frames are downscaled (VIDEO_FRAME_MAX_WIDTH) and JPEG-compressed
  (VIDEO_FRAME_JPEG_QUALITY) before Claude sees them.
- Frames are written to a per-video temporary directory which the caller MUST
  delete after analysis (see Gateway._finalize_upload); they are never part of
  long-term storage.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time

from .config import Config

log = logging.getLogger("frames")

# `Duration: 00:01:23.45` line printed by ffmpeg on stderr for any input.
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})(?:\.(\d+))?")

# Fallback sample offsets (seconds) when the duration cannot be determined.
# Seeks past EOF simply produce no frame, so long offsets are safe.
_FALLBACK_OFFSETS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 60.0, 120.0)


class FrameExtractionError(Exception):
    """Raised when no frames could be extracted from a video."""


def resolve_ffmpeg(cfg: Config) -> str | None:
    """Return a usable ffmpeg executable path, or None if unavailable.

    FFMPEG_PATH is honoured first; otherwise PATH is searched.
    """
    if cfg.ffmpeg_path and os.path.isfile(cfg.ffmpeg_path) \
            and os.access(cfg.ffmpeg_path, os.X_OK):
        return cfg.ffmpeg_path
    return shutil.which("ffmpeg")


def _probe_duration(ffmpeg: str, video_path: str, timeout: float) -> float | None:
    """Parse the input duration (seconds) from ffmpeg's stderr banner."""
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", video_path],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("ffmpeg duration probe failed for %s: %s", video_path, exc)
        return None
    m = _DURATION_RE.search(proc.stderr or "")
    if not m:
        return None
    h, mnt, s, frac = m.group(1), m.group(2), m.group(3), m.group(4) or "0"
    return int(h) * 3600 + int(mnt) * 60 + int(s) + float(f"0.{frac}")


def _jpeg_qscale(quality: int) -> int:
    """Map a 1-100 JPEG quality to ffmpeg's -q:v scale (2 best .. 31 worst)."""
    quality = max(1, min(100, quality))
    return max(2, min(31, round(31 - (quality / 100.0) * 29)))


def extract_frames(video_path: str, out_dir: str, cfg: Config) -> list[str]:
    """Extract up to cfg.video_frames evenly-spaced JPEG frames from a video.

    Returns the list of frame paths (at least one). Raises
    FrameExtractionError if ffmpeg is unavailable or zero frames came out —
    callers must handle that explicitly (no silent failure).
    """
    ffmpeg = resolve_ffmpeg(cfg)
    if not ffmpeg:
        raise FrameExtractionError(
            "ffmpeg not found (set FFMPEG_PATH or install ffmpeg)")
    if not os.path.isfile(video_path):
        raise FrameExtractionError(f"video file not found: {video_path}")

    n_frames = max(1, min(10, cfg.video_frames))  # hard cap for low-RAM VPS
    deadline = time.monotonic() + max(5, cfg.video_frame_extraction_timeout_sec)

    duration = _probe_duration(
        ffmpeg, video_path, timeout=max(5.0, deadline - time.monotonic()))
    if duration and duration > 0:
        # Midpoints of N equal segments: avoids black first/last frames.
        offsets = [duration * (i + 0.5) / n_frames for i in range(n_frames)]
    else:
        log.warning("could not determine duration of %s; using fixed offsets",
                    video_path)
        offsets = list(_FALLBACK_OFFSETS[:n_frames])

    os.makedirs(out_dir, exist_ok=True)
    scale = f"scale='min({cfg.video_frame_max_width},iw)':-2"
    qscale = str(_jpeg_qscale(cfg.video_frame_jpeg_quality))

    frames: list[str] = []
    for i, off in enumerate(offsets, start=1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            log.warning("frame extraction budget exhausted after %d/%d frames",
                        len(frames), n_frames)
            break
        dest = os.path.join(out_dir, f"frame_{i:02d}.jpg")
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
               "-ss", f"{off:.2f}", "-i", video_path,
               "-frames:v", "1", "-vf", scale, "-q:v", qscale, dest]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=remaining)
        except subprocess.TimeoutExpired:
            log.warning("ffmpeg timed out extracting frame %d (offset %.1fs)",
                        i, off)
            continue
        except OSError as exc:
            raise FrameExtractionError(f"ffmpeg failed to start: {exc}") from exc
        if proc.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 0:
            frames.append(dest)
        else:
            # Seek past EOF or decode hiccup on one offset is not fatal.
            err = (proc.stderr or "").strip()
            log.info("no frame at offset %.1fs (rc=%d) %s", off, proc.returncode,
                     err[:200])
            if os.path.isfile(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass

    if not frames:
        raise FrameExtractionError(
            "ffmpeg produced no frames (corrupt video, unsupported codec, or "
            "extraction timeout)")
    log.info("extracted %d frame(s) from %s into %s",
             len(frames), os.path.basename(video_path), out_dir)
    return frames


def cleanup_frames_dir(frames_dir: str) -> None:
    """Remove a temporary frames directory; never raises."""
    try:
        shutil.rmtree(frames_dir)
        log.info("removed frames dir %s", frames_dir)
    except FileNotFoundError:
        pass
    except OSError as exc:
        log.warning("could not remove frames dir %s: %s", frames_dir, exc)
