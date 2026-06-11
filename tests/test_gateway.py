"""Unit tests for the Wayan gateway.

Run from the repo root with the gateway on the path:

    PYTHONPATH=src python -m unittest discover -s tests -v

Network is never touched: the Telegram client and Groq transcription are faked.
"""
import os
import tempfile
import unittest
from dataclasses import replace

# Base env so load_config() succeeds; individual tests override via replace().
os.environ.update({
    "TELEGRAM_BOT_TOKEN": "test:token",
    "WAYAN_AGENT": "jupiter",
    "WAYAN_WORKSPACE": "/tmp",
})

from gateway import app as appmod                       # noqa: E402
from gateway.app import Gateway                         # noqa: E402
from gateway.config import load_config                  # noqa: E402
from gateway.telegram_api import split_message          # noqa: E402
from gateway import link_ingest as link_ingest_mod        # noqa: E402
from gateway import transcribe as transcribe_mod          # noqa: E402
from gateway.transcribe import transcribe, TranscriptionError  # noqa: E402


def make_cfg(**overrides):
    cfg = load_config()
    return replace(cfg, **overrides) if overrides else cfg


class FakeTelegram:
    def __init__(self):
        self.sent = []
        self.actions = []
        self.docs = []
        self.get_file_calls = []
        self.file_info = {"file_path": "voice/file_123.oga"}
        self.audio = b"OGG-AUDIO-BYTES"

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))

    def send_document(self, chat_id, file_path, caption=None):
        self.docs.append((chat_id, os.path.basename(file_path)))
        return {"ok": True}

    def send_chat_action(self, chat_id, action="typing"):
        self.actions.append((chat_id, action))

    def get_file(self, file_id):
        self.get_file_calls.append(file_id)
        return self.file_info

    def download_file(self, file_path):
        return self.audio


def make_gateway(cfg, tg=None):
    gw = Gateway(cfg)
    gw.tg = tg or FakeTelegram()
    return gw


class SplitMessageTests(unittest.TestCase):
    def test_short(self):
        self.assertEqual(split_message("hello"), ["hello"])

    def test_long_prefers_newline(self):
        parts = split_message("a" * 3000 + "\n" + "b" * 3000)
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(len(p) <= 4096 for p in parts))

    def test_hard_split(self):
        parts = split_message("x" * 5000)
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(len(p) <= 4096 for p in parts))


class VoiceConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = make_cfg()
        self.assertTrue(cfg.voice_enabled)
        self.assertTrue(cfg.voice_input)
        self.assertFalse(cfg.voice_output)
        self.assertFalse(cfg.voice_input_ready)  # no key yet

    def test_ready_requires_key(self):
        self.assertTrue(make_cfg(groq_api_key="k").voice_input_ready)
        self.assertFalse(make_cfg(groq_api_key="k", voice_input=False).voice_input_ready)
        self.assertFalse(make_cfg(groq_api_key="k", voice_enabled=False).voice_input_ready)


class TranscribeTests(unittest.TestCase):
    def test_missing_key(self):
        with self.assertRaises(TranscriptionError):
            transcribe(b"x", "a.ogg", make_cfg(groq_api_key=""))

    def test_empty_audio(self):
        with self.assertRaises(TranscriptionError):
            transcribe(b"", "a.ogg", make_cfg(groq_api_key="k"))


