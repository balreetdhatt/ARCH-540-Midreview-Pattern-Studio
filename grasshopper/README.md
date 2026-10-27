# Ombrae-style optical tiles in Grasshopper

Two GhPython components that build the same panel Pattern Studio draws in the browser.
Written for ARCH 540 coursework.

> **Attribution.** Ombrae™, OpticalTile™ and Sculptural Imaging™ are marks of
> Ombrae Studios Inc. and Keith Panel Systems. The geometry here was reconstructed from the
> dimensions KPS publish for their panels — Ø½" or 1" tiles on a 1¼" grid, tilted about 30°,
> standing roughly 3 mm proud — and from the stated principle that each tile reflects a
> varying tone of light. **This is not their process and not their software.** Anything built
> from it needs their licence. Keep this notice with the files.

---

## The two components

| file | what it does |
|---|---|
| `ombrae_from_image.py` | the whole job inside Grasshopper: reads a picture, samples it on the tile grid, solves each tile's hinge angle, builds the geometry |
| `ombrae_from_csv.py` | rebuilds a panel from the `-tiles.csv` that Pattern Studio exports — nothing is re-solved, so the browser and Rhino agree tile for tile |

`ombrae_from_image.gh` is the first component already set up in Rhino 8 (Python 3 Script) with
the canvas below — File Path → `Img`, sliders for W, H, TileD, Pitch, Tilt, DesignAz, DesignEl
and Contrast, toggles for `Solid` (off) and `Go`, panels on `Info` and `Angles`. Open it and
right-click **Image file** → *Select one existing file*. Inputs are left on the "Any" type hint;
the script casts every value itself, so that is fine.

Use the first when you want to drive the design from Grasshopper. Use the second when the
design was settled in the browser and Rhino just has to build it.

## Setting one up

1. Drop a **GhPython Script** component on the canvas (Rhino 7/GH1, or Rhino 8 — the code
   runs under IronPython 2.7 and CPython 3 alike).
2. Open it, paste the file's contents in, and save.
3. Right-click the component → add the inputs you want to drive, named exactly as in the
   file's docstring, and set each one's **type hint** (`float`, `int`, `bool`, `str`).
   Any input you leave off falls back to a sensible default, so you can start with just
   `Img` and `Go` and add sliders as you go.
4. Right-click → rename the outputs to `Plate`, `Tiles`, `Hinges`, `Angles`, `Tones`,
   `Csv`, `Info`.

A reasonable canvas, matching the groups in the reference definition:

```
  [File Path]──Img ─┐
  [Panel W] ────────┤
  [Panel H] ────────┤
  [Slider TileD]────┤                      ┌── Plate  ──→ [Custom Preview, grey]
  [Slider Pitch]────┼──→ OMBRAE FROM IMAGE ┼── Tiles  ──→ [Custom Preview, metal]
  [Slider Tilt] ────┤                      ├── Hinges ──→ [Custom Preview, green]  (shop drawing)
  [Slider Az] ──────┤                      ├── Angles ──→ [Panel]                  (the schedule)
  [Slider El] ──────┤                      ├── Csv    ──→ [Write File]             (hand-off)
  [Slider Contrast]─┤                      └── Info   ──→ [Panel]                  (read this)
  [Toggle Go] ──────┘
```

Keep `Solid` off while you are moving sliders — flat discs rebuild in a fraction of the time —
and turn it on for the final bake.

## How it works

Every tile is the same disc at the same tilt. What changes from tile to tile is the plan angle
of the hinge it is folded along. Turning that hinge sweeps the disc's normal around a cone, so
the light it returns to someone standing in front changes smoothly:

```
n · L  =  sin(tilt)·R·sin(θ − φ)  +  cos(tilt)·Lz
```

where `L` is the sun, `R = hypot(Lx, Ly)` and `φ = atan2(Ly, Lx)`. That is monotonic in `θ`
over half a turn, so it inverts exactly. A tone `t` from 0 (darkest) to 1 (brightest) becomes:

```
θ  =  φ  +  asin(2t − 1)
```

Two consequences worth knowing before you build anything:

- **The picture is solved for one sun.** Move the sun away from `DesignAz` / `DesignEl` and
  the image washes out. That is the effect these panels are sold on, not a fault.
- **A square-on sun has no range.** When the sun is near the panel's own normal, `R` is small,
  every hinge angle gives nearly the same tone, and the panel reads as flat grey. The
  component says so in `Info`. `R` measures how far the sun is off the panel's own face, so
  the fix is to move it *off* the face: swing it round in azimuth, or raise it. Azimuth
  35–65° with elevation 20–45° suits a wall that takes the afternoon; azimuth 0° at
  elevation 5°, straight at the panel, is the dead case.

## Checking it against the browser

The two must agree. To prove it on your own machine:

1. In Pattern Studio, set up a tile panel and export the fabrication bundle.
2. Unzip it and wire `<name>-tiles.csv` into `ombrae_from_csv.py`.
3. Wire the same image and the same settings into `ombrae_from_image.py`.
4. The two tile sets should land on top of each other. If they do not, the `hinge_deg`
   column and the component's `Angles` output will show you where they part company — and
   one of the two has a bug worth finding.

## What has been tested

Run in Rhino 8's Python 3 Script component (Oct 2026), `ombrae_from_image.py` only:

- solves with no errors or warnings — 3,308 tiles on a 74 × 45 grid at the default settings;
- with no image it falls back to the tone ramp and says so in `Info`;
- reads an image through `System.Drawing` under Python 3, the right way up: a black disc on a
  white ground gave mean tone 0.01 for tiles inside the disc and 0.99 at the sides;
- `Solid` on builds 3,308 solid tiles in about 4.7 s; off gives flat discs.

**Not yet run:** `ombrae_from_csv.py`, the browser-vs-Rhino check above, the IronPython 2
component, and a visual inspection of the tiles in the viewport.

## Limits, honestly

- `GetPixel` is slow, so the image is downsampled to twice the tile grid before sampling.
  Fine for a panel; do not expect it to hold fine detail.
- There is no shading or reflectance model here — Rhino renders the real geometry, which is
  better than any approximation. The browser's 2D view is the approximation.
- Tiles are modelled as free-standing discs on a backing plate. On a real panel they are
  formed from the sheet itself, so the back face of a built panel will not look like this.
- Nothing here does panelisation, joints, fixings or edge conditions.
