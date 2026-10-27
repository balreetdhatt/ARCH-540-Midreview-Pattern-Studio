# -*- coding: utf-8 -*-
"""Build the panel from a tile schedule the web tool exported. One GhPython component.

This is the interop piece. Pattern Studio's fabrication bundle contains
<name>-tiles.csv, one row per tile:

    tile,col,row,x_mm,y_mm,hinge_deg,tilt_deg,tone

Point this component at that file and Grasshopper builds exactly the panel the browser
drew — same tiles, same angles, same positions. Nothing is re-solved here, so if the two
ever disagree it is a bug in one of them, not a difference of opinion.

Use ombrae_from_image.py instead when you want Grasshopper to do the solving itself.

INPUTS
    Csv      [str]   path to the -tiles.csv file, OR the file's contents as one string
    TileD    [float] tile diameter, mm      default 25.4
    TileT    [float] tile thickness, mm     default 2
    Thick    [float] backing plate, mm      default 3
    Rise     [float] clearance under the low edge, mm   default 3
    W, H     [float] panel size, mm; 0 means "work it out from the tile extents"
    Solid    [bool]  solid tiles, or flat discs when False
    Go       [bool]

OUTPUTS
    Plate, Tiles, Hinges, Angles, Tones, Count, Info
"""
from __future__ import division
import math
import os
import Rhino.Geometry as rg


def d(v, fallback):
    return fallback if v is None else v


Csv   = globals().get('Csv')
TileD = float(d(globals().get('TileD'), 25.4))
TileT = float(d(globals().get('TileT'), 2.0))
Thick = float(d(globals().get('Thick'), 3.0))
Rise  = float(d(globals().get('Rise'), 3.0))
W     = float(d(globals().get('W'), 0.0))
H     = float(d(globals().get('H'), 0.0))
Solid = bool(d(globals().get('Solid'), True))
Go    = bool(d(globals().get('Go'), True))


def read_rows(src):
    """Accept a path or the raw text, and be forgiving about column order."""
    if not src:
        return [], 'nothing wired to Csv'
    text = src
    if '\n' not in src and os.path.exists(src):
        f = open(src, 'r')
        text = f.read()
        f.close()
    lines = [ln.strip() for ln in text.replace('\r', '').split('\n') if ln.strip()]
    if not lines:
        return [], 'the file is empty'
    head = [h.strip().lower() for h in lines[0].split(',')]
    need = ['x_mm', 'y_mm', 'hinge_deg', 'tilt_deg']
    if not all(h in head for h in need):
        return [], ('the header is "%s"; this wants a Pattern Studio tile schedule with '
                    'x_mm, y_mm, hinge_deg and tilt_deg' % lines[0][:70])
    ix = dict((h, head.index(h)) for h in head)
    rows, bad = [], 0
    for ln in lines[1:]:
        c = ln.split(',')
        if len(c) < len(head):
            bad += 1
            continue
        try:
            rows.append((float(c[ix['x_mm']]), float(c[ix['y_mm']]),
                         float(c[ix['hinge_deg']]), float(c[ix['tilt_deg']]),
                         float(c[ix['tone']]) if 'tone' in ix else 0.5))
        except ValueError:
            bad += 1
    note = ('%d rows could not be read and were skipped' % bad) if bad else ''
    return rows, note


def build():
    rows, note = read_rows(Csv)
    if not rows:
        return None, [], [], [], [], 0, (note or 'no tiles')

    r = TileD / 2.0
    xs = [q[0] for q in rows]
    ys = [q[1] for q in rows]
    w = W if W > 0 else max(xs) + min(xs)
    h = H if H > 0 else max(ys) + min(ys)

    tiles, hinges, angles, tones = [], [], [], []
    for (x, y, hdeg, tdeg, tone) in rows:
        th = math.radians(hdeg)
        a = math.radians(tdeg)
        n = rg.Vector3d(math.sin(a) * math.sin(th), -math.sin(a) * math.cos(th), math.cos(a))
        zc = Thick + Rise + r * math.sin(a) + TileT / 2.0
        centre = rg.Point3d(x, y, zc)
        pl = rg.Plane(centre - n * (TileT / 2.0), n)
        cir = rg.Circle(pl, r)
        if Solid:
            tiles.append(rg.Cylinder(cir, TileT).ToBrep(True, True))
        else:
            tiles.append(rg.Brep.CreatePlanarBreps([cir.ToNurbsCurve()], 0.01)[0])
        ux, uy = math.cos(th), math.sin(th)
        hinges.append(rg.Line(rg.Point3d(x - ux * r, y - uy * r, Thick),
                              rg.Point3d(x + ux * r, y + uy * r, Thick)))
        angles.append(hdeg)
        tones.append(tone)

    plate = rg.Brep.CreateFromBox(rg.BoundingBox(rg.Point3d(0, 0, 0), rg.Point3d(w, h, Thick)))
    info = ('%d tiles rebuilt from the schedule, Ø%.1f mm, panel %.0f x %.0f mm.'
            % (len(tiles), TileD, w, h))
    if W <= 0 or H <= 0:
        info += '\nPanel size was inferred from the tile extents; wire W and H for the real one.'
    if note:
        info += '\nNOTE: ' + note
    return plate, tiles, hinges, angles, tones, len(tiles), info


if Go:
    Plate, Tiles, Hinges, Angles, Tones, Count, Info = build()
else:
    Plate, Tiles, Hinges, Angles, Tones, Count, Info = None, [], [], [], [], 0, 'set Go to True'
