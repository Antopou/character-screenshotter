#!/usr/bin/env python3
"""
Anime Character Screenshot Tool  v4
Two modes — automatically selected:

  MODE A (DeepDanbooru)   — character has a Danbooru tag  → set CHARACTER_TAG
  MODE B (EfficientNet)   — character not on Danbooru     → add images to references/

You can even combine both: set CHARACTER_TAG AND add reference images
for extra accuracy.
"""

import cv2
import numpy as np
from pathlib import Path
import urllib.request
import zipfile
import os
import sys

from PIL import Image
import imagehash

# ============================================================
#  SETTINGS — Edit these!
# ============================================================

# ── Mode A: DeepDanbooru ─────────────────────────────────
# Find tag at https://danbooru.donmai.us
# Leave empty ("") to skip DeepDanbooru and use reference images only
CHARACTER_TAG  = ""           # e.g. "rem_(re:zero)" or "nakano_miku"
TAG_THRESHOLD  = 0.45         # Confidence needed (0.3–0.8)

# ── Mode B: Reference images ──────────────────────────────
# Put clear face screenshots of your character in the references/ folder
# Used automatically when CHARACTER_TAG is empty, or as a second check
REFERENCE_FOLDER    = "references"
MATCH_THRESHOLD     = 0.72    # Neural similarity needed (0.6–0.9)

# ── How to combine both modes (if both are active) ────────
# "either"  → screenshot if DeepDanbooru OR reference matches  (more results)
# "both"    → screenshot only if BOTH match                    (fewer but more accurate)
COMBINE_MODE = "either"

# ── General ───────────────────────────────────────────────
VIDEO_FOLDER         = "videos"
OUTPUT_FOLDER        = "screenshots"
CHECKS_PER_SECOND    = 1      # Frames per second to check
MIN_SECONDS_GAP      = 4      # Min seconds between screenshots
DEDUP_HASH_THRESHOLD = 8      # Visual dedup strictness (lower = stricter)
DEDUP_MEMORY         = 14     # Recent screenshots to compare against

# ============================================================

MODEL_DIR    = "deepdanbooru-v3"
MODEL_FILE   = os.path.join(MODEL_DIR, "model-resnet_custom_v3.h5")
TAGS_FILE    = os.path.join(MODEL_DIR, "tags.txt")
MODEL_URL    = ("https://github.com/KichangKim/DeepDanbooru/releases/download"
                "/v3-20211112-sgd-e28/deepdanbooru-v3-20211112-sgd-e28.zip")
CASCADE_URL  = ("https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface"
                "/master/lbpcascade_animeface.xml")
CASCADE_FILE = "lbpcascade_animeface.xml"
VIDEO_EXTS   = {'.mkv', '.mp4', '.avi', '.mov', '.m2ts', '.ts'}


# ────────────────────────────────────────────────────────────
#  Cascade (face detector — shared by both modes)
# ────────────────────────────────────────────────────────────

def download_cascade():
    if not os.path.exists(CASCADE_FILE):
        print("Downloading anime face detector (~1 MB)...")
        urllib.request.urlretrieve(CASCADE_URL, CASCADE_FILE)
        print("Done.\n")


def detect_faces(cascade, frame):
    """Return list of (x,y,w,h) face boxes in a frame — two passes for group scenes."""
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces_a = cascade.detectMultiScale(gray, scaleFactor=1.1,
                                       minNeighbors=5, minSize=(40, 40))
    faces_b = cascade.detectMultiScale(gray, scaleFactor=1.05,
                                       minNeighbors=3, minSize=(20, 20))
    if len(faces_a) > 0 and len(faces_b) > 0:
        return np.vstack([faces_a, faces_b])
    elif len(faces_a) > 0:
        return faces_a
    elif len(faces_b) > 0:
        return faces_b
    return []


# ────────────────────────────────────────────────────────────
#  MODE A — DeepDanbooru
# ────────────────────────────────────────────────────────────

