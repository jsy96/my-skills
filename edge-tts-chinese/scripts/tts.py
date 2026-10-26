#!/usr/bin/env python3
"""Isolated Edge TTS CLI with bounded execution and staged MP3/SRT output."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


SKILL_DIR = Path(__file__).resolve().parents[1]
VERSION = "7.3.1"
VOICES = {
    "yunjian": "zh-CN-YunjianNeural",
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "yunxi": "zh-CN-YunxiNeural",
}


def signed_value(pattern, label):
    def parse(value):
        if not re.fullmatch(pattern, value):
            raise argparse.ArgumentTypeError(f"{label}格式不正确；负数请用等号，例如 --rate=-10%")
        return value
    return parse


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--setup", action="store_true", help="创建或复用独立依赖环境")
    actions.add_argument("--list-voices", action="store_true", help="查询在线中文声音")
    actions.add_argument("--text", help="直接输入文字")
    actions.add_argument("--file", type=Path, help="UTF-8 文本文件")
    parser.add_argument("--output", type=Path, help="MP3 输出路径")
    parser.add_argument("--subtitles", type=Path, help="可选 SRT 输出路径")
    parser.add_argument("--voice", default="yunjian", help="音色别名或完整 Voice ID")
    parser.add_argument("--rate", default="-10%", type=signed_value(r"[+-]\d+%", "语速"))
    parser.add_argument("--volume", default="+0%", type=signed_value(r"[+-]\d+%", "音量"))
    parser.add_argument("--pitch", default="+0Hz", type=signed_value(r"[+-]\d+Hz", "音高"))
    parser.add_argument("--timeout", type=int, default=120, help="单次操作总时限（秒）")
    parser.add_argument("--proxy", help="可选 HTTP 代理 URL")
    parser.add_argument("--overwrite", action="store_true", help="允许替换现有输出")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 3600:
        parser.error("--timeout 必须在 1 到 3600 秒之间")
    if args.text is not None or args.file is not None:
        if args.output is None:
            parser.error("合成需要 --output /absolute/path/audio.mp3")
    elif args.output is not None or args.subtitles is not None:
        parser.error("--setup 和 --list-voices 不接受输出路径")
    return args


def run(command, timeout):
    return subprocess.run(command, check=True, timeout=timeout,
                          capture_output=True, text=True)


def environment_path():
    override = os.environ.get("EDGE_TTS_CHINESE_VENV")
    return Path(override).expanduser().resolve() if override else SKILL_DIR / ".venv"


def environment_python(directory):
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def installed_version(python):
    if not python.is_file():
        return None
    try:
        return run([str(python), "-c",
                    "from importlib.metadata import version; print(version('edge-tts'))"],
                   timeout=15).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def setup(timeout):
    directory = environment_path()
    python = environment_python(directory)
    if installed_version(python) != VERSION:
        if not python.is_file():
            # Run venv in a subprocess so environment creation also has a deadline.
            run([sys.executable, "-m", "venv", str(directory)], timeout=timeout)
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "--retries", "0", "--timeout", "30", "-r",
             str(SKILL_DIR / "requirements.txt")], timeout=timeout)
    if installed_version(python) != VERSION:
        raise RuntimeError("依赖版本核验失败，请检查独立环境；未切换系统 Python")
    print(json.dumps({"environment": str(directory), "edge_tts": VERSION}, ensure_ascii=False))


def require_environment():
    python = environment_python(environment_path())
    if installed_version(python) != VERSION:
        raise RuntimeError("缺少独立环境或版本不匹配。先运行本脚本 --setup；需要 edge-tts==" + VERSION)
    return python


def list_voices(python, args):
    code = (
        "import asyncio,json,sys,edge_tts; "
        "items=asyncio.run(edge_tts.list_voices(proxy=sys.argv[1] or None)); "
        "print(json.dumps([{'name':v['ShortName'],'gender':v['Gender'],'locale':v['Locale']} "
        "for v in items if v['Locale'].startswith('zh-')],ensure_ascii=False))"
    )
    result = run([str(python), "-c", code, args.proxy or ""], timeout=args.timeout)
    print(result.stdout.strip())


def validate_outputs(args):
    output = args.output.expanduser().resolve()
    subtitle = args.subtitles.expanduser().resolve() if args.subtitles else None
    if output.suffix.lower() != ".mp3":
        raise ValueError("--output 必须使用 .mp3 扩展名")
    if subtitle and subtitle.suffix.lower() != ".srt":
        raise ValueError("--subtitles 必须使用 .srt 扩展名")
    source = args.file.expanduser().resolve() if args.file is not None else None
    for path in (output, subtitle):
        if path is None:
            continue
        if path == source:
            raise ValueError("输出不能覆盖输入文本文件")
        if path.exists() and (not args.overwrite or not path.is_file()):
            raise FileExistsError(f"输出已存在或不是普通文件：{path}；授权替换后才使用 --overwrite")
    return output, subtitle


def synthesize(python, args):
    output, subtitle = validate_outputs(args)
    text = (args.file.expanduser().read_text(encoding="utf-8-sig")
            if args.file is not None else args.text)
    if not text.strip():
        raise ValueError("输入文字为空")
    voice = VOICES.get(args.voice.lower(), args.voice)
    output.parent.mkdir(parents=True, exist_ok=True)
    if subtitle:
        subtitle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".edge-tts-", dir=output.parent) as temp:
        stage = Path(temp)
        source = stage / "input.txt"
        audio = stage / "audio.mp3"
        captions = stage / "captions.srt"
        source.write_text(text, encoding="utf-8")
        command = [str(python), "-m", "edge_tts", "--file", str(source),
                   "--voice", voice, f"--rate={args.rate}",
                   f"--volume={args.volume}", f"--pitch={args.pitch}",
                   "--no-progress", "--write-media", str(audio)]
        if subtitle:
            command.extend(["--write-subtitles", str(captions)])
        if args.proxy:
            command.extend(["--proxy", args.proxy])
        run(command, timeout=args.timeout)
        if not audio.is_file() or audio.stat().st_size < 256:
            raise RuntimeError("未返回有效音频，临时结果不交付")
        if subtitle:
            content = captions.read_text(encoding="utf-8") if captions.is_file() else ""
            if not re.search(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", content):
                raise RuntimeError("未返回有效 SRT，临时结果不交付")
        # Recheck before publication; existing outputs remain intact on TTS failures.
        validate_outputs(args)
        previous_subtitle = subtitle.read_bytes() if subtitle and subtitle.exists() else None
        if subtitle:
            # Stage in the destination directory so os.replace works across volumes.
            with tempfile.NamedTemporaryFile(dir=subtitle.parent, suffix=".srt", delete=False) as f:
                subtitle_stage = Path(f.name)
                f.write(captions.read_bytes())
            try:
                subtitle_stage.replace(subtitle)
            finally:
                subtitle_stage.unlink(missing_ok=True)
        try:
            audio.replace(output)
        except OSError:
            # If audio publication fails, put back the matching old subtitle.
            if subtitle:
                if previous_subtitle is None:
                    subtitle.unlink(missing_ok=True)
                else:
                    with tempfile.NamedTemporaryFile(dir=subtitle.parent, suffix=".srt", delete=False) as f:
                        rollback = Path(f.name)
                        f.write(previous_subtitle)
                    try:
                        rollback.replace(subtitle)
                    except OSError as exc:
                        raise RuntimeError(f"字幕回滚失败，旧字幕备份保留在：{rollback}") from exc
            raise
    print(json.dumps({"voice": voice, "rate": args.rate, "volume": args.volume,
                      "pitch": args.pitch, "audio": str(output),
                      "subtitles": str(subtitle) if subtitle else None,
                      "bytes": output.stat().st_size, "edge_tts": VERSION}, ensure_ascii=False))


def main(argv=None):
    if sys.version_info < (3, 9):
        print("需要 Python 3.9 或更新版本", file=sys.stderr)
        return 1
    args = parse_args(argv)
    try:
        if args.setup:
            setup(args.timeout)
        else:
            python = require_environment()
            if args.list_voices:
                list_voices(python, args)
            else:
                synthesize(python, args)
    except subprocess.TimeoutExpired:
        print("操作超时，已停止；请检查网络或使用 --timeout 增加时限。未自动重试。", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()[-1800:]
        print(f"调用失败（退出码 {exc.returncode}）。未自动重试。\n{detail}", file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
