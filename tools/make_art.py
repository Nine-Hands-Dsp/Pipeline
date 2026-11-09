"""
PIPELINE (NINE HANDS | DSP) - visuel du plugin, entierement reconstruit (nov. 2026) : pedale simple, 1235 x 1800.

Methode de Screamer (tools/make_art.py) : dessin dans un repere de travail 760 x 958 unites, rendu en 4K
(AS = 4 pixels par unite, boitier, arete, peinture et vagues sur-echantillonnes), puis recadrage sur boitier + jacks
et reduction en 1235 x 1800 (meme echelle en largeur et en hauteur). Canal alpha = boitier + embases jack :
transparent seulement autour des jacks et dans les coins arrondis.

Boitier alu peint bleu ocean metallise, vagues de design/source/Pipeline-vagues.svg (bleu #5596b9 + ecume #efe4ca),
ecran noir (texte et oscilloscope dessines par le plugin). Pieces photo du kit NINE HANDS | DSP (tools/photo_controls.py) :
potards moletes (photo de l'utilisateur, repere et point effaces), LED bleue a facettes, footswitch d'Echoflex, embases jack.
Une seule lumiere : en haut a gauche (ombres vers le bas a droite).

Textes, graduations, filets, cadre interieur, logo NINE HANDS | DSP et vagues sont aussi dessines en VECTORIEL par
le plugin (Poppins, NineHandsLogo.svg, PipelineWaves.svg), nets a toutes les tailles : ils ne sont pas imprimes dans le fond
(les vagues sont aussi cuites a plat dans le fond ; les commandes et leurs ombres sont dans un calque separe, controls.png,
que le plugin pose au-dessus des vagues vectorielles).

Sorties : background.png (boitier, vagues, ecran), controls.png (commandes + ombres), glow_led.png, led_on.png, Layout.h, tools/layout.json,
          design/Pipeline_fond_4K.png (fond 4K, reference)
Usage : python3 tools/make_art.py
"""
import os, sys, math, subprocess, json, re
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import photo_controls as PC

AS = 4                                   # 4 pixels par unite : rendu 4K (3040 x 3832) puis reduction
UW, UH = 760, 958
W, H = UW * AS, UH * AS
L = np.array([-0.46, -0.62, 0.64]); L /= np.linalg.norm(L)
V = np.array([0.0, 0.0, 1.0]); HV = (L + V) / np.linalg.norm(L + V)

# ------------------------------------------------------------------ geometrie (unites de travail)
OUT_W, OUT_H = 1235, 1800
JACK_LEN = 104.0
_jtest = PC.jack_sprite(JACK_LEN, AS, 1)
JACK_PROT = _jtest[1] - 1.5 / AS
PY0, PH, PR = 34.0, 890.0, 30.0
PW = OUT_W / OUT_H * PH - 2 * JACK_PROT
PX0 = (UW - PW) / 2
CX = PX0 + PW / 2
CROP_X0, CROP_W = PX0 - JACK_PROT, PW + 2 * JACK_PROT
SC = (OUT_H / 2.0) / PH                          # unites de travail -> unites du plugin (617,5 x 900)

