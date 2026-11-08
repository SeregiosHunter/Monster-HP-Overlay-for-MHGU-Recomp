# Monster HP Overlay for MHGU Recomp

> [!IMPORTANT]
> **I recommend you to back up your save file every time you test any mods.**

An on-screen monster HP overlay for **Monster Hunter Generations Ultimate running on [MHGURecomp](https://github.com/morerokk/MHGURecomp)** (Windows).

It shows each monster as a small card: name, size and crown, a colour-changing HP bar with the exact numbers, and a bar for each abnormal status (Poison, Paralysis, Rage timer and so on). The look is inspired by [HunterPie](https://github.com/HunterPie/HunterPie).

<!-- Add a screenshot here: drag an image into the GitHub editor and it will insert the line for you. -->

## Features

- Monster cards with name, size multiplier, crown (Gold, Silver, Mini) and HP as numbers and percentage.
- HP bar that changes colour as the monster gets weaker (green, yellow, red).
- Abnormal status bars: Poison, Sleep, Paralysis, Dizzy, Exhaust, Jump, Blast and the Rage timer.
- Compact cards for small monsters.
- **Ctrl + Alt + O** shows or hides the overlay without closing it. It keeps reading the game while hidden.
- Reads game memory only. It does not modify the game or any of its files.

## Requirements

- Windows.
- [MHGURecomp](https://github.com/morerokk/MHGURecomp) running Monster Hunter Generations Ultimate.
- Tested with MHGURecomp 0.15.1. A different Recomp version may move the data this overlay reads (see [Known limitations](#known-limitations)).

## How to use

1. Download the latest `.zip` from the [Releases](../../releases) page and extract it into its own folder. **Keep all the files together**, including the `lib` folder.
2. Start MHGURecomp and enter a hunt.
3. Run `MHGU-MHXX-HP-Overlay.exe` from the extracted folder. Close any other copy of the overlay first.
4. The first scan can take a few seconds. The console shows `[Recomp] Scanned ... monster candidate(s)` when it finds monsters.
5. Press **Ctrl + Alt + O** any time to hide or show the cards.

## Configuration

Edit `config.ini` with a text editor and restart the overlay for changes to apply.

| Option | Default | What it does |
|---|---|---|
| `toggle_hotkey` | `^!o` | Shortcut that shows or hides the overlay. Uses [AutoHotkey hotkey symbols](https://www.autohotkey.com/docs/v1/Hotkeys.htm#Symbols) (`^` Ctrl, `!` Alt, `+` Shift, `#` Win). |
| `font_size` | `18` | Scales the **whole card** (text, bars and width). Try 22 or 26 for a bigger overlay. |
| `font_family` | `Segoe UI, Arial` | Fonts, comma separated. |
| `show_initial_hp` | `true` | Show the maximum HP next to the current HP. |
| `show_hp_percentage` | `true` | Show the HP percentage. |
| `show_small_monsters` | `true` | Also show small monsters. |
| `show_size_multiplier` | `true` | Show the size, for example `x100`. |
| `show_crown` | `true` | Show the Gold, Silver or Mini badge. |
| `show_abnormal_status` | `true` | Show status bars inside the cards. |
| `always_show_abnormal_status` | `true` | Keep `true` on Recomp (see below). |
| `x`, `y` | `100`, `0` | Position as a percentage of the game window (100, 0 is the top right corner). |
| `fix_x`, `fix_y` | `0` | Extra offset in pixels. |
| `text_color`, `background_color` | `white`, `black` | Any [CSS SVG colour name](https://upload.wikimedia.org/wikipedia/commons/2/2b/SVG_Recognized_color_keyword_names.svg). |
| `text_opacity`, `background_opacity` | `100`, `75` | 1 to 100. |
| `hp_update_time` | `0.6` | Seconds between HP updates. Raise it if the overlay uses too much CPU. |
| `max_workers` | `2` | Threads used by the memory scan. |
| `debugger` | `false` | Writes a `.log` file for troubleshooting. |

Options inherited from the original project that **no longer change anything** in this version: `font_weight`, `align`, `abnormal_status_*` colours and opacities, `emu_hide_ui`. `hotkey` (borderless mode) comes from the original emulator overlay and is not needed on Recomp.

## Known limitations

- **Experimental.** It is not guaranteed to work with every MHGURecomp version. The overlay finds monsters by scanning the game's memory and reads fields at fixed offsets, so a Recomp update that changes the memory layout can break it.
- **Status bars show for every monster.** The original overlay only showed the status of the monster you were targeting, but it cannot detect the target on Recomp, so status is always shown for all large monsters (`always_show_abnormal_status = true`).
- The first scan after entering a hunt can take several seconds.
- If the overlay does not show anything, check the console for the `[Recomp] Scanned ...` line and open an issue with its text.

## Building from source

Requires Windows, Python 3.12 and the Microsoft C++ build tools (the memory scanner is a small C extension).

```
python -m venv .venv
.venv\Scripts\activate
pip install .
build
```

The result is in `build\dist`. The repository also has a GitHub Actions workflow (`.github/workflows/build.yml`) that builds it on every push to `main`; the output is attached to the run as an artifact.

## What changed from the original

This project is a fork of version 1.1.1 of [MHGU-MHXX-HP-Overlay-For-Switch-Emulator](https://github.com/Alexander-Lancellott/MHGU-MHXX-HP-Overlay-For-Switch-Emulator) by Alexander-Lancellott.

- `modules/recomp_window.py`: finds the MHGURecomp window and places the overlay on its client area.
- `modules/recomp_memory.py`: reads MHGURecomp's memory (guest address base `0x10000000000`, committed heap pages only) with the original monster signature and field offsets.
- `modules/widgets.py`: the new card widget and `overlay.py`: the show/hide hotkey.

## Credits and license

- Original overlay and memory research: [Alexander-Lancellott](https://github.com/Alexander-Lancellott).
- MHGURecomp: [morerokk](https://github.com/morerokk/MHGURecomp).
- Visual inspiration: [HunterPie](https://github.com/HunterPie/HunterPie).

Released under the **GPL-3.0** license, the same as the original project. See [LICENSE](LICENSE).