def ensure_dd_model():
    if os.path.exists(MODEL_FILE) and os.path.exists(TAGS_FILE):
        return
    print("=" * 62)
    print("  DeepDanbooru v3 model not found (~700 MB)")
    print("=" * 62)
    print(f"\n  URL: {MODEL_URL}\n")
    print("  A) Press Enter  → auto-download now")
    print("  B) Type 'skip'  → download manually, extract to 'deepdanbooru-v3/'")
    choice = input("\n  Choice: ").strip().lower()
    if choice == 'skip':
        print("Re-run after placing model files.")
        sys.exit(0)
    print("\nDownloading (~700 MB) ...")
    zip_path = "deepdanbooru-v3.zip"
    def _prog(c, bs, ts):
        if ts > 0:
            pct = min(c * bs / ts * 100, 100)
            bar = "#" * int(pct // 2) + "-" * (50 - int(pct // 2))
            sys.stdout.write(f"\r  [{bar}] {pct:.1f}%  ")
            sys.stdout.flush()
    urllib.request.urlretrieve(MODEL_URL, zip_path, reporthook=_prog)
    print("\nExtracting...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(MODEL_DIR)
    os.remove(zip_path)
    print("Model ready!\n")


def load_dd_model():
    import tensorflow as tf
    print("  Loading DeepDanbooru v3...")
    model = tf.keras.models.load_model(MODEL_FILE)
    with open(TAGS_FILE, 'r', encoding='utf-8') as f:
        tags = [line.strip() for line in f]
    print(f"  {len(tags):,} tags loaded.")
    return model, tags


def dd_score(model, tags, frame, char_tag):
    """Return DeepDanbooru confidence for char_tag in this frame."""
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (512, 512))
    img = img.astype(np.float32) / 255.0
    preds = model(np.expand_dims(img, 0), training=False).numpy()[0]
    try:
        return float(preds[tags.index(char_tag)])
    except ValueError:
        return 0.0


# ────────────────────────────────────────────────────────────
#  MODE B — EfficientNet + reference images
# ────────────────────────────────────────────────────────────

def load_efficientnet():
    import torch
    import torchvision.transforms as T
    from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
    print("  Loading EfficientNet (open-source, ~25 MB first download)...")
    m = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    m.classifier = torch.nn.Identity()
    m.eval()
    tfm = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    print("  EfficientNet ready.")
    return m, tfm


def get_embedding(model, tfm, bgr_img):
    import torch
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    t   = tfm(Image.fromarray(rgb)).unsqueeze(0)
    with torch.no_grad():
        e = model(t)
    return e / e.norm()


def cosine_sim(e1, e2):
    return float((e1 * e2).sum())


def load_references(folder, cascade, eff_model, eff_tfm):
    ref_path = Path(folder)
    if not ref_path.exists():
        ref_path.mkdir(parents=True)
        print(f"  '{folder}' created. Add character face images and re-run.")
        sys.exit(1)
    files = (list(ref_path.glob("*.jpg"))
           + list(ref_path.glob("*.jpeg"))
           + list(ref_path.glob("*.png")))
    if not files:
        print(f"  No images in '{folder}'. Add .jpg/.png face images and re-run.")
        sys.exit(1)
    print(f"  Loading {len(files)} reference image(s)...")
    embeddings = []
    for p in files:
        img = cv2.imread(str(p))
        if img is None:
            continue
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1,
                                         minNeighbors=5, minSize=(20, 20))
        face  = img[faces[0][1]:faces[0][1]+faces[0][3],
                    faces[0][0]:faces[0][0]+faces[0][2]] if len(faces) > 0 else img
        embeddings.append(get_embedding(eff_model, eff_tfm, face))
        label = "face found" if len(faces) > 0 else "no face — using full image"
        print(f"    {p.name}  ({label})")
    return embeddings


def ref_score(eff_model, eff_tfm, face_img, ref_embeddings):
    """Return best cosine similarity against reference embeddings."""
    emb = get_embedding(eff_model, eff_tfm, face_img)
    return max(cosine_sim(emb, r) for r in ref_embeddings)


# ────────────────────────────────────────────────────────────
#  Deduplication
# ────────────────────────────────────────────────────────────

_recent_hashes = []

def is_duplicate(frame):
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    h   = imagehash.phash(pil)
    return any(abs(h - prev) <= DEDUP_HASH_THRESHOLD for prev in _recent_hashes)

def record_hash(frame):
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    _recent_hashes.append(imagehash.phash(pil))
    if len(_recent_hashes) > DEDUP_MEMORY:
        _recent_hashes.pop(0)


# ────────────────────────────────────────────────────────────
#  Video processing
# ────────────────────────────────────────────────────────────

