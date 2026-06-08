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
from gateway import transcribe as transcribe_mod          # noqa: E402
from gateway.transcribe import transcribe, TranscriptionError  # noqa: E402


def make_cfg(**overrides):
    cfg = load_config()
    return replace(cfg, **overrides) if overrides else cfg


class FakeTelegram:
    def __init__(self):
        self.sent = []
        self.actions = []
        self.file_info = {"file_path": "voice/file_123.oga"}
        self.audio = b"OGG-AUDIO-BYTES"

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))

    def send_chat_action(self, chat_id, action="typing"):
        self.actions.append((chat_id, action))

    def get_file(self, file_id):
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
        self._orig_transcribe = appmod.transcribe
        self._orig_run = appmod.run_claude

    def tearDown(self):
        appmod.transcribe = self._orig_transcribe
        appmod.run_claude = self._orig_run

    def test_voice_disabled(self):
        gw = make_gateway(make_cfg(voice_enabled=False, groq_api_key="k"))
        self.assertIsNone(gw._transcribe_voice(1, {"file_id": "f"}))
        self.assertTrue(any("disabled" in t for _, t in gw.tg.sent))

    def test_voice_no_key(self):
        gw = make_gateway(make_cfg(groq_api_key=""))
        self.assertIsNone(gw._transcribe_voice(1, {"file_id": "f"}))
        self.assertTrue(any("GROQ_API_KEY" in t for _, t in gw.tg.sent))

    def test_voice_happy_path(self):
        appmod.transcribe = lambda audio, name, cfg: "hello world"
        gw = make_gateway(make_cfg(groq_api_key="k"))
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
        gw = make_gateway(make_cfg(groq_api_key="k"))
        gw._handle_message({"chat": {"id": 1}, "voice": {"file_id": "f"}})
        self.assertEqual(captured["prompt"], "do the thing")
        self.assertIn((1, "done"), gw.tg.sent)

    def test_text_still_works(self):
        captured = {}

        def fake_run(text, cfg, continue_session):
            captured["prompt"] = text
            return "ok"

        appmod.run_claude = fake_run
        gw = make_gateway(make_cfg())
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
        # file written into <workspace>/uploads
        uploads = os.path.join(self.ws, "uploads")
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
        uploads = os.path.join(self.ws, "uploads")
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


if __name__ == "__main__":
    unittest.main()
