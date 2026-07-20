#!/usr/bin/env python3
"""
Screenshotter — Terminal UI

Interactive menu for:
  - Extract frames at interval  (frame_extractor.run)
  - Detect character (AI)       (character_detector.run)

Run with no args → TUI. Run with subcommand → CLI passthrough.

    python screenshotter.py                   # interactive
    python screenshotter.py extract ...       # forwards to frame_extractor
    python screenshotter.py detect            # forwards to character_detector
"""

import sys
from pathlib import Path

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.validator import PathValidator, NumberValidator
except ImportError:
    print("Missing dependency: InquirerPy", file=sys.stderr)
    print("Install with:  pip install InquirerPy", file=sys.stderr)
    sys.exit(1)

import frame_extractor
import character_detector

VIDEO_EXTS = frame_extractor.VIDEO_EXTS


def list_videos(folder):
    p = Path(folder).expanduser()
    if not p.is_dir():
        return []
    return sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXTS)


def list_subdirs(folder):
    p = Path(folder).expanduser()
    if not p.is_dir():
        return []
    try:
        return sorted(
            d for d in p.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
    except PermissionError:
        return []


_SENTINEL_UP     = "__UP__"
_SENTINEL_PICK   = "__PICK_HERE__"
_SENTINEL_HOME   = "__HOME__"
_SENTINEL_CWD    = "__CWD__"
_SENTINEL_MANUAL = "__MANUAL__"
_SENTINEL_CANCEL = "__CANCEL__"


ESC_KEYBIND = {"skip": [{"key": "escape"}]}


def browse_for_folder(start=None):
    """
    Interactive directory navigator. Arrow-select through file tree.
    ESC = back (undo last navigation).
    Returns folder Path (containing videos) or None if cancelled.
    """
    start_path = Path(start or Path.cwd()).expanduser().resolve()
    history = [start_path]

    while True:
        current = history[-1]
        subdirs = list_subdirs(current)
        videos_here = list_videos(current)

        choices = []
        choices.append(Choice(_SENTINEL_PICK,
                              name=f"✅  Use this folder  ({len(videos_here)} video(s) here)"))
        if current.parent != current:
            choices.append(Choice(_SENTINEL_UP, name=".. (up one level)"))

        for d in subdirs:
            n_vids = len(list_videos(d))
            tag = f"  🎬 {n_vids}" if n_vids else ""
            choices.append(Choice(str(d), name=f"📁  {d.name}/{tag}"))

        for v in videos_here:
            choices.append(Choice(f"__FILE__{v}", name=f"🎬  {v.name}",
                                  enabled=False))

        choices.append(Choice(_SENTINEL_HOME,   name="⌂  Jump to $HOME"))
        choices.append(Choice(_SENTINEL_CWD,    name="⌂  Jump to current working dir"))
        choices.append(Choice(_SENTINEL_MANUAL, name="⌨  Type path manually"))
        choices.append(Choice(_SENTINEL_CANCEL, name="✗  Cancel (or Ctrl+C)"))

        hint = "  [ESC = back]" if len(history) > 1 else ""
        pick = inquirer.select(
            message=f"Browse: {current}{hint}",
            choices=choices,
            default=_SENTINEL_PICK if videos_here else None,
            height="70%",
            keybindings=ESC_KEYBIND,
            mandatory=False,
        ).execute()

        # ESC pressed → skip returns None
        if pick is None:
            if len(history) > 1:
                history.pop()
                continue
            return None

        if pick == _SENTINEL_PICK:
            return current
        if pick == _SENTINEL_UP:
            history.append(current.parent)
            continue
        if pick == _SENTINEL_HOME:
            history.append(Path.home())
            continue
        if pick == _SENTINEL_CWD:
            history.append(Path.cwd())
            continue
        if pick == _SENTINEL_CANCEL:
            return None
        if pick == _SENTINEL_MANUAL:
            typed = inquirer.filepath(
                message="Path:",
                default=str(current),
                only_directories=True,
                validate=PathValidator(is_dir=True, message="Not a directory"),
            ).execute()
            history.append(Path(typed).expanduser().resolve())
            continue
        if pick.startswith("__FILE__"):
            continue
        history.append(Path(pick))


def prompt_video_selection(default_folder="videos"):
    default_start = default_folder if Path(default_folder).is_dir() else str(Path.cwd())

    while True:
        folder = browse_for_folder(start=default_start)
        if folder is None:
            return []

        videos = list_videos(folder)
        if not videos:
            print(f"  No videos in {folder}")
            return []

        choices = [Choice(str(v), name=v.name, enabled=True) for v in videos]
        selected = inquirer.checkbox(
            message=f"Select videos in {folder.name}/  [ESC = back to browser]",
            choices=choices,
            validate=lambda result: len(result) > 0,
            invalid_message="Pick at least one video.",
            height="70%",
            keybindings=ESC_KEYBIND,
            mandatory=False,
        ).execute()

        if selected is None:
            default_start = str(folder)
            continue
        return [Path(s) for s in selected]


def prompt_timestamp(message):
    while True:
        raw = inquirer.text(message=message, default="").execute()
        raw = raw.strip()
        if not raw:
            return None
        try:
            return frame_extractor.parse_ts(raw)
        except Exception:
            print("  Bad timestamp. Use MM:SS or HH:MM:SS. Blank = skip.")


def flow_extract():
    videos = prompt_video_selection()
    if not videos:
        return

    mode = inquirer.select(
        message="Interval mode:",
        choices=["Every N seconds", "Every N frames"],
        default="Every N seconds",
    ).execute()

    every_seconds = every_n_frames = None
    if mode == "Every N seconds":
        every_seconds = float(inquirer.text(
            message="Seconds between shots:",
            default="2.0",
            validate=NumberValidator(float_allowed=True),
        ).execute())
    else:
        every_n_frames = int(inquirer.text(
            message="Frames between shots:",
            default="50",
            validate=NumberValidator(),
        ).execute())

    fmt = inquirer.select(
        message="Image format:",
        choices=["jpg", "png"],
        default="jpg",
    ).execute()

    quality = 92
    if fmt == "jpg":
        quality = int(inquirer.text(
            message="JPEG quality (1-100):",
            default="92",
            validate=NumberValidator(),
        ).execute())

    output = inquirer.text(message="Output folder:", default="screenshots").execute()
    start_sec = prompt_timestamp("Start time (MM:SS, blank = beginning):")
    end_sec = prompt_timestamp("End time (MM:SS, blank = end):")

    config = {
        "videos": videos,
        "output": output,
        "every_seconds": every_seconds,
        "every_n_frames": every_n_frames,
        "format": fmt,
        "quality": quality,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "prefix": None,
    }
    frame_extractor.run(config)


def flow_detect():
    videos = prompt_video_selection()
    if not videos:
        return

    tag = inquirer.text(
        message="Character tag (Danbooru, blank = skip DeepDanbooru):",
        default="",
    ).execute().strip()

    ref_folder = inquirer.text(
        message="Reference folder (blank = skip reference mode):",
        default="references",
    ).execute().strip()

    if not tag and (not ref_folder or not Path(ref_folder).exists()):
        print("  Need at least a character tag OR a reference folder with images.")
        return

    config = {"videos": videos}
    if tag:
        config["CHARACTER_TAG"] = tag
        config["TAG_THRESHOLD"] = float(inquirer.text(
            message="Tag threshold (0.3-0.8):",
            default="0.45",
            validate=NumberValidator(float_allowed=True),
        ).execute())
    else:
        config["CHARACTER_TAG"] = ""

    if ref_folder:
        config["REFERENCE_FOLDER"] = ref_folder
        if Path(ref_folder).exists():
            config["MATCH_THRESHOLD"] = float(inquirer.text(
                message="Match threshold (0.6-0.9):",
                default="0.72",
                validate=NumberValidator(float_allowed=True),
            ).execute())

    if tag and ref_folder and Path(ref_folder).exists():
        config["COMBINE_MODE"] = inquirer.select(
            message="Combine mode:",
            choices=["either", "both"],
            default="either",
        ).execute()

    config["CHECKS_PER_SECOND"] = int(inquirer.text(
        message="Checks per second:",
        default="1",
        validate=NumberValidator(),
    ).execute())
    config["MIN_SECONDS_GAP"] = int(inquirer.text(
        message="Min gap between shots (sec):",
        default="4",
        validate=NumberValidator(),
    ).execute())
    config["OUTPUT_FOLDER"] = inquirer.text(
        message="Output folder:", default="screenshots",
    ).execute()

    character_detector.run(config)


def tui_loop():
    print("=" * 62)
    print("  Character Screenshotter — Terminal UI")
    print("=" * 62)

    print("  Exit: pick 'Quit', press ESC on main menu, or Ctrl+C anywhere.")
    while True:
        action = inquirer.select(
            message="What to do?  [ESC or Ctrl+C = quit]",
            choices=[
                Choice("extract", name="Extract frames at interval (simple, no AI)"),
                Choice("detect",  name="Detect character (AI: DeepDanbooru + reference)"),
                Choice("quit",    name="Quit"),
            ],
            keybindings=ESC_KEYBIND,
            mandatory=False,
        ).execute()

        if action is None or action == "quit":
            return
        try:
            if action == "extract":
                flow_extract()
            elif action == "detect":
                flow_detect()
        except KeyboardInterrupt:
            print("\n  Interrupted. Back to menu.")
            continue

        again = inquirer.confirm(message="Run again?", default=False).execute()
        if not again:
            return


def main():
    if len(sys.argv) > 1:
        sub = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        if sub == "extract":
            frame_extractor.main()
            return
        if sub == "detect":
            character_detector.main()
            return
        print(f"Unknown subcommand: {sub!r}. Use 'extract' or 'detect', or no args for TUI.",
              file=sys.stderr)
        sys.exit(2)

    try:
        tui_loop()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(130)


if __name__ == "__main__":
    main()