# positions validees en v1.4.3 (repere 760 x 958, boitier 529 x 940 a partir de y = 12), ramenees au nouveau boitier
KX = PW / 529.0
def YO(y): return PY0 + (y - 12.0) * PH / 940.0
FR_IN, FR_R, FR_W = 15.0, 19.0, 1.7             # cadre interieur (filet creme) : retrait, rayon, epaisseur
FACE = (PX0 + FR_IN, PY0 + FR_IN, PW - 2 * FR_IN, PH - 2 * FR_IN)
LED = (CX, YO(69.0) + 2.0)
KNOB_R = 60.0                                   # potards agrandis comme Screamer (nov. 2026)
KNOBS = [(CX - 136.5 * KX, YO(202.6), 'RATE'), (CX + 136.5 * KX, YO(202.6), 'DEPTH')]
MODE = (CX, YO(397.7)); MODE_R = 50.5
MODE_FIRST, MODE_STEP = -150.0, 300.0 / 7.0
MODE_NAMES = ['SINE', 'TRI', 'RAMP', 'SQR', 'RAND', 'ENV D', 'ENV R', 'ENV P']
LBL_OFF = [(-44.0, 72.0), (-90.0, 26.5), (-84.0, -39.5), (-32.0, -78.5), (31.5, -78.5), (85.0, -39.5), (90.0, 26.5), (43.5, 72.0)]
LBL_K = (MODE_R + 38.0) / (46.0 + 38.0)          # etiquettes repoussees avec le selecteur agrandi
LABELS = [(MODE[0] + dx * KX * LBL_K, MODE[1] + dy * PH / 940.0 * LBL_K) for dx, dy in LBL_OFF]
TITLE_Y = YO(562.0); SUB_Y = YO(616.0)
SCREEN = (CX - 227.0 * KX / 1.074 * 1.0, YO(649.0), 454.0, 113.0 * PH / 940.0)     # verre de l'ecran
ROW = (SCREEN[0] + 9.0, SCREEN[1] + 7.0, SCREEN[2] - 18.0, 47.0)                   # ligne d'etat + oscilloscope
BAR = (SCREEN[0] + 15.0, ROW[1] + ROW[3] + 4.0, SCREEN[2] - 30.0, 34.0)             # barre de presets
FS = (CX, YO(840.75) - 6.0)
FS_FLATS = 100.0
LOGO_C = (CX, PY0 + PH - FR_IN - 19.0)
LOGO_W = 168.0
JACK_Y = TITLE_Y
# vagues (PipelineWaves.svg, coordonnees d'origine) : largeur = largeur du cadre interieur, creux du titre sur le titre
WV_X0, WV_W, WV_TOP, WV_H, WV_TITLE = 211.0, 813.0, 602.6, 1077.9, 1062.6
WV_KX = FACE[2] / WV_W
WV_KY = WV_KX * 0.94
def wave_xf(x, y): return FACE[0] + (x - WV_X0) * WV_KX, TITLE_Y + (y - WV_TITLE) * WV_KY

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
UX, UY = (XX + 0.5) / AS, (YY + 0.5) / AS
del YY, XX

