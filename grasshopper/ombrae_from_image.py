# -*- coding: utf-8 -*-
"""Ombrae-style optical tile panel, built from an image. One GhPython component.

Drop this into a GhPython Script component (GH1 / IronPython 2.7, or Rhino 8's Python 3 —
it is written to run in both) and wire the inputs below. It does the whole job: reads the
picture, samples it on the tile grid, solves each tile's hinge rotation for the tone it has
to carry, and builds the geometry.

WHY A HINGE ANGLE. Every tile is the same disc at the same tilt. Turning the hinge in plan
sweeps the disc's normal around a cone, so the amount of light it returns to someone
standing in front changes smoothly:

    n . L  =  sin(tilt) * R * sin(theta - phi)  +  cos(tilt) * Lz

with L the sun, R = hypot(Lx,Ly) and phi = atan2(Ly,Lx). That is monotonic in theta over
half a turn, so it inverts exactly, and a target tone t in 0..1 becomes

    theta = phi + asin(2t - 1)

The picture is therefore solved for ONE sun. Away from it the panel washes out; that is
the effect, not a defect.

INPUTS  (set the type hint in brackets; everything except Img has a sensible default)
    Img        [str]   path to the image file
    W, H       [float] panel size, mm                        default 2400 x 1200
    Thick      [float] backing plate thickness, mm           default 3
    Frame      [float] border kept clear of tiles, mm        default 25
    TileD      [float] tile diameter, mm                     default 25.4   (1")
    Pitch      [float] grid spacing, mm                      default 31.75  (1.25")
    RowPitch   [float] row spacing as a multiple of Pitch    default 0.8
    Stagger    [float] odd-row offset, 0..0.5 of Pitch       default 0.5
    Tilt       [float] tile tilt out of the face, degrees    default 30
    Rise       [float] clearance under the tile's low edge   default 3
    TileT      [float] tile thickness, mm                    default 2
    DesignAz   [float] the sun the picture is tuned to, deg  default 40
    DesignEl   [float] its elevation, deg                    default 30
    Contrast   [float] tone contrast                          default 1.25
    Gamma      [float] tone gamma                             default 1.0
    Bright     [float] tone offset, -0.5..0.5                 default 0
    Levels     [int]   tone steps, 0 = continuous             default 0
    Dither     [bool]  break up banding                       default True
    Invert     [bool]                                          default False
    Fit        [str]   "cover" | "contain" | "stretch"        default "cover"
    Solid      [bool]  build solid tiles; False = flat discs, much faster
    Go         [bool]  set True to build

OUTPUTS
    Plate      the backing panel
    Tiles      one brep per tile
    Hinges     the plan hinge line of each tile, for the shop drawing
    Angles     hinge angle per tile, degrees
    Tones      target tone per tile, 0..1
    Csv        the same schedule the web tool exports, so the two agree
    Info       what it did, and anything it had to warn about
"""
from __future__ import division
import math
import Rhino.Geometry as rg

# ---------------------------------------------------------------- defaults
def d(v, fallback):
    return fallback if v is None else v

W        = float(d(globals().get('W'), 2400.0))
H        = float(d(globals().get('H'), 1200.0))
Thick    = float(d(globals().get('Thick'), 3.0))
Frame    = float(d(globals().get('Frame'), 25.0))
TileD    = float(d(globals().get('TileD'), 25.4))
Pitch    = float(d(globals().get('Pitch'), 31.75))
RowPitch = float(d(globals().get('RowPitch'), 0.8))
Stagger  = float(d(globals().get('Stagger'), 0.5))
Tilt     = float(d(globals().get('Tilt'), 30.0))
Rise     = float(d(globals().get('Rise'), 3.0))
TileT    = float(d(globals().get('TileT'), 2.0))
DesignAz = float(d(globals().get('DesignAz'), 40.0))
DesignEl = float(d(globals().get('DesignEl'), 30.0))
Contrast = float(d(globals().get('Contrast'), 1.25))
Gamma    = float(d(globals().get('Gamma'), 1.0))
Bright   = float(d(globals().get('Bright'), 0.0))
Levels   = int(d(globals().get('Levels'), 0))
Dither   = bool(d(globals().get('Dither'), True))
Invert   = bool(d(globals().get('Invert'), False))
Fit      = str(d(globals().get('Fit'), 'cover'))
Solid    = bool(d(globals().get('Solid'), True))
Go       = bool(d(globals().get('Go'), True))
Img      = globals().get('Img')

