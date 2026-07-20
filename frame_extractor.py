"""
Frame Extractor — CLI

Dump screenshots from a video at fixed intervals. No AI, no dedup.
Terminal-only with tqdm progress bar.

Examples:
    python frame_extractor.py video.mp4 -s 5
    python frame_extractor.py video.mp4 -n 300 -f png
    python frame_extractor.py videos/ -s 2 --start 00:30 --end 05:00
"""

import argparse
import sys
from pathlib import Path

import cv2
from tqdm import tqdm

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m2ts", ".ts"}


def parse_ts(s):
    """Parse 'MM:SS' or 'HH:MM:SS' to seconds (float)."""
    parts = s.split(":")
    if len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + float(sec)
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + float(sec)
    raise argparse.ArgumentTypeError(f"Bad timestamp: {s!r} (want MM:SS or HH:MM:SS)")


def collect_videos(input_path):
    p = Path(input_path)
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXTS)
    raise FileNotFoundError(f"No such file/folder: {input_path}")


def process_video(video, out_root, step_frames, fmt, quality,
                  start_sec, end_sec, prefix):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        print(f"  Cannot open: {video.name}", file=sys.stderr)
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = int(start_sec * fps) if start_sec is not None else 0
    end_frame = int(end_sec * fps) if end_sec is not None else total
    end_frame = min(end_frame, total) if total > 0 else end_frame

    out_dir = Path(out_root) / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    name_prefix = prefix or video.stem
    ext = "png" if fmt == "png" else "jpg"
    imwrite_params = [] if ext == "png" else [cv2.IMWRITE_JPEG_QUALITY, int(quality)]

    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_num = start_frame
    saved = 0
    span = max(1, end_frame - start_frame)
    pbar = tqdm(total=span, unit="f", desc=video.name, dynamic_ncols=True)

    try:
        while True:
            if frame_num >= end_frame:
                break
            grabbed = cap.grab()
            if not grabbed:
                break

            if (frame_num - start_frame) % step_frames == 0:
                ret, frame = cap.retrieve()
                if ret:
                    ts = frame_num / fps
                    mm = int(ts // 60)
                    ss = int(ts % 60)
                    fname = f"{name_prefix}_{mm:02d}m{ss:02d}s_f{frame_num}.{ext}"
                    cv2.imwrite(str(out_dir / fname), frame, imwrite_params)
                    saved += 1
                    pbar.set_postfix(saved=saved)

            frame_num += 1
            pbar.update(1)
    finally:
        pbar.close()
        cap.release()

    print(f"  {video.name}: {saved} saved → {out_dir}")
    return saved


def build_parser():
    p = argparse.ArgumentParser(
        description="Dump screenshots from a video at fixed intervals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="Video file OR folder of videos")
    p.add_argument("-o", "--output", default="screenshots",
                   help="Output folder (default: screenshots)")

    grp = p.add_mutually_exclusive_group()
    grp.add_argument("-n", "--every-n-frames", type=int, metavar="N",
                     help="Grab every N frames")
    grp.add_argument("-s", "--every-seconds", type=float, metavar="SEC",
                     help="Grab every SEC seconds (default 2.0)")

    p.add_argument("-f", "--format", choices=["jpg", "png"], default="jpg",
                   help="Image format (default: jpg)")
    p.add_argument("-q", "--quality", type=int, default=92,
                   help="JPEG quality 1-100 (default: 92)")
    p.add_argument("--start", type=parse_ts, default=None,
                   help="Start timestamp MM:SS or HH:MM:SS")
    p.add_argument("--end", type=parse_ts, default=None,
                   help="End timestamp MM:SS or HH:MM:SS")
    p.add_argument("--prefix", default=None,
                   help="Filename prefix (default: video stem)")
    return p


def run(config):
    """
    config keys:
      videos      : list[Path] | Path | str  (file, folder, or list)
      output      : str  (default 'screenshots')
      every_n_frames : int | None
      every_seconds  : float | None  (default 2.0 if both None)
      format      : 'jpg' | 'png'    (default 'jpg')
      quality     : int              (default 92)
      start_sec   : float | None
      end_sec     : float | None
      prefix      : str | None
    returns: total screenshots saved
    """
    vids_arg = config.get("videos")
    if isinstance(vids_arg, (str, Path)):
        videos = collect_videos(vids_arg)
    else:
        videos = [Path(v) for v in vids_arg]

    if not videos:
        print("No videos found.", file=sys.stderr)
        return 0

    output   = config.get("output", "screenshots")
    fmt      = config.get("format", "jpg")
    quality  = config.get("quality", 92)
    start_s  = config.get("start_sec")
    end_s    = config.get("end_sec")
    prefix   = config.get("prefix")
    n_frames = config.get("every_n_frames")
    n_secs   = config.get("every_seconds")

    total_saved = 0
    for video in videos:
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.release()

        if n_frames is not None:
            step = max(1, int(n_frames))
        else:
            secs = n_secs if n_secs is not None else 2.0
            step = max(1, int(round(fps * secs)))

        try:
            total_saved += process_video(
                video, output, step, fmt, quality, start_s, end_s, prefix,
            )
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            raise

    print(f"\nTotal: {total_saved} screenshots across {len(videos)} video(s).")
    return total_saved


def main():
    args = build_parser().parse_args()
    config = {
        "videos": args.input,
        "output": args.output,
        "every_n_frames": args.every_n_frames,
        "every_seconds": args.every_seconds,
        "format": args.format,
        "quality": args.quality,
        "start_sec": args.start,
        "end_sec": args.end,
        "prefix": args.prefix,
    }
    try:
        run(config)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
