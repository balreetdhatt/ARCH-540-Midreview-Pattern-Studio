# Pattern Studio — ARCH 540 mid-review package

Balreet Dhatt · Assignment 2 · state of the work on 23 October 2026 (mid-review).

A motif, a photograph or a sentence → rules → a panel → cut files. Pattern Studio is a single-file web tool that reads a pattern's symmetry from a photograph, reads a brief into editable settings, and builds one picture three ways (cut screen, tilted optical tiles, perforated image) with real stock gauges and fabrication checks, then exports DXF, STL and a tile schedule.

## Links

- **Slides**: `index.html` in this repository (with GitHub Pages: the repository's front page).
- **Tool, frozen as it stood on 23 October 2026 before 1 pm**: https://claude.ai/artifact/9rXMyBMiEa2braopF7yDky (the same file as `pattern-studio.html` here).

## What is here

| File | What it is |
|---|---|
| `pattern-studio.html` | The tool. Open in Chrome. One file, no install; it loads three.js and two Google fonts from the web. |
| `index.html` | The five-minute mid-review deck. Open in a browser; arrow keys move between slides. Uses `demo.mp4` and `img/`. |
| `demo.mp4` | The recorded walkthrough shown in the deck. |
| `diagrams.html` | The three mid-review diagrams: as-is workflow, case study, tool logic. |
| `img/` | Stills used by the deck. |
| `proposal-150-words.txt` | The 150-word proposal. |
| `grasshopper/` | Rhino/Grasshopper scripts that rebuild an optical-tile panel from the tool's CSV or from an image, with their own README. |

## Opening it

Clone or download the repository and double-click `index.html` for the deck or `pattern-studio.html` for the tool. If the repository is served with GitHub Pages, the deck is the site's front page and the tool is at `/pattern-studio.html`.

## Using the tool

1. **Source**: pick a built-in pattern or photograph, or describe a panel in a sentence and let the reader fill the settings.
2. **Pattern / Tiles / Perforated**: adjust cell, bar, thickness, tile pitch and tilt, or hole size and pitch. The checks on the right flag anything that cannot be cut or will not stand up.
3. **Finish**: material, frame, light and room.
4. **Deliver**: DXF for the cutter, STL for the model, CSV tile schedule, and a drawing sheet, each with provenance.
