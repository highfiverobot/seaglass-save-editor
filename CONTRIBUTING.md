# Contributing

Thanks for your interest in improving the Seaglass Save Editor! This guide
covers setup, the code layout, and how to get changes merged.

## Setup (Windows)

1. Install **Python 3.11+** from <https://www.python.org/downloads/windows/>
   (tick the **py launcher** during install).
2. Run **`setup.bat`** once. This creates a local virtual environment
   (`.venv`) and installs dependencies from `requirements.txt`.
3. Launch the app with **`run_app.bat`**. Edits run live from source, so you
   do **not** need to rebuild the exe while developing.

## Running from source in any OS

```
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seaglass_editor.py
```

## Code layout

| File | Responsibility |
|------|----------------|
| `seaglass_inspect.py` | Read/decrypt core: ROM tables, save sector I/O, party + PC-box decoding, sprites, gender/growth/level. Also a read-only CLI (`python seaglass_inspect.py <save> <rom>`). |
| `seaglass_write.py`    | Edit setters, re-encrypt + repack, per-section checksum fix-up, save writing, and `.pk3` export. |
| `seaglass_editor.py`   | PySide6 GUI (party/box browser, editor, save/export). |
| `theme.py`             | Dark UI theme (Qt). |

Data/logic lives in `seaglass_inspect.py` / `seaglass_write.py`; the GUI should
stay a thin layer over them. If you can, add logic to the core modules (with a
headless test) rather than to the GUI.

## Tests

A headless smoke test lives in `tests/smoke_test.py`. It needs the PySide6
`offscreen` platform and a sample save + ROM to exercise the full path. Run:

```
python tests/smoke_test.py
```

It is skipped gracefully if the sample files are absent. CI runs a lighter
import/parse check on every push (see `.github/workflows/ci.yml`).

## Submitting changes

1. Fork and create a branch.
2. Keep changes focused; match the existing code style.
3. Make sure `python -m py_compile *.py` passes and, if you touched the core,
   that the smoke test still passes.
4. Open a pull request describing **what** and **why**.

## What we will NOT merge

- Anything that requires uploading users' save files to a server (this tool is
  strictly local).
- Changes that silently break save checksums or in-game validity.

## Building the standalone exe

Contributors generally don't need to. End users download a prebuilt exe; it is
produced automatically on release tags by `.github/workflows/release.yml`. For
local testing you can run **`build_exe.bat`**, which outputs
`dist/SeaglassEditor.exe`.