BAYER = [(v + 0.5) / 16.0 - 0.5 for v in
         [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]]


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# ---------------------------------------------------------------- the tone field
class Field(object):
    """Whatever the source is, it ends up as one luminance raster sampled in 0..1."""

    def __init__(self, path, cols, rows, fit):
        self.w = max(8, cols * 2)
        self.h = max(8, rows * 2)
        self.lum = None
        self.note = ''
        if not path:
            self.note = 'no image given, using a diagonal tone ramp'
            self._ramp()
            return
        try:
            import System.Drawing as sd
            src = sd.Bitmap(path)
            sw, sh = float(src.Width), float(src.Height)
            # cover crops, contain letterboxes, stretch distorts
            if fit == 'stretch':
                dw, dh = float(self.w), float(self.h)
            else:
                k = (max(self.w / sw, self.h / sh) if fit == 'cover'
                     else min(self.w / sw, self.h / sh))
                dw, dh = sw * k, sh * k
            dst = sd.Bitmap(self.w, self.h)
            g = sd.Graphics.FromImage(dst)
            g.Clear(sd.Color.Black)
            g.InterpolationMode = sd.Drawing2D.InterpolationMode.HighQualityBicubic
            g.DrawImage(src, sd.Rectangle(int((self.w - dw) / 2), int((self.h - dh) / 2),
                                          int(dw), int(dh)))
            g.Dispose()
            self.lum = [0.0] * (self.w * self.h)
            for j in range(self.h):
                for i in range(self.w):
                    p = dst.GetPixel(i, j)
                    self.lum[j * self.w + i] = (0.299 * p.R + 0.587 * p.G + 0.114 * p.B) / 255.0
            dst.Dispose()
            src.Dispose()
        except Exception as ex:
            self.note = 'could not read "%s" (%s), using a tone ramp instead' % (path, ex)
            self._ramp()

    def _ramp(self):
        self.lum = [0.0] * (self.w * self.h)
        for j in range(self.h):
            for i in range(self.w):
                self.lum[j * self.w + i] = clamp((i / float(self.w - 1) +
                                                  (1 - j / float(self.h - 1))) / 2.0, 0, 1)

    def at(self, u, v):
        """bilinear, u and v in 0..1 with v measured down the image"""
        x = clamp(u * (self.w - 1), 0, self.w - 1)
        y = clamp(v * (self.h - 1), 0, self.h - 1)
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        x1, y1 = min(x0 + 1, self.w - 1), min(y0 + 1, self.h - 1)
        fx, fy = x - x0, y - y0
        a = self.lum[y0 * self.w + x0] * (1 - fx) + self.lum[y0 * self.w + x1] * fx
        b = self.lum[y1 * self.w + x0] * (1 - fx) + self.lum[y1 * self.w + x1] * fx
        return a * (1 - fy) + b * fy


# ---------------------------------------------------------------- the solve
def sun(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return (math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e))


