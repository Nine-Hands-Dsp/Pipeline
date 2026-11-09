# PIPELINE (NINE HANDS | DSP) - notice PDF en francais, illustree avec le rendu reel du plugin.
# Usage : python3 tools/manual.py <dossier des captures (tools/render)> <fichier PDF de sortie>
#   (captures produites par l'outil tools/render : pipeline_full.png, pipeline_envp.png, ...)
import os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, CondPageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[1]
OUT = sys.argv[2]
VERSION = "1.6.0"
TMP = os.path.dirname(os.path.abspath(OUT))
FONTS = os.path.join(ROOT, "assets", "fonts")

for n, f in (("Pop", "Poppins-Regular"), ("PopL", "Poppins-Light"), ("PopM", "Poppins-Medium"), ("PopB", "Poppins-Bold"),
             ("Title", "BarlowCondensed-ExtraBold")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(FONTS, f + ".ttf")))

ACC = colors.HexColor("#1E87FF"); ACC_L = colors.HexColor("#6FB8FF")       # bleu de la LED allumee
DARK = colors.HexColor("#1B1C20"); GREY = colors.HexColor("#686A72"); LIGHT = colors.HexColor("#EEF2F5")
ACC_RGB = (30, 135, 255)
LAY = json.load(open(os.path.join(ROOT, "tools", "layout.json")))

# logo NINE HANDS | DSP blanc (SVG officiel) en PNG, rendu par Chromium (tools/svg_render.js)
LOGO_PNG = os.path.join(TMP, "nine_hands_logo_blanc.png")
subprocess.run(["node", os.path.join(ROOT, "tools", "svg_render.js"), os.path.join(ROOT, "NineHandsLogo.svg"), LOGO_PNG, "1288", "120"], check=True)

def shot(name): return Image.open(os.path.join(SHOTS, name)).convert("RGB")
src = shot("pipeline_full.png")
K = src.height / 900.0          # repere du plugin : 617,5 x 900 unites (fond 1235 x 1800 / 2)

# ---------- capture annotee ----------
kn, st_, pr_ = LAY["knobs"], LAY["status"], LAY["preset"]
marks = [  # numero, x, y (unites du plugin)
    (1, kn[0][0] - 72, kn[0][1] - 66), (2, kn[1][0] + 72, kn[1][1] - 66), (3, kn[2][0] + 118, kn[2][1] + 78),
    (4, st_[0] + st_[2] + 12, st_[1] + st_[3] * 0.5), (5, pr_[0] + pr_[2] + 18, pr_[1] + pr_[3] * 0.5),
    (6, LAY["led"][0] + 30, LAY["led"][1]), (7, LAY["fs"][0] + 72, LAY["fs"][1]),
    (8, 40, LAY["jackY"] - 52), (9, 577, LAY["jackY"] - 52)]
ann = src.copy(); dr = ImageDraw.Draw(ann)
fnt = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 34)
for n, x, y in marks:
    cx, cy, r = x * K, y * K, 27
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=ACC_RGB, width=5)
    dr.text((cx, cy + 1), str(n), font=fnt, fill=(27, 28, 32), anchor="mm")
annotated = os.path.join(TMP, "pipeline_annotated.png"); ann.save(annotated)

def crop_u(im, box): return im.crop(tuple(int(v * K) for v in box))
def strip(images, path, gap=16):
    h = max(i.height for i in images)
    s = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), h), (255, 255, 255))
    x = 0
    for i in images: s.paste(i, (x, 0)); x += i.width + gap
    s.save(path); return path

knobs_img = strip([crop_u(src, (40, 60, 578, 285))], os.path.join(TMP, "pipeline_knobs.png"))
mx, my = kn[2][0], kn[2][1]
box_m = (mx - 140, my - 125, mx + 140, my + 120)
mode_img = strip([crop_u(src, box_m), crop_u(shot("pipeline_envp.png"), box_m)], os.path.join(TMP, "pipeline_mode.png"))
fx, fy = LAY["fs"]
box_f = (fx - 70, fy - 62, fx + 70, fy + 62)
fs_img = strip([crop_u(shot(p), box_f) for p in ("pipeline_bypass.png", "pipeline_full.png", "pipeline_pressed.png")], os.path.join(TMP, "pipeline_fs.png"))
box_d = (st_[0] - 12, st_[1] - 10, st_[0] + st_[2] + 12, pr_[1] + pr_[3] + 12)
disp_img = strip([crop_u(shot(p), box_d) for p in ("pipeline_full.png", "pipeline_envp.png")], os.path.join(TMP, "pipeline_disp.png"), gap=10)
disp2_img = strip([crop_u(shot(p), box_d) for p in ("pipeline_status.png", "pipeline_sync.png")], os.path.join(TMP, "pipeline_disp2.png"), gap=10)