def process_video(video_path, cascade,
                  dd_model, dd_tags,          # None if Mode A inactive
                  eff_model, eff_tfm,          # None if Mode B inactive
                  ref_embeddings,              # [] if Mode B inactive
                  progress_cb=None, log_cb=None, cancel_cb=None):

    def _log(msg):
        if log_cb:
            log_cb(msg)
        else:
            print(msg)

    use_dd  = dd_model  is not None and dd_tags  is not None
    use_ref = eff_model is not None and len(ref_embeddings) > 0

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        _log(f"  Cannot open: {video_path.name}")
        return 0

    fps          = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    chk_interval = max(1, int(fps / CHECKS_PER_SECOND))
    min_gap_frm  = int(MIN_SECONDS_GAP * fps)

    out_dir = Path(OUTPUT_FOLDER) / video_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    dur_m = int((total_frames / fps) // 60)
    dur_s = int((total_frames / fps) % 60)
    _log(f"\n  {video_path.name}  [{dur_m}m {dur_s}s]")

    saved       = 0
    skipped_dup = 0
    frame_num   = 0
    last_shot   = -min_gap_frm

    while cap.isOpened():
        if cancel_cb and cancel_cb():
            _log(f"  Cancelled at frame {frame_num}")
            break
        grabbed = cap.grab()
        if not grabbed:
            break

        if frame_num % chk_interval == 0 and (frame_num - last_shot) >= min_gap_frm:
            ret, frame = cap.retrieve()
            if ret:
                faces = detect_faces(cascade, frame)
                if len(faces) == 0:
                    frame_num += 1
                    continue

                dd_hit,  dd_conf  = False, 0.0
                ref_hit, ref_conf = False, 0.0

                # Mode A — DeepDanbooru (whole frame)
                if use_dd:
                    dd_conf = dd_score(dd_model, dd_tags, frame, CHARACTER_TAG)
                    dd_hit  = dd_conf >= TAG_THRESHOLD

                # Mode B — EfficientNet (per detected face)
                if use_ref:
                    best = 0.0
                    for (x, y, w, h) in faces:
                        x1 = max(0, x); y1 = max(0, y)
                        x2 = min(frame.shape[1], x+w)
                        y2 = min(frame.shape[0], y+h)
                        face_crop = frame[y1:y2, x1:x2]
                        if face_crop.size == 0:
                            continue
                        s = ref_score(eff_model, eff_tfm, face_crop, ref_embeddings)
                        if s > best:
                            best = s
                    ref_conf = best
                    ref_hit  = ref_conf >= MATCH_THRESHOLD

                # Decide based on combine mode
                if use_dd and use_ref:
                    matched = (dd_hit or ref_hit) if COMBINE_MODE == "either" else (dd_hit and ref_hit)
                elif use_dd:
                    matched = dd_hit
                else:
                    matched = ref_hit

                if matched:
                    if is_duplicate(frame):
                        skipped_dup += 1
                    else:
                        ts  = frame_num / fps
                        mm  = int(ts // 60);  ss = int(ts % 60)
                        n   = len(faces)
                        who = "solo" if n == 1 else f"+{n-1}others"

                        # Build confidence label for filename
                        conf_parts = []
                        if use_dd:  conf_parts.append(f"dd{dd_conf:.2f}")
                        if use_ref: conf_parts.append(f"ref{ref_conf:.2f}")
                        conf_str = "_".join(conf_parts)

                        fname = f"{mm:02d}m{ss:02d}s_{conf_str}_{who}.png"
                        cv2.imwrite(str(out_dir / fname), frame)
                        record_hash(frame)

                        saved    += 1
                        last_shot = frame_num
                        pct = frame_num / total_frames * 100

                        # Build readable log line
                        scores = []
                        if use_dd:  scores.append(f"DD:{dd_conf:.2f}")
                        if use_ref: scores.append(f"REF:{ref_conf:.2f}")
                        note = f"  (+{n-1} others)" if n > 1 else ""
                        _log(f"  Screenshot [{pct:5.1f}%] {mm:02d}:{ss:02d}"
                             f"  {' | '.join(scores)}{note}")

        if progress_cb and frame_num % 30 == 0 and total_frames > 0:
            pct = frame_num / total_frames * 100
            progress_cb(pct, saved, video_path.name)
        elif not progress_cb and total_frames > 0 and frame_num % max(1, total_frames // 20) == 0:
            pct = frame_num / total_frames * 100
            bar = "#" * int(pct // 5) + "-" * (20 - int(pct // 5))
            sys.stdout.write(
                f"\r  [{bar}] {pct:.0f}%  saved:{saved}  dupes_skipped:{skipped_dup}   "
            )
            sys.stdout.flush()

        frame_num += 1

    cap.release()
    if progress_cb:
        progress_cb(100.0, saved, video_path.name)
    _log(f"\n  Done: {saved} saved,  {skipped_dup} duplicates skipped  →  {out_dir.name}/")
    return saved


# ────────────────────────────────────────────────────────────
#  Main
# ────────────────────────────────────────────────────────────

_CONFIG_KEYS = {
    "CHARACTER_TAG", "TAG_THRESHOLD", "REFERENCE_FOLDER", "MATCH_THRESHOLD",
    "COMBINE_MODE", "VIDEO_FOLDER", "OUTPUT_FOLDER",
    "CHECKS_PER_SECOND", "MIN_SECONDS_GAP",
    "DEDUP_HASH_THRESHOLD", "DEDUP_MEMORY",
}


def run(config=None):
    """
    Run character detector. Optional config dict overrides module-level constants.
    Extra keys:
      videos      : explicit list[Path] (overrides VIDEO_FOLDER scan)
      progress_cb : callable(pct, saved, video_name)
      log_cb      : callable(str)
      cancel_cb   : callable() -> bool
    """
    if config:
        overrides = {k: v for k, v in config.items() if k in _CONFIG_KEYS}
        globals().update(overrides)
    cfg = config or {}
    return _main_impl(
        videos_override=cfg.get("videos"),
        progress_cb=cfg.get("progress_cb"),
        log_cb=cfg.get("log_cb"),
        cancel_cb=cfg.get("cancel_cb"),
    )


def main():
    return run(None)


def _main_impl(videos_override=None, progress_cb=None, log_cb=None, cancel_cb=None):
    def _log(m):
        (log_cb or print)(m)
    print("=" * 62)
    print("  Anime Character Screenshot Tool  v4")
    print("  DeepDanbooru + EfficientNet  (auto-mode)")
    print("=" * 62)

    use_dd  = bool(CHARACTER_TAG.strip())
    use_ref = Path(REFERENCE_FOLDER).exists() and any(
        Path(REFERENCE_FOLDER).glob("*.jpg")
    ) or any(
        Path(REFERENCE_FOLDER).glob("*.png")
    ) if Path(REFERENCE_FOLDER).exists() else False

    if not use_dd and not use_ref:
        print("\n  Nothing configured!")
        print("  Option A: Set CHARACTER_TAG (for characters on Danbooru)")
        print("  Option B: Add images to references/ folder (any character)")
        print("  Option C: Both at once for highest accuracy")
        sys.exit(1)

    print(f"\n  Mode: ", end="")
    if use_dd and use_ref:
        print(f"BOTH (combine={COMBINE_MODE})")
    elif use_dd:
        print("DeepDanbooru only")
    else:
        print("Reference images only (EfficientNet)")

    download_cascade()
    cascade = cv2.CascadeClassifier(CASCADE_FILE)

    dd_model = dd_tags = None
    if use_dd:
        print("\n[DeepDanbooru]")
        ensure_dd_model()
        dd_model, dd_tags = load_dd_model()
        if CHARACTER_TAG not in dd_tags:
            print(f"\n  WARNING: '{CHARACTER_TAG}' not in DeepDanbooru v3.")
            first = CHARACTER_TAG.split('_')[0]
            similar = [t for t in dd_tags if first in t][:6]
            if similar:
                print(f"  Similar tags: {similar}")
            print("  Falling back to reference image mode only.")
            dd_model = dd_tags = None
            use_dd   = False

    eff_model = eff_tfm = None
    ref_embeddings = []
    if use_ref or (not use_dd):
        print("\n[EfficientNet / Reference images]")
        eff_model, eff_tfm = load_efficientnet()
        ref_embeddings = load_references(
            REFERENCE_FOLDER, cascade, eff_model, eff_tfm
        )

    print(f"\n  Settings:")
    if use_dd:  print(f"    Character tag   : {CHARACTER_TAG}  (threshold {TAG_THRESHOLD})")
    if use_ref: print(f"    Reference images: {len(ref_embeddings)}  (threshold {MATCH_THRESHOLD})")
    print(f"    Checks/sec      : {CHECKS_PER_SECOND}")
    print(f"    Min gap         : {MIN_SECONDS_GAP}s")
    print(f"    Dedup           : hash≤{DEDUP_HASH_THRESHOLD}  memory:{DEDUP_MEMORY}\n")

    if videos_override:
        videos = [Path(v) for v in videos_override]
    else:
        vid_dir = Path(VIDEO_FOLDER)
        if not vid_dir.exists():
            vid_dir.mkdir(parents=True)
            print(f"  '{VIDEO_FOLDER}' folder created. Add episodes and re-run.")
            sys.exit(1)

        videos = sorted(f for f in vid_dir.iterdir() if f.suffix.lower() in VIDEO_EXTS)
        if not videos:
            print(f"  No videos found in '{VIDEO_FOLDER}'.")
            sys.exit(1)

    print(f"  {len(videos)} video(s) to process\n")
    total = 0
    for v in videos:
        if cancel_cb and cancel_cb():
            _log("Cancelled.")
            break
        total += process_video(
            v, cascade, dd_model, dd_tags, eff_model, eff_tfm, ref_embeddings,
            progress_cb=progress_cb, log_cb=log_cb, cancel_cb=cancel_cb,
        )

    print("\n" + "=" * 62)
    print(f"  All done!  Total screenshots: {total}")
    print(f"  Saved to: {Path(OUTPUT_FOLDER).resolve()}")
    print("=" * 62)
    print("\n  Tips:")
    print("  Too many wrong chars?  raise TAG_THRESHOLD / MATCH_THRESHOLD")
    print("  Missing shots?         lower TAG_THRESHOLD / MATCH_THRESHOLD")
    print("  Still getting dupes?   lower DEDUP_HASH_THRESHOLD to 5")


if __name__ == "__main__":
    main()