def rrect_sd(x, y, x0, y0, w, h, r):
    cx, cy = x0 + w / 2, y0 + h / 2
    qx = np.abs(x - cx) - (w / 2 - r); qy = np.abs(y - cy) - (h / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

def fbm(shape, scales, amps, seed=0):
    r = np.random.default_rng(seed); out = np.zeros(shape, np.float32)
    for s, a in zip(scales, amps):
        n = r.standard_normal((max(2, shape[0] // s + 2), max(2, shape[1] // s + 2))).astype(np.float32)
        out += a * cv2.resize(n, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return out

def over(dst, rgba, x0, y0):
    h, w = rgba.shape[:2]
    X0, Y0 = int(round(x0)), int(round(y0))
    sx0, sy0 = max(0, -X0), max(0, -Y0)
    ex, ey = min(w, W - X0), min(h, H - Y0)
    a = rgba[sy0:ey, sx0:ex, 3:4] / 255.0
    reg = dst[Y0 + sy0:Y0 + ey, X0 + sx0:X0 + ex]
    dst[Y0 + sy0:Y0 + ey, X0 + sx0:X0 + ex] = reg * (1 - a) + rgba[sy0:ey, sx0:ex, :3] * a

print('boitier 4K...')
# ------------------------------------------------------------------ 1. boitier : peinture bleu ocean metallisee, arete arrondie
sd = rrect_sd(UX, UY, PX0, PY0, PW, PH, PR)
body = np.clip(0.5 - sd * AS, 0, 1).astype(np.float32)
EDGE = 9.0
d_in = np.clip(-sd, 0, None)
hgt = np.where(d_in < EDGE, np.sqrt(np.clip(EDGE ** 2 - (EDGE - d_in) ** 2, 0, None)), EDGE).astype(np.float32)
del d_in
gy, gx = np.gradient(cv2.GaussianBlur(hgt, (0, 0), 1.0 * AS / 2), 1.0 / AS)
del hgt
nrm = np.dstack([-gx, -gy, np.ones_like(gx)]).astype(np.float32); del gx, gy
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
ndl = np.clip(nrm @ L.astype(np.float32), 0, 1); ndh = np.clip(nrm @ HV.astype(np.float32), 0, 1); del nrm
paint = np.array([15.0, 58.0, 101.0], np.float32)
img = paint * (0.50 + 0.78 * ndl)[..., None] + (62 * ndh ** 40 + 16 * ndh ** 6)[..., None] * np.array([0.85, 0.93, 1.0], np.float32)
del ndl, ndh
rng = np.random.default_rng(11)
flake = (rng.random((H, W), dtype=np.float32) ** 18)
flake = cv2.GaussianBlur(flake, (0, 0), 0.3 * AS) * 150
sheen = np.exp(-(((UX - 290) / 320) ** 2 + ((UY - 190) / 360) ** 2)).astype(np.float32)
grain = fbm((H, W), [2, 4], [1.3, 0.8], 3) + 0.8 * fbm((H, W), [180, 520], [0.8, 1.0], 4)
img += grain[..., None] * np.array([0.45, 0.8, 1.0], np.float32)
img += (flake * (0.35 + 0.9 * sheen))[..., None] * np.array([0.55, 0.8, 1.0], np.float32)
img += (15.0 * sheen)[..., None] * np.array([0.4, 0.75, 1.0], np.float32)
del flake, grain
img *= body[..., None]

# ------------------------------------------------------------------ 2. vagues (cuites a plat, decoupees au cadre interieur)
print('vagues...')
svg = open(os.path.join(ROOT, 'PipelineWaves.svg')).read()
inner = svg[svg.index('<g '):svg.rindex('</svg>')]
a_ = WV_KX * AS; d_ = WV_KY * AS
e_ = (FACE[0] - WV_X0 * WV_KX) * AS; f_ = (TITLE_Y - WV_TITLE * WV_KY) * AS
tmp = os.path.join(ROOT, 'design', '_waves_tmp.svg'); tmp_png = tmp[:-4] + '.png'
open(tmp, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                     f'<g transform="matrix({a_} 0 0 {d_} {e_} {f_})">{inner}</g></svg>')
subprocess.run(['node', os.path.join(HERE, 'svg_render.js'), tmp, tmp_png, str(W), str(H)], check=True)
wv = np.asarray(Image.open(tmp_png).convert('RGBA')).astype(np.float32)
os.remove(tmp); os.remove(tmp_png)
face_m = np.clip(0.5 - rrect_sd(UX, UY, FACE[0], FACE[1], FACE[2], FACE[3], FR_R - FR_IN * 0.0) * AS, 0, 1)
wa = wv[..., 3] / 255.0 * face_m
img = img * (1 - wa[..., None]) + wv[..., :3] * wa[..., None]
del wv, wa

# ------------------------------------------------------------------ 3. ecran (calque des commandes) : verre noir, biseau, trame LCD discrete (texte dessine par le plugin)
print('ecran...')
sx, sy, sw, sh = SCREEN
s_sd = rrect_sd(UX, UY, sx, sy, sw, sh, 7.0)
s_m = np.clip(0.5 - s_sd * AS, 0, 1)
bez = np.clip(0.5 - (rrect_sd(UX, UY, sx - 3.0, sy - 3.0, sw + 6.0, sh + 6.0, 9.5)) * AS, 0, 1) - s_m
# chassis (biseau sombre, arete claire en haut a gauche)
t_ = np.clip((UY - (sy - 3)) / (sh + 6), 0, 1)
bez_col = (30.0 - 14.0 * t_)[..., None] * np.array([0.85, 0.92, 1.0], np.float32)
glass = (9.0 + 5.0 * np.exp(-((UY - sy) / (sh * 0.45)) ** 2))[..., None] * np.array([0.78, 0.9, 1.0], np.float32)
lcd = ((np.mod(UX - sx, 1.6) < 0.5) | (np.mod(UY - sy, 1.6) < 0.5)).astype(np.float32)
lcd = cv2.GaussianBlur(lcd, (0, 0), 0.6)
glass = glass + (lcd * 2.2)[..., None]
inner_sh = np.clip(1.0 - np.clip(-s_sd, 0, 6.0) / 6.0, 0, 1) * 0.55
glass *= (1 - inner_sh)[..., None]
glass += (np.exp(-((UY - sy - 2) / 1.2) ** 2) * 10)[..., None]   # reflet sur l'arete haute du verre
# l'ecran va dans le calque des commandes (au-dessus des vagues vectorielles du plugin : aucun raccord autour du chassis)
scr_a = np.clip(bez + s_m, 0, 1)
scr_p = bez_col * bez[..., None] + glass * s_m[..., None]
del s_sd, bez, t_, bez_col, glass, lcd, inner_sh

img += (fbm((H, W), [1], [0.8], 22) * body)[..., None]

# ------------------------------------------------------------------ calque des commandes (controls.png) : ombres + pieces photo, separe du fond
# pour que le plugin dessine les vagues vectorielles ENTRE le fond et ce calque (aucune zone ou les vagues seraient cuites)
ctl_p = scr_p                                # couleur premultipliee (l'ecran en premier)
ctl_a = scr_a.copy()
def ctl_shade(o):
    global ctl_p, ctl_a
    ctl_p *= (1 - o)[..., None]; ctl_a = o + ctl_a * (1 - o)
def ctl_over(rgba, x0, y0):
    h, w = rgba.shape[:2]
    X0, Y0 = int(round(x0)), int(round(y0))
    sx0, sy0 = max(0, -X0), max(0, -Y0)
    ex, ey = min(w, W - X0), min(h, H - Y0)
    a = rgba[sy0:ey, sx0:ex, 3] / 255.0
    sl = (slice(Y0 + sy0, Y0 + ey), slice(X0 + sx0, X0 + ex))
    ctl_p[sl] = rgba[sy0:ey, sx0:ex, :3] * a[..., None] + ctl_p[sl] * (1 - a)[..., None]
    ctl_a[sl] = a + ctl_a[sl] * (1 - a)

# ------------------------------------------------------------------ 4. occlusion autour des commandes (jamais sur l'ecran)
print('potards, LED, footswitch...')
def occlusion(mask, strength=1.0):
    contact = cv2.GaussianBlur(mask, (0, 0), 3.0 * AS)
    soft = cv2.GaussianBlur(mask, (0, 0), 14.0 * AS)
    o = np.clip(contact * 0.55 + soft * 0.9, 0, 0.5) * strength * (1.0 - mask) * (1 - s_m)
    ctl_shade(o * body)
_m = np.zeros((H, W), np.float32)
for (x, y, _) in KNOBS:
    _m = np.maximum(_m, np.clip((KNOB_R - np.hypot(UX - x, UY - y)) * AS, 0, 1))
_m = np.maximum(_m, np.clip((MODE_R - np.hypot(UX - MODE[0], UY - MODE[1])) * AS, 0, 1))
LED_LENS = 13.0
_m = np.maximum(_m, np.clip((LED_LENS * 1.08 - np.hypot(UX - LED[0], UY - LED[1])) * AS, 0, 1) * 0.6)
FSPR, FSREFL, FS_W, FS_BTN = PC.footswitch_sprite(FS_FLATS, AS, refl_colour=(60.0, 140.0, 255.0))
_fa = np.zeros((H, W), np.float32); _n = FSPR.shape[0]
_x0 = int(round((FS[0] - _n / AS / 2) * AS)); _y0 = int(round((FS[1] - _n / AS / 2) * AS))
_fa[_y0:_y0 + _n, _x0:_x0 + _n] = np.clip((FSPR[..., 3] / 255.0 - 0.86) / 0.14, 0, 1)
_m = np.maximum(_m, _fa); del _fa
occlusion(_m); del _m

KN, KS = PC.knurl_sprite(KNOB_R, AS)
for (x, y, _) in KNOBS:
    ctl_over(KN, (x - KS / 2) * AS, (y - KS / 2) * AS)
KM, KMS = PC.knurl_sprite(MODE_R, AS)
ctl_over(KM, (MODE[0] - KMS / 2) * AS, (MODE[1] - KMS / 2) * AS)

LD, LDON, LS = PC.led_hex_sprites(LED_LENS, AS)
ctl_over(LD, (LED[0] - LS / 2) * AS, (LED[1] - LS / 2) * AS)
def save_half(rgba, fn):
    """sprite 4 px/unite -> 2 px/unite (fichiers du plugin)"""
    pm = rgba.astype(np.float32).copy(); pm[..., :3] *= pm[..., 3:4] / 255.0
    n2 = (pm.shape[1] // 2, pm.shape[0] // 2)
    pm = cv2.resize(pm, n2, interpolation=cv2.INTER_AREA)
    a = np.maximum(pm[..., 3:4], 1e-3); pm[..., :3] = np.where(pm[..., 3:4] > 0.3, pm[..., :3] * 255.0 / a, 0)
    Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(ROOT, fn), optimize=True)
save_half(LDON, 'led_on.png')
ctl_over(FSPR, (FS[0] - FS_W / 2) * AS, (FS[1] - FS_W / 2) * AS)

# ------------------------------------------------------------------ 5. embases jack : OUT a gauche, IN a droite
alpha = body.copy()
for side in (-1, 1):
    j, jw_u, jh_u = PC.jack_sprite(JACK_LEN, AS, side)
    jh, jw = j.shape[:2]
    jw2 = int(math.floor(JACK_PROT * AS))
    if jw2 != jw:
        pm_ = j.copy(); pm_[..., :3] *= pm_[..., 3:4] / 255.0
        pm_ = cv2.resize(pm_, (jw2, jh), interpolation=cv2.INTER_AREA)
        a_j = np.maximum(pm_[..., 3:4], 1e-3); pm_[..., :3] = np.where(pm_[..., 3:4] > 0.5, pm_[..., :3] * 255.0 / a_j, 0)
        j = pm_; jw = jw2
    x0 = int(round((PX0 * AS - jw) if side < 0 else ((PX0 + PW) * AS)))
    y0 = int(round(JACK_Y * AS - jh / 2))
    occ = np.zeros((H, W), np.float32)
    occ[y0:y0 + jh, x0:x0 + jw] = j[..., 3] / 255.0
    contact = cv2.GaussianBlur(occ, (0, 0), 3.0 * AS)
    soft = cv2.GaussianBlur(occ, (0, 0), 18.0 * AS)
    occ = np.clip(contact * 0.9 + soft * 1.6, 0, 0.62) * (0.2 if side > 0 else 0.7)
    ctl_shade(occ * body)
    ctl_over(j, x0, y0)
    ja = np.zeros((H, W), np.float32); ja[y0:y0 + jh, x0:x0 + jw] = j[..., 3] / 255.0
    alpha = np.maximum(alpha, ja)
    del occ, contact, soft, ja

# ------------------------------------------------------------------ 6. sauvegarde : 1235 x 1800 (plugin) + reference 4K
def crop_box():
    return CROP_X0 * AS, (CROP_X0 + CROP_W) * AS, PY0 * AS, (PY0 + PH) * AS
def to_out(a, ow=OUT_W, oh=OUT_H):
    x0, x1, y0, y1 = crop_box()
    M = np.float32([[ow / (x1 - x0), 0, -x0 * ow / (x1 - x0)], [0, oh / (y1 - y0), -y0 * oh / (y1 - y0)]])
    return cv2.warpAffine(a, M, (ow, oh), flags=cv2.INTER_AREA)
def premul_out(rgb, a, ow=OUT_W, oh=OUT_H):
    o_a = np.clip(to_out(a, ow, oh), 0, 1)
    o_rgb = to_out(rgb * a[..., None], ow, oh) / np.maximum(o_a, 1e-3)[..., None]
    return np.dstack([np.clip(o_rgb, 0, 255), o_a * 255]).astype(np.uint8)
Image.fromarray(premul_out(img, body), 'RGBA').save(os.path.join(ROOT, 'background.png'), optimize=True)
_ca = np.clip(to_out(ctl_a), 0, 1); _cp = to_out(ctl_p)
Image.fromarray(np.dstack([np.clip(_cp / np.maximum(_ca, 1e-3)[..., None], 0, 255), _ca * 255]).astype(np.uint8), 'RGBA').save(
    os.path.join(ROOT, 'controls.png'), optimize=True)
img = img * (1 - ctl_a[..., None]) + ctl_p          # composite complet (calque de la LED, reference 4K)
os.makedirs(os.path.join(ROOT, 'design'), exist_ok=True)
Image.fromarray(premul_out(img, alpha, 2 * OUT_W, 2 * OUT_H), 'RGBA').save(os.path.join(ROOT, 'design', 'Pipeline_fond_4K.png'))
for old in ('background.jpg', 'knob_strip.png', 'mode_labels.png'):
    if os.path.exists(os.path.join(ROOT, old)): os.remove(os.path.join(ROOT, old))

# ------------------------------------------------------------------ 7. facade eclairee par la LED bleue (calque alpha : seule la lumiere ajoutee)
GR = min(80.0, LED[1] - 2.0)
def glow(c, fn):
    x0p, y0p = round((c[0] - GR) * AS), round((c[1] - GR) * AS)
    size = round(2 * GR * AS)
    reg = img[y0p:y0p + size, x0p:x0p + size].astype(np.float64)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    d = np.hypot((xx + 0.5) / AS - GR, (yy + 0.5) / AS - GR)
    h1, h2 = 7.0, 26.0
    E = 1.0 * h1 ** 3 / (d ** 2 + h1 ** 2) ** 1.5 + 0.15 * h2 ** 3 / (d ** 2 + h2 ** 2) ** 1.5
    E *= np.clip((GR - d) / 30.0, 0, 1)
    E[d < LED_LENS * 1.08] = 0.0
    col = np.array([0.30, 0.62, 1.0])
    lum = reg.mean(2, keepdims=True)
    lit = reg + (reg * 2.0 + 12.0 * np.clip(lum / 40.0, 0.3, 1.6)) * E[..., None] * col
    add = lit - reg
    a = np.clip(np.abs(add).max(-1) / 12.0, 0, 1)
    rgb = np.where(a[..., None] > 1e-3, reg + add / np.maximum(a, 1e-3)[..., None], reg)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.float32)
    save_half(out, fn)
    return (x0p / AS, y0p / AS, size / AS, size / AS)
GLR = glow(LED, 'glow_led.png')

# ------------------------------------------------------------------ 8. serigraphie vectorielle (dessinee par le plugin) + Layout.h
TEXTS = []        # (texte, police 0 medium / 1 bold / 2 light, taille em, espacement, x, y, rotation)
TICKS = []        # (x0, y0, x1, y1, epaisseur)
for (x, y, t) in KNOBS:
    TEXTS.append((t, 0, 19.0, 3.4, x, y - KNOB_R - 31.0, 0.0))
    for i in range(11):
        a = math.radians(-150 + 30 * i)
        r0, r1 = KNOB_R + 9.0, KNOB_R + (17.0 if i in (0, 5, 10) else 15.0)
        TICKS.append((x + r0 * math.sin(a), y - r0 * math.cos(a), x + r1 * math.sin(a), y - r1 * math.cos(a), 1.9))
TEXTS.append(('MODE', 0, 16.0, 3.2, MODE[0], MODE[1] - 107.0 * LBL_K, 0.0))
for i in range(8):
    a = math.radians(MODE_FIRST + MODE_STEP * i)
    r0, r1 = MODE_R + 6.0, MODE_R + 13.0
    TICKS.append((MODE[0] + r0 * math.sin(a), MODE[1] - r0 * math.cos(a), MODE[0] + r1 * math.sin(a), MODE[1] - r1 * math.cos(a), 1.9))
LABEL_FIRST = len(TEXTS)
for i, n in enumerate(MODE_NAMES):
    TEXTS.append((n, 0, 13.5, 1.0, LABELS[i][0], LABELS[i][1], 0.0))
TEXTS.append(('PIPELINE', 1, 66.0, 4.0, CX, TITLE_Y, 0.0))
TEXTS.append(('PITCH VIBRATO', 2, 18.0, 7.5, CX, SUB_Y, 0.0))
TEXTS.append(('OUT', 0, 13.0, 1.6, PX0 + FR_IN + 13.0, JACK_Y, 90.0))
TEXTS.append(('IN', 0, 13.0, 1.6, PX0 + PW - FR_IN - 13.0, JACK_Y, 90.0))
# filets ondules de part et d'autre du sous-titre (x0, x1, y, amplitude, nombre de periodes, epaisseur)
from PIL import ImageFont
fl = ImageFont.truetype(os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Light.ttf'), 1000)
fb = ImageFont.truetype(os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Bold.ttf'), 1000)
def tw(font, s, em, tr): return sum(font.getlength(c) for c in s) / 1000.0 * em + tr * (len(s) - 1)
subw = tw(fl, 'PITCH VIBRATO', 18.0, 7.5); titw = tw(fb, 'PIPELINE', 66.0, 4.0)
WAVY = []
for sgn in (-1, 1):
    xa, xb = CX + sgn * (subw / 2 + 14.0), CX + sgn * (titw / 2 + 4.0)
    WAVY.append((min(xa, xb), max(xa, xb), SUB_Y, 2.4, 2.5, 1.6))

def f(v): return f"{v:.2f}f"
def X(v): return (v - CROP_X0) * SC
def Y(v): return (v - PY0) * SC
def PT(p): return "{ %s, %s }" % (f(X(p[0])), f(Y(p[1])))
def RC(r): return "{ %s, %s, %s, %s }" % (f(X(r[0])), f(Y(r[1])), f(r[2] * SC), f(r[3] * SC))
json.dump({"frame": [OUT_W / 2, OUT_H / 2], "knobs": [[X(k[0]), Y(k[1]), KNOB_R * SC] for k in KNOBS] + [[X(MODE[0]), Y(MODE[1]), MODE_R * SC]],
           "led": [X(LED[0]), Y(LED[1])], "fs": [X(FS[0]), Y(FS[1])],
           "status": [X(ROW[0]), Y(ROW[1]), ROW[2] * SC, ROW[3] * SC], "preset": [X(BAR[0]), Y(BAR[1]), BAR[2] * SC, BAR[3] * SC],
           "jackY": Y(JACK_Y), "jackL": X(PX0 - JACK_PROT / 2), "jackR": X(PX0 + PW + JACK_PROT / 2)},
          open(os.path.join(ROOT, 'tools', 'layout.json'), 'w'), indent=1)
with open(os.path.join(ROOT, 'Layout.h'), 'w') as fo:
    w_ = fo.write
    w_(f"// genere par tools/make_art.py - ne pas modifier a la main (repere {OUT_W / 2} x {OUT_H / 2} = fond {OUT_W} x {OUT_H} px / 2)\n#pragma once\n#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{{\n")
    w_(f"    constexpr float frameW = {f(OUT_W / 2)}, frameH = {f(OUT_H / 2)};   // pedale plein cadre (jacks aux bords gauche / droit)\n")
    w_(f"    const juce::Point<float> ratePos {PT(KNOBS[0][:2])}, depthPos {PT(KNOBS[1][:2])}, modePos {PT(MODE)};\n")
    w_(f"    const float knobR = {f(KNOB_R * SC)}, modeR = {f(MODE_R * SC)};   // rayon exterieur du moletage\n")
    w_(f"    const float knobSpriteHalf = {f(KS / 2 * SC)}, modeSpriteHalf = {f(KMS / 2 * SC)};\n")
    w_(f"    const float modeFirstDeg = {MODE_FIRST:.4f}f, modeStepDeg = {MODE_STEP:.4f}f;     // 8 positions\n")
    w_(f"    // repere du potard (photo) : rayons x rayon exterieur\n")
    w_(f"    const float idxR0 = {PC.KK_LINE[0]:.4f}f, idxR1 = {PC.KK_LINE[1]:.4f}f, idxHalfW = {PC.KK_LINE[2]:.4f}f, dotR = {PC.KK_DOT[0]:.4f}f, dotSize = {PC.KK_DOT[1]:.4f}f;\n")
    w_(f"    const juce::Point<float> ledPos {PT(LED)}; const float ledS = {f(LS * SC)};\n")
    w_(f"    const juce::Rectangle<float> glowRect {RC(GLR)};\n")
    w_(f"    const juce::Point<float> footPos {PT(FS)}; const float footR = {f(FS_BTN * SC)}, fsS = {f(FS_W * SC)}, footHit = {f(FS_FLATS * 0.5 * SC)};\n")
    w_(f"    const juce::Rectangle<float> screenRect {RC(SCREEN)}, rowRect {RC(ROW)}, barRect {RC(BAR)};\n")
    w_(f"    const juce::Rectangle<float> boxRect {RC((PX0, PY0, PW, PH))};   // boitier\n")
    w_(f"    const juce::Rectangle<float> faceRect {RC(FACE)}; const float faceR = {f(FR_R * SC)}, faceLineW = {f(FR_W * SC)};   // cadre interieur\n")
    w_(f"    const float jackY = {f(Y(JACK_Y))};\n")
    w_("    // serigraphie vectorielle : texte, police (0 medium, 1 bold, 2 light), taille em, espacement, centre, rotation (degres)\n")
    w_("    struct Txt { const char* s; int font; float em, track, x, y, rot; };\n")
    w_("    const Txt texts[] = {\n" + ",\n".join(f'        {{ "{t[0]}", {t[1]}, {f(t[2] * SC)}, {f(t[3] * SC)}, {f(X(t[4]))}, {f(Y(t[5]))}, {f(t[6])} }}' for t in TEXTS) + "\n    };\n")
    w_(f"    constexpr int modeLabelFirst = {LABEL_FIRST};   // texts[modeLabelFirst + i] = etiquette du mode i\n")
    w_("    struct Tick { float x0, y0, x1, y1, w; };\n")
    w_("    const Tick ticks[] = { " + ", ".join(f"{{ {f(X(t[0]))}, {f(Y(t[1]))}, {f(X(t[2]))}, {f(Y(t[3]))}, {f(t[4] * SC)} }}" for t in TICKS) + " };\n")
    w_("    struct Wavy { float x0, x1, y, amp, periods, w; };\n")
    w_("    const Wavy wavy[] = { " + ", ".join(f"{{ {f(X(v[0]))}, {f(X(v[1]))}, {f(Y(v[2]))}, {f(v[3] * SC)}, {v[4]:.2f}f, {f(v[5] * SC)} }}" for v in WAVY) + " };\n")
    w_(f"    const juce::Point<float> logoPos {PT(LOGO_C)}; const float logoW = {f(LOGO_W * SC)};\n")
    w_("    // vagues (PipelineWaves.svg) : x' = waveA * x + waveB, y' = waveC * y + waveD (unites du plugin)\n")
    w_(f"    const float waveA = {WV_KX * SC:.6f}f, waveB = {X(FACE[0] - WV_X0 * WV_KX):.4f}f, waveC = {WV_KY * SC:.6f}f, waveD = {Y(TITLE_Y - WV_TITLE * WV_KY):.4f}f;\n")
    w_("}\n")
print('ok', 'PW', PW, 'jackprot', JACK_PROT)