class GroqUploadFilenameTests(unittest.TestCase):
    """The Groq 400 bug: Telegram '.oga' must be sent to Groq as '.ogg'."""

    class _FakeResp:
        status_code = 200
        text = "ok"

        def json(self):
            return {"text": "hi"}

    def _capture_post(self, input_filename):
        captured = {}

        def fake_post(url, headers=None, files=None, data=None, timeout=None):
            captured["files"] = files
            captured["data"] = data
            return self._FakeResp()

        orig = transcribe_mod.requests.post
        transcribe_mod.requests.post = fake_post
        try:
            out = transcribe(b"AUDIO-BYTES", input_filename, make_cfg(groq_api_key="k"))
        finally:
            transcribe_mod.requests.post = orig
        return out, captured

    def test_oga_becomes_ogg(self):
        out, captured = self._capture_post("file_123.oga")
        self.assertEqual(out, "hi")
        name, _bytes, content_type = captured["files"]["file"]
        self.assertTrue(name.endswith(".ogg"), name)
        self.assertEqual(content_type, "audio/ogg")
        self.assertEqual(captured["data"]["model"], make_cfg(groq_api_key="k").groq_model)

    def test_no_extension_becomes_ogg(self):
        _out, captured = self._capture_post("file_456")
        name, _bytes, content_type = captured["files"]["file"]
        self.assertEqual(name, "voice.ogg")
        self.assertEqual(content_type, "audio/ogg")

    def test_accepted_extension_preserved(self):
        _out, captured = self._capture_post("note.mp3")
        name, _bytes, content_type = captured["files"]["file"]
        self.assertEqual(name, "note.mp3")
        self.assertEqual(content_type, "audio/mpeg")


class VoiceRoutingTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_transcribe = appmod.transcribe
        self._orig_run = appmod.run_claude

    def tearDown(self):
        appmod.transcribe = self._orig_transcribe
        appmod.run_claude = self._orig_run

    def _cfg(self, **over):
        return make_cfg(workspace=self.ws, **over)

    def test_voice_disabled(self):
        gw = make_gateway(self._cfg(voice_enabled=False, groq_api_key="k"))
        self.assertIsNone(gw._transcribe_voice(1, {"file_id": "f"}))
        self.assertTrue(any("disabled" in t for _, t in gw.tg.sent))

    def test_voice_no_key(self):
        gw = make_gateway(self._cfg(groq_api_key=""))
        self.assertIsNone(gw._transcribe_voice(1, {"file_id": "f"}))
        self.assertTrue(any("GROQ_API_KEY" in t for _, t in gw.tg.sent))

    def test_voice_happy_path(self):
        appmod.transcribe = lambda audio, name, cfg: "hello world"
        gw = make_gateway(self._cfg(groq_api_key="k"))
        result = gw._transcribe_voice(1, {"file_id": "f"})
        self.assertEqual(result, "hello world")
        self.assertTrue(any("hello world" in t for _, t in gw.tg.sent))  # echoed

    def test_voice_routes_into_claude(self):
        captured = {}

        def fake_run(text, cfg, continue_session):
            captured["prompt"] = text
            return "done"

        appmod.transcribe = lambda audio, name, cfg: "do the thing"
        appmod.run_claude = fake_run
        gw = make_gateway(self._cfg(groq_api_key="k"))
        gw._handle_message({"chat": {"id": 1}, "voice": {"file_id": "f"}})
        self.assertEqual(captured["prompt"], "do the thing")
        self.assertIn((1, "done"), gw.tg.sent)

    def test_text_still_works(self):
        captured = {}

        def fake_run(text, cfg, continue_session):
            captured["prompt"] = text
            return "ok"

        appmod.run_claude = fake_run
        gw = make_gateway(self._cfg())
        gw._handle_message({"chat": {"id": 1}, "text": "hi there"})
        self.assertEqual(captured["prompt"], "hi there")
        self.assertIn((1, "ok"), gw.tg.sent)


class FileHandlingTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self.cfg = make_cfg(workspace=self.ws)
        self._orig_run = appmod.run_claude

    def tearDown(self):
        appmod.run_claude = self._orig_run

    def test_largest_photo(self):
        photos = [{"file_id": "a", "file_unique_id": "ua"},
                  {"file_id": "b", "file_unique_id": "ub"}]
        att = Gateway._largest_photo(photos)
        self.assertEqual(att["file_id"], "b")
        self.assertTrue(att["file_name"].endswith(".jpg"))
        self.assertIsNone(Gateway._largest_photo(None))

    def test_safe_filename(self):
        name = Gateway._safe_filename("../../etc/pa ss?wd.txt")
        self.assertNotIn("/", name)
        self.assertNotIn("?", name)
        self.assertTrue(name.endswith("pa ss_wd.txt"))

    def test_document_saved_and_prompted(self):
        gw = make_gateway(self.cfg)
        gw.tg.file_info = {"file_path": "documents/report.pdf"}
        prompt = gw._handle_file(
            1, {"file_id": "f", "file_name": "report.pdf"}, "Проверь отчёт")
        # file written into <workspace>/uploads/tmp
        uploads = os.path.join(self.ws, "uploads", "tmp")
        files = os.listdir(uploads)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("report.pdf"))
        # prompt carries the caption (task) and the saved path
        self.assertIn("Проверь отчёт", prompt)
        self.assertIn(uploads, prompt)
        # an ack was sent
        self.assertTrue(any("Файл получен" in t for _, t in gw.tg.sent))

    def test_no_caption_uses_default_task(self):
        gw = make_gateway(self.cfg)
        prompt = gw._handle_file(1, {"file_id": "f", "file_name": "data.csv"}, "")
        self.assertIn("Analyze the uploaded file", prompt)

    def test_prompt_has_explicit_read_instruction(self):
        gw = make_gateway(self.cfg)
        prompt = gw._handle_file(
            1, {"file_id": "f", "file_name": "report.pdf"}, "Summarize this document")
        # Deterministic read-then-act contract
        self.assertIn("Task:", prompt)
        self.assertIn("Summarize this document", prompt)
        self.assertIn("You MUST first read and inspect the file located at:", prompt)
        self.assertIn("Only after reading the file, complete the requested task.", prompt)
        self.assertIn("If the file cannot be read, explain why.", prompt)
        # absolute path present
        uploads = os.path.join(self.ws, "uploads", "tmp")
        self.assertTrue(any(uploads in line and line.endswith(".pdf")
                            for line in prompt.splitlines()))

    def test_file_prompt_helper_is_pure(self):
        # Backward-compatible helper usable for documents, images, future types.
        p = Gateway._file_prompt("do X", "/abs/path/img.png")
        self.assertIn("Task:\n\ndo X", p)
        self.assertIn("/abs/path/img.png", p)
        self.assertIn("You MUST first read and inspect the file located at:", p)
        # default task applies when empty
        self.assertIn("Analyze the uploaded file",
                      Gateway._file_prompt("", "/abs/x.bin"))

    def test_file_prompt_has_output_instruction(self):
        gw = make_gateway(self.cfg)
        prompt = gw._handle_file(1, {"file_id": "f", "file_name": "a.txt"}, "do")
        self.assertIn("save them to this directory", prompt)
        self.assertIn(os.path.join(self.ws, "outbox"), prompt)


class OutboxDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self.outbox = os.path.join(self.ws, "outbox")
        os.makedirs(self.outbox, exist_ok=True)
        self.cfg = make_cfg(workspace=self.ws)
        self._orig_run = appmod.run_claude

    def tearDown(self):
        appmod.run_claude = self._orig_run

    def _write(self, name, content="x"):
        with open(os.path.join(self.outbox, name), "w") as fh:
            fh.write(content)

    def test_new_file_delivered(self):
        gw = make_gateway(self.cfg)
        before = gw._outbox_snapshot(self.outbox)   # empty
        self._write("result.csv")
        gw._deliver_outbox(1, self.outbox, before)
        self.assertEqual(gw.tg.docs, [(1, "result.csv")])

    def test_unchanged_not_resent(self):
        self._write("old.txt")
        gw = make_gateway(self.cfg)
        before = gw._outbox_snapshot(self.outbox)   # already contains old.txt
        gw._deliver_outbox(1, self.outbox, before)
        self.assertEqual(gw.tg.docs, [])

    def test_text_task_produces_file(self):
        def fake_run(text, cfg, continue_session):
            with open(os.path.join(self.outbox, "report.md"), "w") as fh:
                fh.write("# report")
            return "готово"

        appmod.run_claude = fake_run
        gw = make_gateway(self.cfg)
        gw._handle_message({"chat": {"id": 7}, "text": "сделай отчёт файлом"})
        self.assertIn((7, "готово"), gw.tg.sent)
        self.assertIn((7, "report.md"), gw.tg.docs)

    def test_files_disabled(self):
        gw = make_gateway(replace(self.cfg, files_enabled=False))
        self.assertIsNone(gw._handle_file(1, {"file_id": "f"}, ""))
        self.assertTrue(any("disabled" in t for _, t in gw.tg.sent))

    def test_file_too_large(self):
        gw = make_gateway(replace(self.cfg, file_max_mb=1))
        att = {"file_id": "f", "file_name": "big.bin", "file_size": 5 * 1024 * 1024}
        self.assertIsNone(gw._handle_file(1, att, ""))
        self.assertTrue(any("слишком большой" in t for _, t in gw.tg.sent))

    def test_document_routes_into_claude(self):
        captured = {}

        def fake_run(text, cfg, continue_session):
            captured["prompt"] = text
            return "ok"

        appmod.run_claude = fake_run
        gw = make_gateway(self.cfg)
        gw._handle_message({
            "chat": {"id": 1},
            "document": {"file_id": "f", "file_name": "x.txt"},
            "caption": "do it",
        })
        self.assertIn("do it", captured["prompt"])
        self.assertIn("uploads", captured["prompt"])
        self.assertIn((1, "ok"), gw.tg.sent)


class StorageTests(unittest.TestCase):
    """Minimal-storage policy: temporary raw uploads, Markdown transcripts."""

    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_transcribe = appmod.transcribe
        self._orig_run = appmod.run_claude

    def tearDown(self):
        appmod.transcribe = self._orig_transcribe
        appmod.run_claude = self._orig_run

    def _ls(self, *parts):
        d = os.path.join(self.ws, *parts)
        return os.listdir(d) if os.path.isdir(d) else []

    def _read_only_md(self, subdir="transcripts"):
        d = os.path.join(self.ws, subdir)
        mds = [f for f in os.listdir(d) if f.endswith(".md")] if os.path.isdir(d) else []
        self.assertEqual(len(mds), 1, f"expected exactly one .md in {subdir}, got {mds}")
        with open(os.path.join(d, mds[0]), encoding="utf-8") as fh:
            return fh.read()

    def test_voice_writes_transcript_and_deletes_raw(self):
        appmod.transcribe = lambda audio, name, cfg: "hello from voice"
        gw = make_gateway(make_cfg(workspace=self.ws, groq_api_key="k",
                                   file_keep_original=False))
        out = gw._transcribe_voice(1, {"file_id": "f"}, message_id=42)
        self.assertEqual(out, "hello from voice")
        body = self._read_only_md()
        self.assertIn("hello from voice", body)
        self.assertIn("Telegram message id: 42", body)
        self.assertIn("Provider/model: groq:", body)
        self.assertIn("Agent: jupiter", body)
        self.assertEqual(self._ls("uploads", "tmp"), [])  # raw deleted

    def test_voice_keep_original_retains_raw(self):
        appmod.transcribe = lambda audio, name, cfg: "kept"
        gw = make_gateway(make_cfg(workspace=self.ws, groq_api_key="k",
                                   file_keep_original=True))
        gw._transcribe_voice(1, {"file_id": "f"}, message_id=1)
        self.assertEqual(len(self._ls("uploads", "tmp")), 1)  # raw kept

    def test_document_writes_transcript_and_deletes_raw(self):
        appmod.run_claude = lambda text, cfg, continue_session: "doc analysis result"
        gw = make_gateway(make_cfg(workspace=self.ws, file_keep_original=False))
        gw._handle_message({
            "chat": {"id": 5},
            "document": {"file_id": "f", "file_name": "report.pdf"},
            "caption": "summarize",
            "message_id": 99,
        })
        body = self._read_only_md()
        self.assertIn("doc analysis result", body)
        self.assertIn("claude -p", body)
        self.assertIn("report.pdf", body)
        self.assertEqual(self._ls("uploads", "tmp"), [])  # raw deleted

    def test_transcripts_disabled_still_deletes_raw(self):
        appmod.transcribe = lambda audio, name, cfg: "x"
        gw = make_gateway(make_cfg(workspace=self.ws, groq_api_key="k",
                                   transcripts_enabled=False,
                                   file_keep_original=False))
        gw._transcribe_voice(1, {"file_id": "f"})
        self.assertEqual([f for f in self._ls("transcripts") if f.endswith(".md")], [])
        self.assertEqual(self._ls("uploads", "tmp"), [])


