"""Offline behavior checks; no network calls or dependency installation."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tts.py"
SPEC = importlib.util.spec_from_file_location("skill_tts", SCRIPT)
tts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tts)

AUDIO = b"ID3" + b"sample" * 100
SRT = "1\n00:00:00,100 --> 00:00:01,200\n你好，世界。\n"


class SpeechBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "旁白.mp3"
        self.subtitle = self.root / "captions" / "旁白.srt"

    def args(self, *extra):
        return tts.parse_args([
            "--text", "你好，世界。", "--output", str(self.audio),
            "--subtitles", str(self.subtitle), *extra,
        ])

    def successful_call(self, command, timeout):
        self.assertGreater(timeout, 0)
        self.source_text = Path(command[command.index("--file") + 1]).read_text(
            encoding="utf-8"
        )
        Path(command[command.index("--write-media") + 1]).write_bytes(AUDIO)
        if "--write-subtitles" in command:
            Path(command[command.index("--write-subtitles") + 1]).write_text(
                SRT, encoding="utf-8"
            )
        self.command = command
        return subprocess.CompletedProcess(command, 0, "", "")

    def synthesize(self, args, call=None):
        with patch.object(tts, "run", side_effect=call or self.successful_call):
            with redirect_stdout(io.StringIO()):
                tts.synthesize(Path("/fake/python"), args)

    def assert_no_staging(self):
        self.assertFalse(list(self.root.glob(".edge-tts-*")))
        if self.subtitle.parent.exists():
            self.assertEqual(list(self.subtitle.parent.iterdir()), [self.subtitle])

    def test_success_publishes_audio_and_subtitles_in_separate_directories(self):
        self.synthesize(self.args())
        self.assertEqual(self.audio.read_bytes(), AUDIO)
        self.assertEqual(self.subtitle.read_text(encoding="utf-8"), SRT)
        self.assertIn("zh-CN-YunjianNeural", self.command)
        self.assertIn("--rate=-10%", self.command)
        self.assert_no_staging()

    def test_utf8_bom_file_is_read_without_bom(self):
        source = self.root / "输入.txt"
        source.write_bytes(b"\xef\xbb\xbf" + "带引号的中文：`$()`。".encode("utf-8"))
        args = tts.parse_args(["--file", str(source), "--output", str(self.audio)])
        self.synthesize(args)
        self.assertEqual(self.source_text, "带引号的中文：`$()`。")
        self.assertEqual(self.audio.read_bytes(), AUDIO)
        self.assert_no_staging()

    def test_empty_input_and_invalid_arguments_fail_before_call(self):
        with patch.object(tts, "run") as call:
            with self.assertRaises(ValueError):
                tts.synthesize(Path("/fake/python"), self.args("--text", " \n\t"))
            call.assert_not_called()
        for extra in (["--rate=-0.5%"], ["--pitch=0Hz"], ["--timeout", "0"]):
            with self.subTest(extra=extra), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.args(*extra)
        with self.assertRaises(ValueError):
            self.synthesize(self.args("--output", str(self.root / "wrong.wav")))
        self.assertFalse(self.audio.exists())
        self.assertFalse(self.subtitle.exists())

    def test_existing_outputs_are_not_overwritten_without_flag(self):
        self.audio.write_bytes(b"original audio")
        self.subtitle.parent.mkdir()
        self.subtitle.write_text("original captions", encoding="utf-8")
        with patch.object(tts, "run") as call:
            with self.assertRaises(FileExistsError):
                tts.synthesize(Path("/fake/python"), self.args())
            call.assert_not_called()
        self.assertEqual(self.audio.read_bytes(), b"original audio")
        self.assertEqual(self.subtitle.read_text(), "original captions")
        self.assert_no_staging()

    def test_failed_or_timed_out_call_preserves_original_pair(self):
        self.audio.write_bytes(b"original audio")
        self.subtitle.parent.mkdir()
        self.subtitle.write_text("original captions", encoding="utf-8")
        errors = [subprocess.CalledProcessError(1, "fake", stderr="unavailable"),
                  subprocess.TimeoutExpired("fake", 1)]
        for error in errors:
            def interrupted_call(command, timeout):
                Path(command[command.index("--write-media") + 1]).write_bytes(b"partial")
                Path(command[command.index("--write-subtitles") + 1]).write_text("partial")
                raise error
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(type(error)):
                    self.synthesize(self.args("--overwrite"), interrupted_call)
                self.assertEqual(self.audio.read_bytes(), b"original audio")
                self.assertEqual(self.subtitle.read_text(), "original captions")
                self.assert_no_staging()

    def test_invalid_returned_audio_or_subtitles_are_not_published(self):
        for audio, captions in ((b"", SRT), (AUDIO, "not an SRT")):
            def incomplete_call(command, timeout):
                Path(command[command.index("--write-media") + 1]).write_bytes(audio)
                Path(command[command.index("--write-subtitles") + 1]).write_text(captions)
            with self.subTest(audio_size=len(audio), captions=captions):
                with self.assertRaises(RuntimeError):
                    self.synthesize(self.args(), incomplete_call)
                self.assertFalse(self.audio.exists())
                self.assertFalse(self.subtitle.exists())
                self.assertFalse(list(self.root.glob(".edge-tts-*")))
                self.assertEqual(list(self.subtitle.parent.iterdir()), [])

    def test_audio_publication_failure_restores_previous_subtitle_state(self):
        self.audio.write_bytes(b"original audio")
        self.subtitle.parent.mkdir()
        real_replace = Path.replace

        def fail_audio_publication(path, target):
            if path.name == "audio.mp3":
                raise PermissionError("simulated output target failure")
            return real_replace(path, target)

        for original in (b"original captions", None):
            if original is None:
                self.subtitle.unlink(missing_ok=True)
            else:
                self.subtitle.write_bytes(original)
            with self.subTest(previous_subtitle=original):
                with patch.object(Path, "replace", fail_audio_publication):
                    with self.assertRaises(PermissionError):
                        self.synthesize(self.args("--overwrite"))
                self.assertEqual(self.audio.read_bytes(), b"original audio")
                if original is None:
                    self.assertFalse(self.subtitle.exists())
                    self.assertEqual(list(self.subtitle.parent.iterdir()), [])
                else:
                    self.assertEqual(self.subtitle.read_bytes(), original)
                    self.assertEqual(list(self.subtitle.parent.iterdir()), [self.subtitle])
                self.assertFalse(list(self.root.glob(".edge-tts-*")))


if __name__ == "__main__":
    unittest.main()