# ---------- couverture : pedale detouree (canal alpha du fond + calque des commandes : boitier + jacks), reflet, halo bleu ----------
a_bg = np.asarray(Image.open(os.path.join(ROOT, "background.png")).split()[3].resize(src.size, Image.LANCZOS))
a_ct = np.asarray(Image.open(os.path.join(ROOT, "controls.png")).split()[3].resize(src.size, Image.LANCZOS))
msk = Image.fromarray(np.maximum(a_bg, np.where(a_ct > 200, a_ct, 0)).astype(np.uint8))
cut = Image.new("RGBA", src.size, (0, 0, 0, 0)); cut.paste(src, (0, 0), msk)
cut = cut.crop(cut.getbbox())
cw, ch = cut.size
pad = int(cw * 0.16)
canvas = Image.new("RGBA", (cw + 2 * pad, int(ch * 1.30) + pad), (0, 0, 0, 255))
yy, xx = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float64)
gcx, gcy = canvas.width / 2, pad + ch * 0.45
glow = np.exp(-(((xx - gcx) / (cw * 0.62)) ** 2 + ((yy - gcy) / (ch * 0.48)) ** 2)) * 30
edge = np.clip(np.minimum.reduce([xx, canvas.width - 1 - xx, yy, canvas.height - 1 - yy]) / (pad * 0.9), 0, 1)
glow *= edge ** 2
halo = np.dstack([glow * 0.15, glow * 0.55, glow * 1.0, np.full_like(glow, 255)]).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(halo, "RGBA"))
refl = cut.transpose(Image.FLIP_TOP_BOTTOM)
ra = np.array(refl).astype(np.float64)
fade = np.clip(1 - np.arange(refl.height) / (refl.height * 0.22), 0, 1) ** 1.6 * 0.22
ra[..., 3] *= fade[:, None]
canvas.alpha_composite(Image.fromarray(ra.astype(np.uint8), "RGBA"), (pad, pad + ch + 6))
canvas.alpha_composite(cut, (pad, pad))
canvas = canvas.crop((0, 0, canvas.width, pad + int(ch * 1.20)))
cover = os.path.join(TMP, "pipeline_cover_cutout.png"); canvas.convert("RGB").save(cover)

def img(path, width):
    im = Image.open(path); h = width * im.height / im.width
    return RLImage(path, width=width, height=h)