MB = 1024 * 1024


class UploadSafetyTests(unittest.TestCase):
    """Two-step upload gate: static type limit + disk availability + confirm."""

    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_run = appmod.run_claude
        self._orig_transcribe = appmod.transcribe
        appmod.run_claude = lambda text, cfg, continue_session: "ok"
        appmod.transcribe = lambda audio, name, cfg: "transcribed"

    def tearDown(self):
        appmod.run_claude = self._orig_run
        appmod.transcribe = self._orig_transcribe

    def _gw(self, free_mb=100000, **over):
        gw = make_gateway(make_cfg(workspace=self.ws, **over))
        gw._free_mb = lambda: free_mb
        return gw

    @staticmethod
    def _doc(size_mb, name="report.pdf", mime="application/pdf"):
        return {"file_id": "f", "file_name": name, "mime_type": mime,
                "file_size": int(size_mb * MB)}

    def test_small_file_processes_immediately(self):
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(2),
                            "caption": "do it", "message_id": 1})
        self.assertIn((1, "ok"), gw.tg.sent)                 # processed
        self.assertEqual(gw.tg.get_file_calls, ["f"])        # downloaded
        self.assertNotIn(1, gw._pending_confirmations)       # no pending

    def test_telegram_oversized_suggests_link(self):
        # > Telegram's 20 MB download cap -> tell the user to send a link.
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(30),
                            "message_id": 7})
        self.assertTrue(any("send a direct link" in t for _, t in gw.tg.sent))
        self.assertEqual(gw.tg.get_file_calls, [])
        self.assertNotIn(1, gw._pending_confirmations)

    def test_large_file_asks_for_confirmation(self):
        # 10 MB file with a 5 MB confirm threshold (below the Telegram cap).
        gw = self._gw(free_mb=100000, large_file_confirm_mb=5)
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(10),
                            "caption": "x", "message_id": 7})
        self.assertTrue(any("Large file detected" in t for _, t in gw.tg.sent))
        self.assertIn(1, gw._pending_confirmations)          # pending stored
        self.assertEqual(gw.tg.get_file_calls, [])           # NOT downloaded

    def test_process_file_continues(self):
        gw = self._gw(free_mb=100000, large_file_confirm_mb=5)
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(10),
                            "caption": "x", "message_id": 7})
        gw._handle_message({"chat": {"id": 1}, "text": "PROCESS FILE",
                            "message_id": 8})
        self.assertIn((1, "ok"), gw.tg.sent)                 # processed after confirm
        self.assertEqual(gw.tg.get_file_calls, ["f"])        # downloaded now
        self.assertNotIn(1, gw._pending_confirmations)       # cleared

    def test_expired_pending_does_not_process(self):
        gw = self._gw(free_mb=100000, large_file_confirm_mb=5)
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(10),
                            "message_id": 7})
        gw._pending_confirmations[1]["created_at"] -= (
            gw.cfg.upload_confirmation_timeout_min * 60 + 5)
        gw._handle_message({"chat": {"id": 1}, "text": "PROCESS FILE"})
        self.assertTrue(any("expired" in t.lower() for _, t in gw.tg.sent))
        self.assertEqual(gw.tg.get_file_calls, [])           # never downloaded

    def test_file_above_limit_rejected(self):
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1},
                            "video": {"file_id": "v", "file_size": int(684 * MB)},
                            "message_id": 9})
        self.assertTrue(any("File too large" in t for _, t in gw.tg.sent))
        self.assertEqual(gw.tg.get_file_calls, [])           # not downloaded
        self.assertNotIn(1, gw._pending_confirmations)

    def test_insufficient_disk_rejected(self):
        gw = self._gw(free_mb=100, large_file_confirm_mb=5)  # below required for 10 MB
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(10),
                            "message_id": 7})
        self.assertTrue(any("Not enough disk space" in t for _, t in gw.tg.sent))
        self.assertEqual(gw.tg.get_file_calls, [])
        self.assertNotIn(1, gw._pending_confirmations)

    def test_disk_rechecked_after_confirmation(self):
        gw = self._gw(free_mb=100000, large_file_confirm_mb=5)
        gw._handle_message({"chat": {"id": 1}, "document": self._doc(10),
                            "message_id": 7})
        self.assertIn(1, gw._pending_confirmations)
        gw._free_mb = lambda: 100  # disk filled up before confirmation
        gw._handle_message({"chat": {"id": 1}, "text": "PROCESS FILE"})
        self.assertTrue(any("Not enough disk space" in t for _, t in gw.tg.sent))
        self.assertEqual(gw.tg.get_file_calls, [])           # blocked on recheck


