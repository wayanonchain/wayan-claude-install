"""Unit tests for the Wayan gateway.

Run from the repo root with the gateway on the path:

    PYTHONPATH=src python -m unittest discover -s tests -v

Network is never touched: the Telegram client and Groq transcription are faked.
"""
import os
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


if __name__ == "__main__":
    unittest.main()
