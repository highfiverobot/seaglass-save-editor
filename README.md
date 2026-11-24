<img width="512" height="512" alt="emerald seaglass editor" align="center" src="https://github.com/user-attachments/assets/83fefe0c-c059-4ae2-897d-4ec42094b3b0" />

# Seaglass Save Editor

A friendly desktop save editor for **Pokemon Emerald Seaglass**. Browse your
party and PC boxes, edit Pokemon, and write back a clean, checksum-correct
save -- or export individual Pokemon as `.pk3` files for use in PKHeX.

Everything runs **locally**. Your save file never leaves your computer and
nothing is uploaded anywhere.

---

## Features

### Viewing
- **Party** browser -- every party Pokemon shown as a sprite in a collapsible
  "Party" section.
- **PC Boxes** -- all 14 boxes shown as collapsible sprite grids (the current
  box is highlighted and auto-expanded). Click any Pokemon to see its details.
- **Shiny indicator** -- shiny sprites have a star in their tooltip; a
  **"Show only shinies"** toggle filters both party and boxes.
- **Info panel** -- sprite, species, **gender**, shiny status, egg flag, PID,
  OTID and base stats.
- Responsive layout -- sprite grids reflow to fit the window at any width.

### Editing (party Pokemon)
- Nickname
- Level and EXP
- Friendship
- **Ability** (all available ability slots)
- Held item
- Four moves
- IVs (0-31) and EVs (0-255) per stat
- **Shiny** -- toggle on/off reliably:
  - On: sets the shiny flag.
  - Off: clears the flag, and if the Pokemon is *also* shiny by its PID,
    adjusts the hidden Secret ID so it becomes genuinely non-shiny while
    keeping its visible Trainer ID, nature, gender and everything else
    unchanged.

> **Species and Nature are read-only** by design. Changing them would
> desynchronise internal PID-derived data (nature, gender, encryption). We
> leave them fixed to keep your save safe.

### Saving and exporting
- **Save** -- overwrite the currently-open save (with a confirmation prompt).
- **Save As...** -- write to a new file (recommended; keeps your original safe).
- All writes recompute the affected sector checksums; the file stays valid.
- **Export .pk3...** -- export the selected Pokemon (party *or* box) as a
  100-byte Gen3 `.pk3` file for PKHeX. If the Pokemon is shiny in-game, the export is made shiny by the standard Gen3 PID/OTID rule (only the hidden Secret ID is adjusted), so it shows as shiny in both PKHeX and the game -- PID, visible Trainer ID and nature are left untouched.

---

## How to run

### Option 1 -- the ready-made executable (easiest, no install)
1. Download `SeaglassEditor.exe` (from the Releases page).
2. Double-click it. That is it -- no Python, no setup.

### Option 2 -- run from source
1. Install Python 3.11+.
2. Run `setup.bat` once (creates a virtual environment and installs PySide6).
3. Run `run_app.bat`.

---

## What you need
- Your **Seaglass save file** (`.sav`, typically from an emulator or flashcart).
- The **Seaglass ROM** (`pokemon emerald seaglass.gba`) -- the editor reads
  species names, abilities, moves, items, stats and sprites from it. You must
  have the ROM; it is not bundled.

Typical flow:
1. **Open ROM...** -> choose your `.gba`.
2. **Open Save...** -> choose your `.sav`.
3. Click a Pokemon, make changes, **Apply to Pokemon**.
4. **Save As...** (or **Save**) to write the result.

---

## First-run warning (SmartScreen)

Because the `.exe` is not code-signed, Windows may show:

> "Windows protected your PC"

Click **More info -> Run anyway**. This is normal for unsigned independent
apps and does not indicate the file is unsafe. You can also build it yourself
from source (below) if you prefer.

---

## Building the executable yourself

```
setup.bat          :: one-time: creates .venv and installs dependencies
build_exe.bat      :: builds dist\SeaglassEditor.exe (one-file, windowed)
```

To add an icon, drop a multi-resolution `app.ico` in the project folder before
running `build_exe.bat`; it is picked up automatically.

Releases are also built automatically on GitHub when a tag like `v0.1.0` is
pushed (see `.github/workflows/release.yml`).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the code layout and the
pull-request process. Contributions are welcome.

---

## Notes and disclaimer

- This tool edits **your own save**. Always **back up** your save before
  editing (the **Save As...** button writes to a new file for exactly this
  reason).
- Editing values that the game validates on load (e.g. impossible moves) may
  cause in-game quirkiness -- the editor does not enforce full legality.
- The PC box view is **read-only** in this version; box editing and `.pk3`
  import are planned.
- Not affiliated with Nintendo, Game Freak, or the Seaglass team. Pokemon and
  related assets are trademarks of their respective owners.

---

## License

MIT -- see [LICENSE](LICENSE).

## Credits
- Reference behaviour cross-checked against PKHeX `.pk3` files.
- Built with [PySide6](https://doc.qt.io/qtforpython/).