class LinkIngestTests(unittest.TestCase):
    """Large-file ingestion from URLs (direct files + yt-dlp gating + SSRF)."""

    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_run = appmod.run_claude
        self._orig_transcribe = appmod.transcribe
        self._orig_head = link_ingest_mod.head_probe
        self._orig_stream = link_ingest_mod.stream_download
        appmod.run_claude = lambda text, cfg, continue_session: "ok"
        appmod.transcribe = lambda audio, name, cfg: "link transcript"

    def tearDown(self):
        appmod.run_claude = self._orig_run
        appmod.transcribe = self._orig_transcribe
        link_ingest_mod.head_probe = self._orig_head
        link_ingest_mod.stream_download = self._orig_stream

    def _gw(self, free_mb=100000, **over):
        gw = make_gateway(make_cfg(workspace=self.ws, **over))
        gw._free_mb = lambda: free_mb
        return gw

    def _fake_head(self, ctype, clen):
        def head(url, max_redirects=5):
            return (url, ctype, clen)
        link_ingest_mod.head_probe = head

    def _fake_stream(self, nbytes, hard_cap_error=False):
        def stream(url, dest, max_bytes, max_redirects=5):
            if hard_cap_error:
                raise link_ingest_mod.LinkError("exceeded max bytes")
            with open(dest, "wb") as fh:
                fh.write(b"x" * min(nbytes, 1024))
            return url, nbytes
        link_ingest_mod.stream_download = stream

    # public IP literal → no DNS lookup, passes SSRF check
    URL_VID = "http://93.184.216.34/clip.mp4"
    URL_DOC = "http://93.184.216.34/report.pdf"

    def test_direct_small_url_processes(self):
        self._fake_head("application/pdf", 2 * MB)
        self._fake_stream(2 * MB)
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1}, "text": f"summarize {self.URL_DOC}",
                            "message_id": 1})
        self.assertIn((1, "ok"), gw.tg.sent)            # processed through Claude
        self.assertNotIn(1, gw._pending_links)

    def test_large_url_asks_process_link(self):
        self._fake_head("video/mp4", 180 * MB)          # < 250 video limit, large
        gw = self._gw(free_mb=100000)
        gw._handle_message({"chat": {"id": 1}, "text": self.URL_VID, "message_id": 1})
        self.assertTrue(any("Large link detected" in t for _, t in gw.tg.sent))
        self.assertIn(1, gw._pending_links)

    def test_process_link_continues(self):
        self._fake_head("video/mp4", 180 * MB)
        self._fake_stream(180 * MB)
        gw = self._gw(free_mb=100000)
        gw._handle_message({"chat": {"id": 1}, "text": self.URL_VID, "message_id": 1})
        gw._handle_message({"chat": {"id": 1}, "text": "PROCESS LINK", "message_id": 2})
        self.assertIn((1, "ok"), gw.tg.sent)            # transcript -> Claude -> reply
        self.assertNotIn(1, gw._pending_links)

    def test_oversized_url_rejected(self):
        self._fake_head("video/mp4", 684 * MB)          # > 250 video limit
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1}, "text": self.URL_VID, "message_id": 1})
        self.assertTrue(any("File too large" in t for _, t in gw.tg.sent))
        self.assertNotIn(1, gw._pending_links)

    def test_missing_content_length_streams_with_guard(self):
        self._fake_head("video/mp4", None)              # unknown size
        self._fake_stream(5 * MB)                       # within cap
        gw = self._gw(free_mb=100000)
        gw._handle_message({"chat": {"id": 1}, "text": self.URL_VID, "message_id": 1})
        self.assertIn((1, "ok"), gw.tg.sent)            # streamed + processed

    def test_private_url_blocked(self):
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1},
                            "text": "http://192.168.1.5/clip.mp4", "message_id": 1})
        self.assertTrue(any("blocked" in t.lower() for _, t in gw.tg.sent))

    def test_unsupported_scheme_blocked(self):
        gw = self._gw()
        gw._handle_message({"chat": {"id": 1},
                            "text": "ftp://1.2.3.4/clip.mp4", "message_id": 1})
        self.assertTrue(any("blocked" in t.lower() for _, t in gw.tg.sent))

    def test_ytdlp_disabled_message(self):
        gw = self._gw(ytdlp_enabled=False)
        gw._handle_message({"chat": {"id": 1},
                            "text": "https://youtu.be/abc123", "message_id": 1})
        self.assertTrue(any("YTDLP_ENABLED" in t for _, t in gw.tg.sent))