def build():
    notes = []
    x0, y0 = Frame, Frame
    x1, y1 = W - Frame, H - Frame
    px = max(TileD * 0.3, Pitch)
    py = max(TileD * 0.3, Pitch * RowPitch)
    avail_x, avail_y = (x1 - x0) - TileD, (y1 - y0) - TileD
    if avail_x < 0 or avail_y < 0:
        return None, [], [], [], [], '', 'the frame leaves no room for a tile this size'
    cols = int(math.floor(avail_x / px)) + 1
    rows = int(math.floor(avail_y / py)) + 1
    if cols * rows > 40000:
        return None, [], [], [], [], '', '%d tiles is more than this will build' % (cols * rows)

    field = Field(Img, cols, rows, Fit)
    if field.note:
        notes.append(field.note)

    a = math.radians(Tilt)
    L = sun(DesignAz, DesignEl)
    R = math.hypot(L[0], L[1])
    phi = math.atan2(L[1], L[0])
    if math.sin(a) * R < 0.06:
        notes.append('the design sun is almost square-on to the panel, so turning a tile '
                     'barely changes its tone. Move it off the face: more azimuth, or higher.')

    stag = Stagger * px if rows > 1 else 0.0
    gx = x0 + TileD / 2.0 + (avail_x - ((cols - 1) * px + stag)) / 2.0
    gy = y0 + TileD / 2.0 + (avail_y - (rows - 1) * py) / 2.0

    r = TileD / 2.0
    zc = Thick + Rise + r * math.sin(a) + TileT / 2.0
    step = (1.0 / (Levels - 1)) if Levels > 1 else 0.0

    tiles, hinges, angles, tones, csv = [], [], [], [], ['tile,col,row,x_mm,y_mm,hinge_deg,tilt_deg,tone']
    k = 0
    for j in range(rows):
        for i in range(cols):
            cx = gx + i * px + (stag if (j % 2) else 0.0)
            cy = gy + j * py
            if cx > x1 - TileD / 2.0 + 0.01:
                continue
            u = (cx - x0) / max(1.0, x1 - x0)
            v = 1.0 - (cy - y0) / max(1.0, y1 - y0)
            t = field.at(u, v)
            t = (t - 0.5) * Contrast + 0.5 + Bright
            t = math.pow(clamp(t, 0, 1), Gamma)
            if Invert:
                t = 1.0 - t
            if Dither:
                t += BAYER[(j % 4) * 4 + (i % 4)] * (step if step else 0.055)
            t = clamp(t, 0, 1)
            if step:
                t = round(t / step) * step

            theta = phi + math.asin(clamp(2 * t - 1, -1, 1))
            tilt = a
            n = rg.Vector3d(math.sin(tilt) * math.sin(theta),
                            -math.sin(tilt) * math.cos(theta),
                            math.cos(tilt))
            centre = rg.Point3d(cx, cy, zc)
            pl = rg.Plane(centre - n * (TileT / 2.0), n)
            cir = rg.Circle(pl, r)
            if Solid:
                tiles.append(rg.Cylinder(cir, TileT).ToBrep(True, True))
            else:
                tiles.append(rg.Brep.CreatePlanarBreps([cir.ToNurbsCurve()], 0.01)[0])

            ux, uy = math.cos(theta), math.sin(theta)
            hinges.append(rg.Line(rg.Point3d(cx - ux * r, cy - uy * r, Thick),
                                  rg.Point3d(cx + ux * r, cy + uy * r, Thick)))
            deg = math.degrees(theta) % 360.0
            angles.append(deg)
            tones.append(t)
            k += 1
            csv.append('%d,%d,%d,%.2f,%.2f,%.2f,%.2f,%.4f'
                       % (k, i + 1, j + 1, cx, cy, deg, math.degrees(tilt), t))

    plate = rg.Brep.CreateFromBox(rg.BoundingBox(rg.Point3d(0, 0, 0), rg.Point3d(W, H, Thick)))
    lo, hi = (min(tones), max(tones)) if tones else (0, 0)
    info = ('%d tiles on a %d x %d grid, Ø%.1f mm at %.2f mm, tilted %.0f deg.\n'
            'Tuned to a sun at %.0f / %.0f deg. Tones span %.2f to %.2f.'
            % (len(tiles), cols, rows, TileD, Pitch, Tilt, DesignAz, DesignEl, lo, hi))
    if hi - lo < 0.55:
        notes.append('the image only spans %d%% of the tonal range — it will read flat'
                     % int((hi - lo) * 100))
    if notes:
        info += '\nNOTE: ' + '; '.join(notes)
    return plate, tiles, hinges, angles, tones, '\n'.join(csv), info


if Go:
    Plate, Tiles, Hinges, Angles, Tones, Csv, Info = build()
else:
    Plate, Tiles, Hinges, Angles, Tones, Csv, Info = None, [], [], [], [], '', 'set Go to True'