# ---------- styles ----------
st = {
    "h1": ParagraphStyle("h1", fontName="PopB", fontSize=20, leading=24, textColor=ACC, spaceAfter=8, spaceBefore=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="PopM", fontSize=13, leading=17, textColor=DARK, spaceAfter=4, spaceBefore=10, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Pop", fontSize=9.6, leading=14, textColor=DARK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Pop", fontSize=8.2, leading=11.5, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Pop", fontSize=8.4, leading=11, textColor=DARK),
    "cellb": ParagraphStyle("cellb", fontName="PopM", fontSize=8.4, leading=11, textColor=DARK),
}
def P(t, s="p"): return Paragraph(t, st[s])
def bullets(items): return [P("&bull;&nbsp;&nbsp;" + i) for i in items]
def table(rows, widths, header=True):
    data = [[P(c, "cellb" if (header and r == 0) else "cell") for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9D6")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header: style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACC)]
    t.setStyle(TableStyle(style)); return t

# ---------- donnees (identiques au code livre : PluginProcessor.cpp, PipelineDSP.h) ----------
MODES = ["SINE", "TRIANGLE", "RAMP", "SQUARE", "RANDOM", "ENV D", "ENV R", "ENV P"]
FACTORY = [  # nom, rate, depth, mode
    ("Smooth Sine Wave", 4.0, 4.0, 0), ("Haunting Ramp (High Rate)", 7.5, 5.0, 2), ("Chooglin' Amp Vibrato", 6.5, 3.0, 0),
    ("Seasick Sine", 2.5, 7.5, 0), ("Triangle Wobble", 5.0, 5.0, 1), ("Sonar Ping", 3.5, 6.5, 2), ("Hammer-On Trill", 6.5, 6.0, 3),
    ("Kosmische Pulse", 4.0, 3.5, 3), ("Warped Record", 3.0, 2.0, 4), ("Drunken Master", 5.0, 8.5, 4), ("Motorik Dig-In", 6.0, 6.0, 5),
    ("Touch Rate Ripple", 5.5, 4.5, 6), ("My Bloody Valentine", 6.0, 10.0, 7), ("Touch Chorus", 3.0, 5.0, 7), ("Pseudo Flange", 1.5, 5.0, 7)]
def hz(v): return 0.1 * 160 ** ((v / 10.0) ** 0.8)
def pc(v): return f"{round(v * 10)} %"
def rate_s(v, mode):
    if mode == 6: return pc(v) + " (sensib.)"
    if mode == 7: return pc(v) + " (amplitude)"
    h = hz(v)
    s = f"{h:.2f}" if h < 1 else f"{h:.1f}"
    return pc(v) + "<br/>(" + s.replace(".", ",") + " Hz)"
def depth_s(v, mode):
    if mode == 5: return pc(v) + " (sensib.)"
    if mode == 7:
        w = round(v * 10)
        return "tout traité" if w >= 100 else f"{100 - w} / {w}"
    return pc(v)
FACT_DESC = ["Le premier réglage conseillé du manuel d'origine : un vibrato doux et classique.",
        "Le deuxième réglage conseillé du manuel d'origine : des « pings » de sonar à vitesse élevée.",
        "Sinus plus rapide et moins profond : le vibrato d'ampli du swamp rock.",
        "Lent et profond : la hauteur tangue comme un bateau.",
        "Des virages plus francs en haut et en bas de chaque cycle que le sinus.",
        "Une rampe lente : un « ping » vers le haut, puis une descente rapide et un long palier.",
        "Onde carrée : deux hauteurs et un saut instantané entre elles, un trille sans hammer-on.",
        "Carré plus lent et moins profond : des pulsations kosmische régulières.",
        "Random à faible Depth : le pleurage d'un disque voilé.",
        "Random à forte Depth : des glissandos imprévisibles et « graisseux ».",
        "Env D : plus on attaque fort, plus le vibrato est profond. Pour les grooves motorik.",
        "Env R : plus on attaque fort, plus le vibrato est rapide.",
        "Env P tout traité : chaque attaque fait plonger la hauteur comme un levier de vibrato, puis elle remonte.",
        "Env P à midi : 50/50 sec / traité, un chorus sensible au toucher.",
        "Env P avec une petite amplitude à 50/50 : un pseudo-flanger dynamique."]
DIVS = "4 mesures, 2 mesures, 1 mesure, 1/2, 1/4 D, 1/2 T, 1/4, 1/8 D, 1/4 T, 1/8, 1/8 T, 1/16, 1/16 T, 1/32"

t = dict(
 lang="FRANÇAIS", sub="Vibrato de hauteur",
 intro_t="1. Présentation",
 intro=["<b>Pipeline</b> est un plugin VST3 NINE HANDS | DSP qui reprend le vibrato <b>EarthQuaker Devices Aqueduct</b> : mêmes commandes (RATE, DEPTH et un sélecteur MODE à 8 positions), mêmes huit modes de modulation, du « pas si bizarre » au « franchement bizarre », et même footswitch Flexi-Switch.",
        "Comme la pédale, Pipeline est un vrai vibrato de hauteur : la guitare passe dans une ligne de retard très courte dont la longueur est modulée, on entend donc une variation de hauteur (et non de volume, ce serait un trémolo). Dans les modes à forme d'onde, le signal est 100 % traité, comme sur l'original ; seul <b>Env P</b> a un mélange sec / traité.",
        "Pipeline a été construit d'après le manuel d'origine, la page du fabricant et les tests (Premier Guitar, MusicRadar, Guitar World, Bonedo). La forme de chaque mode a été dessinée comme la forme du mouvement de <b>hauteur</b> que l'on entend, puis mesurée sur des signaux de test.",
        "Le visuel est celui de NINE HANDS | DSP : boîtier bleu océan et vagues japonaises. Les textes, graduations, vagues, cadre et logo sont dessinés en vectoriel par le plugin : ils restent nets à toutes les tailles de fenêtre, y compris sur les écrans Retina et 4K."],
 inst_t="2. Installation",
 inst=[("Téléchargement", "Sur la page GitHub <b>Nine-Hands-Dsp/pipeline</b>, les boutons <b>Télécharger Windows</b> et <b>Télécharger macOS</b> du README donnent toujours la dernière version (<b>Pipeline-VST3-Windows.zip</b>, <b>Pipeline-VST3-macOS.zip</b>)."),
       ("Windows", "Décompressez l'archive et copiez le dossier <b>Pipeline.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Décompressez l'archive et copiez <b>Pipeline.vst3</b> dans <b>~/Bibliothèque/Audio/Plug-Ins/VST3</b> (ou /Library/Audio/Plug-Ins/VST3). La version est universelle (Apple Silicon et Intel) et signée localement ; si macOS la bloque, tapez <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Pipeline.vst3</b> dans le Terminal."),
       ("Reaper", "Options &gt; Préférences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. Le plugin apparaît sous le nom <b>Pipeline (NINE HANDS | DSP)</b>. Pour le piloter avec des footswitchs et pédales d'expression MIDI, la piste doit recevoir le MIDI du contrôleur (armement ou monitoring d'entrée, entrée MIDI réglée sur votre appareil, par exemple la M-Vave Chocolate Plus).")],
 ov_t="3. Vue d'ensemble",
 ov_rows=[["N°", "Commande", "Rôle"], ["1", "RATE", "Vitesse du LFO (en Env R : sensibilité de l'enveloppe ; en Env P : sensibilité et amplitude du bend)"],
          ["2", "DEPTH", "Intensité du vibrato (en Env D : sensibilité de l'enveloppe ; en Env P : mélange sec / traité)"],
          ["3", "MODE", "8 positions : SINE, TRI, RAMP, SQR, RAND, ENV D, ENV R, ENV P ; l'étiquette du mode choisi s'allume en bleu"],
          ["4", "Écran", "À gauche : valeur de la commande touchée, sinon le mode, la vitesse et l'écart de hauteur en direct. À droite : courbe de la modulation en direct"],
          ["5", "Barre de presets", "Flèches = preset précédent / suivant, nom = menu des presets"],
          ["6", "LED", "Effet en marche (LED bleue à facettes) ; sa lumière éclaire la façade"],
          ["7", "Footswitch", "Flexi-Switch : appui bref = marche / arrêt, appui maintenu = momentané"],
          ["8 / 9", "OUT / IN", "Sortie à gauche, entrée à droite, comme sur une vraie pédale"]],
 ctl_t="4. Les commandes",
 ctl=[("RATE", "Vitesse du LFO, c'est-à-dire la rapidité avec laquelle la hauteur monte et descend : 0,1 Hz tout à gauche, environ 1,8 Hz à 12 h, 5,6 Hz à 15 h, 16 Hz tout à droite. En <b>Env R</b>, il devient la sensibilité de l'enveloppe ; en <b>Env P</b>, la sensibilité et l'amplitude générale du bend. Avec la <b>synchro tempo</b>, RATE choisit une valeur de note (voir section 6)."),
      ("DEPTH", "Intensité du vibrato (amplitude du LFO). La course est progressive : léger frémissement jusqu'à 11 h, vibrato classique vers midi, tangage au-delà. Comme sur tout vibrato à ligne de retard, un même DEPTH donne plus d'écart de hauteur quand RATE est plus élevé ; aux réglages extrêmes, l'écart est tenu vers +4 / -6 demi-tons pour que le son ne se retourne jamais. En <b>Env D</b>, DEPTH devient la sensibilité de l'enveloppe ; en <b>Env P</b>, le mélange sec / traité."),
      ("Tourner les potards", "Tirez vers le haut / la droite pour augmenter ; Maj = réglage fin ; molette ; double-clic = retour à 12 h ; clic droit = MIDI Learn. Les potards à jupe moletée et chapeau en aluminium tourné sont tirés d'une photo : comme sur un vrai potard filmé, les reflets du métal et l'ombre restent fixes (lumière en haut à gauche), seuls le repère blanc du chapeau et le point blanc du moletage tournent, à l'angle exact.")],
 knobs_cap="RATE et DEPTH : potards moletés, repère et point blancs.",
 modes_t="5. Les huit modes",
 modes_intro="Comme dans le manuel d'origine, les modes sont classés du « pas si bizarre » au « franchement bizarre ». Cliquez sur le sélecteur MODE et tirez, utilisez la molette, ou cliquez directement sur une étiquette autour du sélecteur. Le sélecteur a de vrais crans, comme le gros potard de Ring Think : le repère saute d'une position à l'autre (jamais entre deux) et bute aux deux extrémités (SINE et ENV P). L'étiquette du mode choisi s'allume dans le bleu de la LED, comme une écriture lumineuse, et s'éteint quand l'effet est coupé.",
 modes=[["Mode", "Ce qu'on entend", "RATE", "DEPTH"],
        ["SINE", "Hauteur qui ondule en douceur : le vibrato d'ampli classique.", "Vitesse", "Intensité"],
        ["TRIANGLE", "Montée et descente plus franches que le sinus, un bend plus marqué au sommet de chaque cycle.", "Vitesse", "Intensité"],
        ["RAMP", "Un « ping » de sonar vers le haut, une descente rapide, puis un palier et un retour façon synthé.", "Vitesse", "Intensité"],
        ["SQUARE", "Deux hauteurs et un saut presque instantané entre elles : des trilles sans hammer-on ni pull-off.", "Vitesse", "Intervalle"],
        ["RANDOM", "Pleurage de disque voilé à faible DEPTH, glissandos de plus en plus ivres et aléatoires en montant DEPTH.", "Vitesse", "Intensité et désordre"],
        ["ENV D", "LFO sinus dont l'intensité suit l'attaque : plus on attaque fort, plus le vibrato est profond.", "Vitesse", "Sensibilité de l'enveloppe"],
        ["ENV R", "Vibrato sinus dont la vitesse suit l'attaque : environ 0,35 Hz au repos, jusqu'à 13 Hz en attaquant fort.", "Sensibilité de l'enveloppe", "Intensité"],
        ["ENV P", "Mode « My Bloody Valentine » : chaque attaque fait plonger la hauteur, comme un levier de vibrato, puis elle remonte. Seul mode avec signal sec.", "Sensibilité et amplitude du bend", "Mélange sec / traité"]],
 envp=["<b>Mélange en Env P</b> : DEPTH tout à gauche = tout sec, 12 h = 50 / 50 avec un peu d'annulation de phase (chorus sensible au toucher, pseudo-flanger), tout à droite = tout traité (plongées de hauteur pures). Au-delà de midi, le signal sec diminue progressivement.",
       "<b>Modes d'enveloppe</b> : comme le conseille le manuel d'origine, placez Pipeline en premier dans la chaîne, avant tout ce qui ajoute du gain. Il est réglé pour des micros à sortie faible ou moyenne ; avec des micros puissants, baissez la sensibilité (RATE en Env R et Env P, DEPTH en Env D)."],
 mode_cap="Le sélecteur MODE (Sine, puis Env P) : il saute d'un cran à l'autre (butées sur SINE et ENV P) et l'étiquette du mode choisi s'allume en bleu.",
 fs_t="6. Footswitch, LED et synchro tempo",
 fs=["<b>Flexi-Switch</b> (comme sur l'Aqueduct) : un clic bref met l'effet en marche ou le coupe. Si l'effet est coupé et que vous maintenez l'appui, le footswitch devient momentané : l'effet agit tant que vous appuyez et se coupe au relâchement (au-delà d'environ 0,45 s). Le bouton s'assombrit tant qu'il est enfoncé. Ce comportement se désactive par clic droit &gt; <b>Settings</b> &gt; <b>Flexi-Switch: hold = momentary</b>.",
     "Le bypass et les commutations passent par un court fondu de 12 ms (aucun clic), comme la commutation silencieuse à relais de la pédale. La <b>LED</b> bleue à facettes s'allume et s'éteint en fondu et éclaire la façade autour d'elle.",
     "<b>Synchro tempo</b> (clic droit &gt; <b>Tempo sync</b>) : le LFO suit le tempo du DAW et RATE choisit la valeur de note d'un cycle : " + DIVS + " (D = pointée, T = triolet). Quand le transport est en lecture, la phase du LFO est calée sur les mesures. La synchro s'applique à Sine, Triangle, Ramp, Square, Random et Env D. Sans tempo de l'hôte, l'écran affiche NO TEMPO et RATE fonctionne normalement.",
     "Tous les paramètres sont automatisables dans le DAW (Rate, Depth, Mode, Tempo Sync, Footswitch, Flexi-Switch, mode du footswitch MIDI)."],
 fs_cap="Footswitch : bypass (LED éteinte), effet en marche, enfoncé (bouton assombri).",
 midi_t="7. MIDI",
 midi_txt=["Toutes les commandes se pilotent depuis un contrôleur MIDI (footswitchs, pédales d'expression, potards). Pipeline écoute tous les canaux MIDI. <b>Aucun CC n'est assigné d'office</b> : vous choisissez chacun avec le <b>MIDI Learn</b>, le plugin ne réagit donc jamais à un contrôleur que vous n'avez pas assigné vous-même.",
           "<b>MIDI Learn</b> : clic droit sur RATE, DEPTH, MODE ou le footswitch. Le haut du menu affiche <b>MIDI Learn: &lt;Nom&gt; (CC n / none)</b> avec l'assignation actuelle, <b>Clear MIDI: &lt;Nom&gt;</b> et, tant qu'un apprentissage est en attente, <b>Cancel MIDI learn</b>. Bougez ensuite une pédale, un bouton ou appuyez sur un footswitch de votre contrôleur : l'écran affiche <b>MIDI LEARN: move a control for &lt;Nom&gt;</b>, puis <b>&lt;Nom&gt; = CC n</b> pendant 2 secondes.",
           "Le sous-menu <b>MIDI map</b> contient <b>Learn</b> pour chacune des 5 commandes (Tempo Sync compris), <b>Cancel MIDI learn</b> et <b>Clear all MIDI assignments</b>. Un numéro de CC ne pilote qu'une seule commande. <b>Les assignations sont sauvegardées avec le projet</b> : un projet enregistré avec une version précédente garde les siennes."],
 midi_hdr=["Commande", "Assignation", "Type"],
 midi=[["Rate", "MIDI Learn", "Continu 0-127 ; 14 bits avec CC n+32 pour un CC de 0 à 31"], ["Depth", "MIDI Learn", "Continu 0-127 ; 14 bits avec CC n+32"],
       ["Mode", "MIDI Learn", "Sélecteur 8 positions : 0-127 découpé en 8 zones égales (Sine à Env P)"],
       ["Tempo Sync", "MIDI Learn", "Bascule : 64 et plus = ON"],
       ["Footswitch", "MIDI Learn", "Chaque appui bascule marche / arrêt (par défaut, pour les footswitchs momentanés comme la M-Vave Chocolate) ou à accrochage (127 = on / 0 = off)"]],
 midi2=["<b>Mode du footswitch MIDI</b> : clic droit &gt; <b>Settings</b> &gt; <b>MIDI footswitch: each press toggles on / off</b> (par défaut : un appui = marche, l'appui suivant = arrêt, inutile de maintenir) ou <b>MIDI footswitch latching (127 = on / 0 = off)</b> pour les footswitchs à accrochage.",
        "<b>Pédales d'expression</b> sur RATE ou DEPTH : mouvement lissé (rampe entre deux messages, puis lissage à 2 pôles), CC 14 bits accepté, course apprise automatiquement (0 et 100 % atteints même si la pédale n'envoie que 2-116) et petites zones mortes aux butées. Une pédale sur RATE en Env P règle l'amplitude du bend en temps réel.",
        "<b>Program Change</b> 1 à 15 : presets d'usine."],
 win_t="8. Fenêtre et écran",
 win=["Pipeline utilise le format pédale simple des autres pédales NINE HANDS | DSP : la fenêtre ne peut jamais être réduite sous 60 %. Clic droit &gt; <b>Plugin size</b> : <b>60 %</b>, <b>75 %</b> ou <b>100 %</b> pour cette fenêtre ; <b>Default size (new windows)</b> choisit la taille d'ouverture de toutes les nouvelles fenêtres de Pipeline (réglage commun à toutes les instances, enregistré sur l'ordinateur). Vous pouvez aussi tirer le coin en bas à droite jusqu'à 150 % (proportions bloquées).",
      "La partie gauche de l'écran affiche pendant 2,5 s la valeur de la commande que vous venez de bouger, avec son rôle dans le mode en cours (par exemple <b>RATE (BEND RANGE)</b> en Env P, <b>DEPTH (MIX) 50 / 50</b>). Le reste du temps, elle montre le mode, la vitesse du LFO et l'écart de hauteur en cents en direct (la profondeur du bend en Env P).",
      "<b>Oscilloscope</b> : la partie droite de l'écran dessine la modulation de hauteur en direct (animée, 30 images par seconde), en défilant de droite à gauche : le bord droit, c'est ce que vous entendez maintenant. RATE change le nombre de cycles, DEPTH la hauteur, MODE la forme (sinus, triangle, rampe sonar, carré, aléatoire). Dans les modes d'enveloppe, la courbe suit votre jeu : la vague gonfle (Env D), accélère (Env R) ou plonge comme un levier de vibrato (Env P) à chaque attaque, et reste plate quand rien ne joue. En bypass, la courbe devient plate et grisée."],
 disp_cap="Écran : informations et oscilloscope en direct (Sine, Env P), puis valeur de la commande qu'on règle (Rate en Hz, Rate en synchro tempo).",
 pre_t="9. Presets",
 pre=["15 presets d'usine sont fournis (aussi dans le menu de presets du DAW et en Program Change MIDI). Les deux premiers sont les « Suggested Settings » du manuel d'origine. Neuf emplacements utilisateur peuvent être enregistrés depuis le menu des presets (ils gardent Rate, Depth, Mode et Tempo Sync)."],
 fac_hdr=["N°", "Preset", "Mode", "Rate", "Depth", "Description"],
 tips_t="10. Conseils d'utilisation",
 tips=["Dans Reaper, placez Pipeline en premier, avant votre simulateur d'ampli (par exemple avant Ampire, suivi d'Impulse pour le baffle) : les modes d'enveloppe ont besoin du signal clair et dynamique de la guitare, et un vibrato devant l'ampli sonne comme la pédale sur un pedalboard.",
       "Env P avec le Flexi-Switch : maintenez le footswitch seulement sur les accords à « tordre », pour le jeu en glissé façon Kevin Shields.",
       "Accordages graves : Pipeline n'a pas de détection de hauteur, une 7 cordes en Sol ou plus bas fonctionne sans limite. Sur les notes graves, gardez DEPTH un peu plus bas : un même écart en cents s'entend davantage en battements sur un gros accord grave.",
       "Une pédale d'expression sur DEPTH en Sine ou Triangle fait entrer le vibrato en fin de note tenue ; sur RATE, elle accélère une ondulation façon Leslie.",
       "Square à RATE élevé et DEPTH faible donne une texture rapide qui papillonne ; Random à DEPTH minimum ajoute un léger pleurage de bande aux arpèges clairs."],
 tech_t="11. Caractéristiques techniques",
 tech=[["Format", "VST3, Windows (x64) et macOS (Apple Silicon + Intel)"], ["Canaux", "Mono ou stéréo (même modulation sur les deux canaux)"],
       ["Moteur", "Ligne de retard modulée avec interpolation Hermite 4 points, tables de LFO dessinées en hauteur, suiveur d'enveloppe (attaque 1,5 ms, relâchement 140 ms), passe-bas 2 pôles à 7,2 kHz et saturation douce sur la voie traitée, fondu entre têtes de lecture aux changements de mode et de preset"],
       ["Retard", "0,6 ms minimum plus la moitié de la course de modulation (jusqu'à environ 11 ms à DEPTH maximum et RATE lent) ; aucune latence déclarée à l'hôte, comme un vibrato matériel"],
       ["Plage de hauteur", "Jusqu'à environ +4 / -6 demi-tons (limiteur de pente : jamais de lecture à l'envers)"],
       ["Fréquences", "44,1 à 192 kHz"],
       ["Visuel", "Fond 1235 x 1800 calculé en 4K ; textes, graduations, vagues, cadre et logo vectoriels, nets à toutes les tailles"],
       ["Fenêtre", "Plugin size 60 % / 75 % / 100 %, taille par défaut des nouvelles fenêtres au choix (60 % au départ), jusqu'à 150 %, jamais sous 60 % ; anti-gel v2 sous Windows"],
       ["MIDI", "Tous les canaux ; MIDI Learn sur 5 commandes (rien d'assigné par défaut, sauvegardé avec le projet), CC 14 bits, Program Change 1 à 15"]],
)

W = A4[0] - 36 * mm
def story():
    f = [NextPageTemplate("p"), Spacer(1, 1), PageBreak()]
    f.append(P(t["intro_t"], "h1")); f += [P(x) for x in t["intro"]]
    f.append(P(t["inst_t"], "h1"))
    for h, x in t["inst"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(PageBreak())
    f.append(P(t["ov_t"], "h1"))
    ov = Table([[img(annotated, 92 * mm), table(t["ov_rows"], [11 * mm, 25 * mm, W - 96 * mm - 36 * mm])]], colWidths=[96 * mm, W - 96 * mm])
    ov.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    f.append(ov); f.append(PageBreak())
    f.append(P(t["ctl_t"], "h1"))
    for h, x in t["ctl"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(KeepTogether([Spacer(1, 3 * mm), img(knobs_img, W * 0.62), P(t["knobs_cap"], "small")]))
    f.append(CondPageBreak(120 * mm))
    f.append(P(t["modes_t"], "h1")); f.append(P(t["modes_intro"]))
    f.append(table(t["modes"], [20 * mm, W - 20 * mm - 64 * mm, 32 * mm, 32 * mm]))
    f.append(Spacer(1, 3 * mm))
    f += bullets(t["envp"])
    f.append(KeepTogether([Spacer(1, 2 * mm), img(mode_img, W * 0.55), P(t["mode_cap"], "small")]))
    f.append(P(t["fs_t"], "h1")); f += bullets(t["fs"])
    f.append(KeepTogether([Spacer(1, 2 * mm), img(fs_img, W * 0.50), P(t["fs_cap"], "small")]))
    f.append(P(t["midi_t"], "h1")); f += [P(x) for x in t["midi_txt"]]
    f.append(Spacer(1, 2 * mm)); f.append(KeepTogether([table([t["midi_hdr"]] + t["midi"], [30 * mm, 24 * mm, W - 54 * mm])])); f.append(Spacer(1, 3 * mm))
    f += bullets(t["midi2"])
    f.append(P(t["win_t"], "h1")); f += [P(x) for x in t["win"]]
    f.append(KeepTogether([img(disp_img, W * 0.92), Spacer(1, 2 * mm), img(disp2_img, W * 0.92), P(t["disp_cap"], "small")]))
    f.append(CondPageBreak(235 * mm))
    f.append(P(t["pre_t"], "h1")); f += [P(x) for x in t["pre"]]
    rows = [t["fac_hdr"]]
    for i, (n, r, d, m) in enumerate(FACTORY):
        rows.append([str(i + 1), "<b>" + n + "</b>", MODES[m], rate_s(r, m), depth_s(d, m), FACT_DESC[i]])
    f.append(table(rows, [8 * mm, 32 * mm, 18 * mm, 22 * mm, 20 * mm, W - 100 * mm]))
    f.append(PageBreak())
    f.append(P(t["tips_t"], "h1")); f += bullets(t["tips"])
    f.append(KeepTogether([P(t["tech_t"], "h1"), table(t["tech"], [32 * mm, W - 32 * mm], header=False)]))
    return f

def deco(c, doc):
    c.saveState()
    c.setFillColor(DARK); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 6.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
    c.setFont("Pop", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Pipeline (NINE HANDS | DSP) · v" + VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="PIPELINE - Notice v" + VERSION, author="NINE HANDS | DSP")
# ---- Couverture « minimale » (modele 6, valide nov. 2026) : gabarit fixe commun a toutes les notices ----
COVER_NAME = "PIPELINE"
PEDAL_H, PEDAL_MAXW, PEDAL_TOP = 82 * mm, 115 * mm, 84 * mm
LANG_TOP = 18 * mm
NAME_TOP, NAME_PT = 194 * mm, 30
SUB_TOP, SUB_PT = 208 * mm, 10
LOGO_W, LOGO_BOTTOM = 38 * mm, 22 * mm
BAND_H = 3 * mm
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, 0, A4[0], BAND_H, stroke=0, fill=1)
    def line(text, top, font, size, cs, col):
        w = pdfmetrics.stringWidth(text, font, size) + cs * (len(text) - 1)
        tx = c.beginText((A4[0] - w) / 2, A4[1] - top - size * 0.8); tx.setFont(font, size); tx.setCharSpace(cs)
        tx.setFillColor(col); tx.textOut(text); c.drawText(tx)
    line(t["lang"], LANG_TOP, "PopM", 8.5, 0, ACC_L)
    ci = Image.open(cover); iw, ih = ci.size
    cw_ = iw / 1.32; ch_ = (ih - int(cw_ * 0.16)) / 1.2; pad_ = int(cw_ * 0.16)
    k = min(PEDAL_H / ch_, PEDAL_MAXW / cw_)
    dw, dh = iw * k, ih * k
    y0 = A4[1] - (PEDAL_TOP + (PEDAL_H - ch_ * k) / 2) + pad_ * k
    c.drawImage(cover, (A4[0] - dw) / 2, y0 - dh, dw, dh)
    line(COVER_NAME, NAME_TOP - NAME_PT * 0.02, "Title", NAME_PT, NAME_PT * 0.5, colors.white)
    line(t["sub"], SUB_TOP, "Pop", SUB_PT, 1.5, colors.HexColor("#BDC4B8"))
    lw, lh = Image.open(LOGO_PNG).size
    c.drawImage(LOGO_PNG, (A4[0] - LOGO_W) / 2, LOGO_BOTTOM, LOGO_W, LOGO_W * lh / lw, mask="auto")
    c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
doc.build(story())
print(OUT)