class TaskQueueTests(unittest.TestCase):
    """Per-chat queue, instant acks, /queue, /cancel, timeout, video acks.

    The worker thread is NOT started in tests; we drive it via _process_next()
    so the behavior is deterministic.
    """

    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_run = appmod.run_claude
        appmod.run_claude = lambda text, cfg, continue_session: "ok"

    def tearDown(self):
        appmod.run_claude = self._orig_run

    def _gw(self, **over):
        gw = make_gateway(make_cfg(workspace=self.ws, **over))
        gw._free_mb = lambda: 100000
        return gw

    @staticmethod
    def _txt(chat_id, text, mid=1):
        return {"chat": {"id": chat_id}, "text": text, "message_id": mid}

    def test_rapid_messages_acked_with_positions(self):
        gw = self._gw()
        for i, t in enumerate(("task one", "task two", "task three"), 1):
            gw._handle_update(self._txt(1, t, i))
        acks = [t for _, t in gw.tg.sent if "Task received" in t]
        self.assertEqual(len(acks), 3)
        self.assertIn("Queue position: 1", acks[0])
        self.assertIn("Queue position: 2", acks[1])
        self.assertIn("Queue position: 3", acks[2])
        # worker drains in order
        while gw._process_next():
            pass
        replies = [t for _, t in gw.tg.sent if t == "ok"]
        self.assertEqual(len(replies), 3)

    def test_queue_command_reports_pending(self):
        gw = self._gw()
        gw._handle_update(self._txt(1, "a"))
        gw._handle_update(self._txt(1, "b"))
        gw._handle_update(self._txt(1, "/queue"))
        status = [t for _, t in gw.tg.sent if "📋 Queue:" in t]
        self.assertEqual(len(status), 1)
        self.assertIn("2 pending task(s) total, 2 from this chat", status[0])

    def test_cancel_command_drops_pending(self):
        gw = self._gw()
        gw._handle_update(self._txt(1, "a"))
        gw._handle_update(self._txt(1, "b"))
        gw._handle_update(self._txt(1, "/cancel"))
        self.assertTrue(any("Cancelled 2 pending task(s)" in t for _, t in gw.tg.sent))
        self.assertFalse(gw._process_next())   # queue is empty
        self.assertNotIn("ok", [t for _, t in gw.tg.sent])  # nothing ran

    def test_cancel_only_affects_own_chat(self):
        gw = self._gw()
        gw._handle_update(self._txt(1, "mine"))
        gw._handle_update(self._txt(2, "theirs"))
        gw._handle_update(self._txt(1, "/cancel"))
        self.assertTrue(any("Cancelled 1 pending" in t for _, t in gw.tg.sent))
        self.assertTrue(gw._process_next())    # chat 2's task still there
        self.assertIn((2, "ok"), gw.tg.sent)

    def test_timeout_reply_and_continue(self):
        calls = {"n": 0}

        def flaky(text, cfg, continue_session):
            calls["n"] += 1
            if calls["n"] == 1:
                raise appmod.ClaudeError("claude timed out after 300s")
            return "second ok"

        appmod.run_claude = flaky
        gw = self._gw()
        gw._handle_update(self._txt(1, "slow one"))
        gw._handle_update(self._txt(1, "fast one"))
        while gw._process_next():
            pass
        self.assertTrue(any("⏱" in t and "Moving on" in t for _, t in gw.tg.sent))
        self.assertIn((1, "second ok"), gw.tg.sent)  # queue continued

    def test_worker_never_silent_on_crash(self):
        def boom(text, cfg, continue_session):
            raise RuntimeError("unexpected explosion")

        appmod.run_claude = boom
        gw = self._gw()
        gw._handle_update(self._txt(1, "trigger"))
        self.assertTrue(gw._process_next())
        self.assertTrue(any("⚠️ Task failed" in t for _, t in gw.tg.sent))
        self.assertIsNone(gw._current_task)    # state cleared for next task

    def test_unprocessable_update_not_acked(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1}, "sticker": {"file_id": "s"}})
        self.assertEqual(gw.tg.sent, [])       # silent skip, nothing queued


