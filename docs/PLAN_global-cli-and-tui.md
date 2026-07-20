# Global CLI + Terminal UI — `frame-extract` + `char-detect`

## Context
Two related asks:
1. Invoke `frame_extractor.py` and `character_detector.py` from any directory in terminal (like `claude .` or `code .`), without breaking anything, without cache/state that could cause obscure errors, easy to undo.
2. Interactive **terminal UI** — arrow-key menu to pick video file(s) from a folder, pick interval, pick output format — instead of typing full paths and flags every time. No web/GUI frontend, pure terminal.

## Recommended Approach — Shell Aliases (simplest, safest)

Add two lines to `~/.zshrc`:

```bash
alias frame-extract="python3 /Users/antopou/Projects/Coding/Git/character-screenshotter/frame_extractor.py"
alias char-detect="python3 /Users/antopou/Projects/Coding/Git/character-screenshotter/character_detector.py"
```

Reload shell: `source ~/.zshrc` (or open new terminal).

Use anywhere:
```bash
cd ~/Downloads/some_anime
frame-extract episode01.mkv -s 5
char-detect
```

## Why aliases (not alternatives)

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Shell aliases** | Zero files, zero cache, one-line undo, no PATH changes, no sudo | Only works in zsh (fine — user is on zsh) | ✅ pick this |
| Symlink to `/usr/local/bin` | Global | Needs sudo, harder to remove, pollutes system dir | ❌ |
| `pipx install` / `pyproject.toml` | Real package | Creates venv cache, entry points, install state — user explicitly wants to avoid this | ❌ |
| Add project to `$PATH` | Simple | Every `.py` in project becomes runnable, needs `chmod +x` + shebang | ❌ |

## Behavior Notes (things user should know)

1. **Relative paths resolve to current dir.** Running `frame-extract video.mp4 -s 5` in `~/Downloads` looks for `~/Downloads/video.mp4` and writes to `~/Downloads/screenshots/`. That is the intended behavior.
2. **`character_detector.py` uses hardcoded `videos/` folder.** When run from another dir, it looks for `./videos/` there. Either `cd` into a folder that has `videos/`, or later refactor `character_detector.py` to accept a CLI arg. Out of scope for this plan.
3. **Python deps** (`cv2`, `tqdm`, `torch`, etc.) must be installed in whichever `python3` the alias points to. If user runs a venv, change the alias to that venv's python:
   ```bash
   alias frame-extract="/path/to/venv/bin/python /Users/antopou/Projects/Coding/Git/character-screenshotter/frame_extractor.py"
   ```

## Files to Modify

- `~/.zshrc` — append 2 alias lines (no other file touched)

**Nothing created inside the project.** No `bin/`, no wrapper scripts, no `pyproject.toml`, no `.egg-info`, no `__pycache__` beyond what Python already makes on import.

## Undo

Delete the 2 alias lines from `~/.zshrc`, reload shell. Done. Nothing else to clean.

## Part 2 — Terminal UI (interactive picker)

New wrapper file: `screenshotter.py` (project root). Single entrypoint. Launched with no args → opens interactive menu. Launched with args → falls through to CLI mode (unchanged behavior).

### Library: `InquirerPy`
- Arrow-key menus, checkbox multi-select, text prompts, file path autocomplete
- One dependency, cross-platform (macOS/Linux/Windows), pure Python, no compilation
- Alternatives: `questionary` (similar, older), `textual` (overkill — full TUI framework), `fzf` (external binary, not python)
- Add `InquirerPy` to `requirements.txt`

### Flow

```
$ screenshotter
┌────────────────────────────────────────────────┐
│ ? What to do?  (↑↓ + Enter)                    │
│ ❯ Extract frames at interval (simple)          │
│   Detect character (AI: DeepDanbooru + ref)    │
│   Quit                                         │
└────────────────────────────────────────────────┘

→ picks "Extract frames"

? Pick folder with videos: [./videos/]         (autocomplete)
? Select videos:                               (checkbox, ↑↓ + space)
  ◉ episode01.mkv
  ◯ episode02.mkv
  ◉ episode03.mkv
? Interval:
  ❯ Every N seconds
    Every N frames
? Seconds between shots: [2.0]
? Format: [jpg / png]
? Output folder: [screenshots]
? Start time (MM:SS, blank = beginning):
? End time (MM:SS, blank = end):

→ runs frame_extractor logic with tqdm bar per video
→ on finish: "? Do another? (y/N)"
```

For `char-detect` flow: prompt for `CHARACTER_TAG`, reference folder path, thresholds — same style. Writes chosen values to an in-memory config, runs the detector. Existing script constants become defaults.

### Implementation Sketch

- New file `screenshotter.py` (~120 lines)
- `argparse` with subcommand: `screenshotter` (no args = TUI) / `screenshotter extract ...` (CLI passthrough) / `screenshotter detect ...`
- TUI mode imports `InquirerPy`, builds menus, then calls the same functions from `frame_extractor.py` and `character_detector.py` (refactor: expose their `main()` bodies as callable functions taking a config dict)
- Minor refactor to `frame_extractor.py`: split `main()` into `run(config)` + arg-parsing shim, so TUI can call `run()` directly with a dict
- Minor refactor to `character_detector.py`: same pattern — allow overriding module-level constants from a config dict passed to a `run(config)` function

### Aliases (updated)

```bash
alias screenshotter="python3 /Users/antopou/Projects/Coding/Git/character-screenshotter/screenshotter.py"
```

One alias replaces the two. Type `screenshotter` anywhere → TUI opens.

Keep `frame-extract` / `char-detect` as direct-CLI shortcuts if wanted (optional).

### Files (updated)

- **Create**: `screenshotter.py` — TUI + dispatcher
- **Modify**: `frame_extractor.py` — expose `run(config)`
- **Modify**: `character_detector.py` — expose `run(config)`, accept config overrides
- **Modify**: `requirements.txt` — add `InquirerPy`
- **Modify**: `~/.zshrc` — 1 alias (or 3 if keeping shortcuts)
- **Modify**: `README.md` — document `screenshotter` entrypoint

### Verification (Part 2)

1. `pip install InquirerPy`
2. `screenshotter` in empty dir → menu appears, arrow keys work
3. Pick "Extract frames" → folder prompt → select folder with videos → checkbox multi-select works → interval prompt → runs, tqdm bar shows
4. Ctrl+C at any prompt → exits cleanly, no traceback
5. `screenshotter extract video.mp4 -s 5` → skips TUI, runs CLI directly (backwards compat)

## Open Questions (answer before implementation)

1. Use system `python3` or a specific venv path?
2. Alias names: `frame-extract` + `char-detect` + `screenshotter` OK? Or just single `screenshotter` alias covering everything via TUI + subcommands?
3. Should `character_detector.py` be updated to accept a `--videos DIR` arg so it's usable outside the project folder? (separate change, not strictly required)
4. TUI library — `InquirerPy` (recommended) or `questionary` or `textual`? Default = `InquirerPy`.

## Verification

1. `source ~/.zshrc`
2. `cd /tmp && frame-extract --help` → shows argparse help
3. `cd /tmp && char-detect` → runs (will complain about missing `videos/` if none present — expected)
4. `type frame-extract` → prints alias definition (confirms it is registered)
5. Remove aliases from `~/.zshrc`, `source` again, confirm `command -v frame-extract` returns nothing
