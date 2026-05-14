# Anime Character Screenshot Tool  v4
### DeepDanbooru v3 + EfficientNet — smart auto-mode

Automatically takes screenshots when your chosen character appears,
even in group scenes. Skips near-duplicate frames automatically.

---

## Three ways to use it

### Option A — Character is on Danbooru (best accuracy)
1. Find tag at **https://danbooru.donmai.us**
2. Open `anime_screenshotter.py` in Notepad
3. Set: `CHARACTER_TAG = "irido_yume"`
4. Leave `references/` folder empty

### Option B — Character NOT on Danbooru (post-2021 anime etc.)
1. Take **5-10 clear face screenshots** of the character from the anime
2. Put them in the **`references/`** folder
3. Leave `CHARACTER_TAG = ""` in the script

### Option C — Both at once (highest accuracy)
- Set `CHARACTER_TAG` AND add reference images
- Set `COMBINE_MODE = "either"` for more results, `"both"` for fewer but stricter

---

## Quick start
1. Run **SETUP.bat** (first time only)
2. Configure as above
3. Put episodes in **`videos/`**
4. Run **RUN.bat**

First run downloads models automatically (DeepDanbooru ~700MB, EfficientNet ~25MB).

---

## Settings

| Setting | Default | What it does |
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

## Screenshot filename explained
`05m32s_dd0.67_ref0.74_+2others.png`
- `05m32s` = timestamp (5 min 32 sec)
- `dd0.67` = DeepDanbooru confidence
- `ref0.74` = Reference image similarity
- `+2others` = 2 other characters also visible in the scene