class VideoAckTests(unittest.TestCase):
    """Video / video_note / video-MIME documents must always be acknowledged."""

    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="wayan-ws-")
        self._orig_run = appmod.run_claude
        appmod.run_claude = lambda text, cfg, continue_session: "ok"

    def tearDown(self):
        appmod.run_claude = self._orig_run

    def _gw(self, **over):
        gw = make_gateway(make_cfg(workspace=self.ws, **over))
        gw._free_mb = lambda: 100000
        return gw

    def _assert_video_ack(self, gw):
        self.assertTrue(
            any("🎥 Video received" in t for _, t in gw.tg.sent),
            f"no video ack in {gw.tg.sent}")

    def test_video_message_acked(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1},
                           "video": {"file_id": "v", "file_size": 5 * MB}})
        self._assert_video_ack(gw)

    def test_video_note_acked(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1},
                           "video_note": {"file_id": "v", "file_size": 2 * MB}})
        self._assert_video_ack(gw)

    def test_video_document_acked(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1},
                           "document": {"file_id": "v", "file_name": "clip.mp4",
                                        "mime_type": "video/mp4",
                                        "file_size": 5 * MB}})
        self._assert_video_ack(gw)

    def test_oversized_video_advises_link_after_ack(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1},
                           "video": {"file_id": "v", "file_size": 30 * MB}})
        self._assert_video_ack(gw)             # 1) instant ack
        self.assertTrue(gw._process_next())    # 2) worker gates it
        self.assertTrue(any("send a direct link" in t for _, t in gw.tg.sent))

    def test_video_over_type_limit_rejected_after_ack(self):
        gw = self._gw()
        gw._handle_update({"chat": {"id": 1},
                           "video": {"file_id": "v", "file_size": 684 * MB}})
        self._assert_video_ack(gw)
        self.assertTrue(gw._process_next())
        self.assertTrue(any("File too large" in t for _, t in gw.tg.sent))


if __name__ == "__main__":
    unittest.main()
