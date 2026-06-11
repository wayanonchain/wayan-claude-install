"""Unit tests for gateway.video_frames (no ffmpeg or network required).

Run from the repo root:

    PYTHONPATH=src python -m unittest tests.test_video_frames -v
"""
import os
import tempfile
import unittest
from dataclasses import replace

# Base env so load_config() succeeds (mirrors test_gateway.py).
os.environ.update({
    "TELEGRAM_BOT_TOKEN": "test:token",
    "WAYAN_AGENT": "jupiter",
    "WAYAN_WORKSPACE": "/tmp",
})

from gateway.config import load_config                      # noqa: E402
from gateway.video_frames import (                          # noqa: E402
    FrameExtractionError,
    _jpeg_qscale,
    _DURATION_RE,
    cleanup_frames_dir,
    extract_frames,
    resolve_ffmpeg,
)


def make_cfg(**overrides):
    cfg = load_config()
    return replace(cfg, **overrides) if overrides else cfg


class ConfigDefaultsTests(unittest.TestCase):
    """Visual analysis must be OFF by default (legacy audio-only path)."""

    def test_defaults(self):
        cfg = make_cfg()
        self.assertFalse(cfg.video_visual_analysis)
        self.assertEqual(cfg.video_frames, 5)
        self.assertEqual(cfg.video_frame_max_width, 768)
        self.assertEqual(cfg.video_frame_jpeg_quality, 75)
        self.assertFalse(cfg.video_frame_debug_keep)


class JpegQscaleTests(unittest.TestCase):
    def test_bounds(self):
        # ffmpeg -q:v range is 2 (best) .. 31 (worst).
        self.assertEqual(_jpeg_qscale(100), 2)
        self.assertEqual(_jpeg_qscale(1), 31)

    def test_clamps_out_of_range(self):
        self.assertEqual(_jpeg_qscale(500), 2)
        self.assertEqual(_jpeg_qscale(-5), 31)

    def test_monotonic(self):
        self.assertLessEqual(_jpeg_qscale(75), _jpeg_qscale(25))


class DurationRegexTests(unittest.TestCase):
    def test_parses_ffmpeg_banner(self):
        m = _DURATION_RE.search("  Duration: 00:01:23.45, start: 0.0")
        self.assertIsNotNone(m)
        h, mnt, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        self.assertEqual((h, mnt, s), (0, 1, 23))

    def test_no_match_on_noise(self):
        self.assertIsNone(_DURATION_RE.search("Stream #0:0 Video: h264"))


class ResolveFfmpegTests(unittest.TestCase):
    def test_explicit_path_honoured(self):
        # Use a known-executable file as a stand-in binary.
        cfg = make_cfg(ffmpeg_path="/bin/sh")
        self.assertEqual(resolve_ffmpeg(cfg), "/bin/sh")

    def test_missing_explicit_path_falls_back_to_which(self):
        cfg = make_cfg(ffmpeg_path="/nonexistent/ffmpeg")
        # Result is whatever PATH yields (possibly None) — must not raise.
        resolve_ffmpeg(cfg)


class ExtractFramesErrorTests(unittest.TestCase):
    def test_raises_when_ffmpeg_missing(self):
        cfg = make_cfg(ffmpeg_path="/nonexistent/ffmpeg")
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/nonexistent"          # hide any real ffmpeg
        try:
            with tempfile.TemporaryDirectory() as td:
                video = os.path.join(td, "v.mp4")
                with open(video, "wb") as fh:
                    fh.write(b"\x00")
                with self.assertRaises(FrameExtractionError):
                    extract_frames(video, os.path.join(td, "frames"), cfg)
        finally:
            os.environ["PATH"] = old_path

    def test_raises_when_video_missing(self):
        cfg = make_cfg(ffmpeg_path="/bin/sh")  # "ffmpeg" resolves; file doesn't
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FrameExtractionError):
                extract_frames(os.path.join(td, "missing.mp4"),
                               os.path.join(td, "frames"), cfg)


class CleanupTests(unittest.TestCase):
    def test_removes_dir_with_frames(self):
        with tempfile.TemporaryDirectory() as td:
            frames = os.path.join(td, "x.mp4.frames")
            os.makedirs(frames)
            with open(os.path.join(frames, "frame_01.jpg"), "wb") as fh:
                fh.write(b"jpg")
            cleanup_frames_dir(frames)
            self.assertFalse(os.path.exists(frames))

    def test_missing_dir_never_raises(self):
        cleanup_frames_dir("/nonexistent/frames-dir")


if __name__ == "__main__":
    unittest.main()
