# vidframe

Extract frames from videos at fixed intervals, or auto-screenshot when a
specific anime character appears. Ships with CLI, TUI, and desktop GUI.

Detection combines **DeepDanbooru v3** (tag-based) + **EfficientNet**
(reference-image similarity). Near-duplicate frames dropped automatically.

---

## Install

```bash
uv sync                    # base: extract + GUI/TUI
uv sync --extra detect     # add torch + tensorflow for character detection
```

First detection run downloads models (DeepDanbooru ~700MB, EfficientNet ~25MB).

---

## Run

```bash
uv run vidframe-gui   # desktop GUI (PySide6)
uv run vidframe       # terminal UI
uv run extract        # CLI: frame_extractor
uv run detect         # CLI: character_detector
```

---

## GUI

Two tabs: **Extract** and **Detect**.

- Path fields autocomplete directories inline (ghost text). `Tab` accepts,
  `Shift+Tab` cycles matches, `↓/↑` navigate popup. History ranked by MRU.
- Video list: `↑/↓` navigates, `Enter` toggles check, `Esc` clears
  selection, `Shift+Enter` starts the job.
- Settings persist across sessions (QSettings org `vidframe`).

---

## CLI — extract (no AI)

Fixed-interval frame dumps. No models needed.

```bash
python frame_extractor.py video.mp4 -s 5          # every 5 seconds
python frame_extractor.py video.mp4 -n 300 -f png # every 300 frames, PNG
python frame_extractor.py videos/ -s 2 --start 00:30 --end 05:00
```

Flags: `-o OUTPUT`, `-n N_FRAMES`, `-s SECONDS`, `-f {jpg,png}`, `-q QUALITY`,
`--start MM:SS`, `--end MM:SS`, `--prefix STR`. Progress via `tqdm`.

---

## Detection modes

### A — Character on Danbooru (best accuracy)
1. Find tag at https://danbooru.donmai.us
2. Set `CHARACTER_TAG = "irido_yume"` in `character_detector.py`
3. Leave `references/` empty.

### B — Character not on Danbooru
1. Save 5–10 clear face screenshots to `references/`
2. Leave `CHARACTER_TAG = ""`.

### C — Both (highest accuracy)
- Set `CHARACTER_TAG` **and** add reference images.
- `COMBINE_MODE = "either"` → more results. `"both"` → stricter.

---

## Detector settings

| Setting | Default | Meaning |
|---|---|---|
| `CHARACTER_TAG` | `""` | Danbooru tag. Empty = skip DeepDanbooru |
| `TAG_THRESHOLD` | `0.45` | DeepDanbooru confidence needed |
| `REFERENCE_FOLDER` | `"references"` | Folder with face images |
| `MATCH_THRESHOLD` | `0.72` | EfficientNet similarity needed |
| `COMBINE_MODE` | `"either"` | `"either"` or `"both"` when using both modes |
| `CHECKS_PER_SECOND` | `1` | Higher = slower but catches more |
| `MIN_SECONDS_GAP` | `4` | Min gap between screenshots |
| `DEDUP_HASH_THRESHOLD` | `8` | Lower = stricter duplicate removal |

---

## Screenshot filename format

`05m32s_dd0.67_ref0.74_+2others.png`

- `05m32s` — timestamp
- `dd0.67` — DeepDanbooru confidence
- `ref0.74` — reference similarity
- `+2others` — other characters visible in scene
