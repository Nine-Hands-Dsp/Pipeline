#include "PluginEditor.h"
#include "BinaryData.h"
#include "Layout.h"
#include "WigaWindowSize.h"

using namespace juce;

namespace
{
    // positions dans le repere du plugin 617,5 x 900 unites (fond 1235 x 1800 / 2), generees par tools/make_art.py dans Layout.h
    const float knobHalf = layout::knobR + 6.0f;
    const float modeHalf = layout::modeR + 4.0f;
    const Rectangle<float> statusRect = layout::rowRect;
    // ligne du haut de l'ecran : texte a gauche, oscilloscope de la modulation a droite
    const Rectangle<float> textRect  = statusRect.withWidth (statusRect.getWidth() * 0.58f).withTrimmedLeft (13.0f);
    const Rectangle<float> scopeRect = statusRect.withX (statusRect.getX() + statusRect.getWidth() * 0.60f)
                                                 .withWidth (statusRect.getWidth() * 0.30f).reduced (7.5f, 8.5f);
    const Rectangle<float> presetRect = layout::barRect;
    const Rectangle<float> footRect (layout::footPos.x - layout::fsS * 0.5f, layout::footPos.y - layout::fsS * 0.5f, layout::fsS, layout::fsS);

    const float rotStart = -150.0f, rotEnd = 150.0f;    // degres, 0 = midi (repere vers le haut)
    float knobAngle (float v) { return degreesToRadians (rotStart + (rotEnd - rotStart) * jlimit (0.0f, 10.0f, v) / 10.0f); }
    float modeAngle (int p)   { return degreesToRadians (layout::modeFirstDeg + layout::modeStepDeg * (float) jlimit (0, 7, p)); }

    const Colour inkWhite (0xffd8dad9), lcd (0xff8ccdef);       // couleurs des textes de l'ecran
    const Colour inkCream (0xffefe4ca);
    const Colour ledBlue (0xff1e87ff), ledCore (0xff55b9ff);    // couleur de la LED allumee (photo recoloree)                         // serigraphie (meme creme que l'ecume des vagues)

    const char* const valueIds[] = { "rate", "depth", "mode", "sync", "active", "flexi" };
    constexpr int numValueIds = 6;

    Rectangle<float> square (Point<float> c, float half) { return { c.x - half, c.y - half, half * 2.0f, half * 2.0f }; }
}

//==============================================================================
// POTARD
//==============================================================================
PedalKnob::PedalKnob (RangedAudioParameter& p)
    : attachment (p, [this] (float v) { value = v; })
{
    attachment.sendInitialUpdate();
    setMouseCursor (MouseCursor::PointingHandCursor);
}

bool PedalKnob::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= (float) getWidth() * 0.5f;
}

void PedalKnob::setV (float v)
{
    attachment.setValueAsPartOfGesture (jlimit (0.0f, 10.0f, v));
    if (onUserChange) onUserChange();
}

void PedalKnob::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    dragging = true;
    startV = value;
    attachment.beginGesture();
}

void PedalKnob::mouseDrag (const MouseEvent& e)
{
    if (! dragging) return;
    const float sens = e.mods.isShiftDown() ? 900.0f : 220.0f;     // Maj = reglage fin
    const float d = (float) (e.getDistanceFromDragStartX() - e.getDistanceFromDragStartY());
    setV (startV + d * 10.0f / sens);
}

void PedalKnob::mouseUp (const MouseEvent&)
{
    if (dragging) attachment.endGesture();
    dragging = false;
}

void PedalKnob::mouseDoubleClick (const MouseEvent&)
{
    attachment.setValueAsCompleteGesture (5.0f);
    if (onUserChange) onUserChange();
}

void PedalKnob::mouseWheelMove (const MouseEvent& e, const MouseWheelDetails& w)
{
    if (std::abs (w.deltaY) < 0.0001f) return;
    const float v = value + (w.deltaY > 0 ? 0.2f : -0.2f) * (e.mods.isShiftDown() ? 0.25f : 1.0f);
    attachment.setValueAsCompleteGesture (jlimit (0.0f, 10.0f, v));
    if (onUserChange) onUserChange();
}

//==============================================================================
// SELECTEUR MODE
//==============================================================================
ModeKnob::ModeKnob (RangedAudioParameter& p)
    : attachment (p, [this] (float v)
                  {
                      pos = jlimit (0, 7, roundToInt (v));
                      targetAngle = modeAngle (pos);
                  })
{
    attachment.sendInitialUpdate();
    shownAngle = targetAngle;
    setMouseCursor (MouseCursor::PointingHandCursor);
}

bool ModeKnob::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= (float) getWidth() * 0.5f;
}

void ModeKnob::moveTo (int p)
{
    p = jlimit (0, 7, p);
    if (p == pos) return;
    attachment.setValueAsCompleteGesture ((float) p);
    if (onUserChange) onUserChange();
}

void ModeKnob::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    dragging = true;
    accum = 0.0f;
    lastDrag = e.position;
}

// Selecteur a crans, comme le gros potard de Ring Think : le deplacement de la souris s'accumule et chaque tranche de
// 16 px fait sauter le repere d'un cran entier, instantanement (aucune position intermediaire, aucun glissement).
// Aux extremites (SINE / ENV P) il reste en butee.
void ModeKnob::mouseDrag (const MouseEvent& e)
{
    if (! dragging) return;
    constexpr float pxPerStep = 16.0f;
    accum += (e.position.x - lastDrag.x) - (e.position.y - lastDrag.y);
    lastDrag = e.position;
    while (accum >=  pxPerStep) { accum -= pxPerStep; if (pos < 7) moveTo (pos + 1); else accum = 0.0f; }
    while (accum <= -pxPerStep) { accum += pxPerStep; if (pos > 0) moveTo (pos - 1); else accum = 0.0f; }
}

void ModeKnob::mouseUp (const MouseEvent&)
{
    dragging = false;
}

void ModeKnob::mouseWheelMove (const MouseEvent&, const MouseWheelDetails& w)
{
    if (std::abs (w.deltaY) > 0.0f) moveTo (pos + (w.deltaY > 0 ? 1 : -1));
}

bool ModeKnob::tick()
{
    // aucun glissement : le repere est dessine directement sur le cran (redessin seulement quand il change)
    if (shownAngle == targetAngle) return false;
    shownAngle = targetAngle;
    return true;
}

//==============================================================================
// FOOTSWITCH (Flexi-Switch)
//==============================================================================
FootSwitchArea::FootSwitchArea (RangedAudioParameter& p, std::atomic<float>* flexiFlag)
    : flexi (flexiFlag),
      attachment (p, [this] (float v) { value = v > 0.5f; })
{
    attachment.sendInitialUpdate();
    setMouseCursor (MouseCursor::PointingHandCursor);
}

bool FootSwitchArea::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= (float) getWidth() * 0.5f;
}

void FootSwitchArea::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    pressed = true;
    downTime = Time::getMillisecondCounterHiRes();
    turnedOnByPress = ! value;
    if (onPressChange) onPressChange();
    attachment.setValueAsCompleteGesture (value ? 0.0f : 1.0f);    // bascule des l'appui (comme Echoflex)
    if (onUserChange) onUserChange();
}

void FootSwitchArea::mouseUp (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) return;
    // Flexi-Switch : appui maintenu = momentane -> au relachement, l'effet se coupe
    const bool flex = flexi != nullptr && flexi->load() > 0.5f;
    if (pressed && flex && turnedOnByPress && Time::getMillisecondCounterHiRes() - downTime > 450.0 && value)
    {
        attachment.setValueAsCompleteGesture (0.0f);
        if (onUserChange) onUserChange();
    }
    pressed = false;
    if (onPressChange) onPressChange();
}

//==============================================================================
// EDITEUR
//==============================================================================
PipelineAudioProcessorEditor::PipelineAudioProcessorEditor (PipelineAudioProcessor& p)
    : AudioProcessorEditor (&p), proc (p),
      rateKnob  (*p.apvts.getParameter ("rate")),
      depthKnob (*p.apvts.getParameter ("depth")),
      modeKnob  (*p.apvts.getParameter ("mode")),
      foot (*p.apvts.getParameter ("active"), p.apvts.getRawParameterValue ("flexi"))
{
    setLookAndFeel (&lnf);
    background = ImageCache::getFromMemory (BinaryData::background_png, BinaryData::background_pngSize);
    controls   = ImageCache::getFromMemory (BinaryData::controls_png, BinaryData::controls_pngSize);
    glowLed    = ImageCache::getFromMemory (BinaryData::glow_led_png, BinaryData::glow_led_pngSize);
    ledOn      = ImageCache::getFromMemory (BinaryData::led_on_png, BinaryData::led_on_pngSize);
    if (auto xml = XmlDocument::parse (String::fromUTF8 (BinaryData::NineHandsLogo_svg, BinaryData::NineHandsLogo_svgSize)))
        logo = Drawable::createFromSVG (*xml);
    if (auto xml = XmlDocument::parse (String::fromUTF8 (BinaryData::PipelineWaves_svg, BinaryData::PipelineWaves_svgSize)))
        waves = Drawable::createFromSVG (*xml);
    {
        const int p0 = jlimit (0, 7, roundToInt (proc.raw ("mode")));
        labelLit[p0] = 1.0f;
    }
    labelFace = Typeface::createSystemTypefaceFor (BinaryData::BarlowCondensedSemiBold_ttf, BinaryData::BarlowCondensedSemiBold_ttfSize);
    boldFace  = Typeface::createSystemTypefaceFor (BinaryData::BarlowCondensedBold_ttf, BinaryData::BarlowCondensedBold_ttfSize);
    pMedium   = Typeface::createSystemTypefaceFor (BinaryData::PoppinsMedium_ttf, BinaryData::PoppinsMedium_ttfSize);
    pBold     = Typeface::createSystemTypefaceFor (BinaryData::PoppinsBold_ttf, BinaryData::PoppinsBold_ttfSize);
    pLight    = Typeface::createSystemTypefaceFor (BinaryData::PoppinsLight_ttf, BinaryData::PoppinsLight_ttfSize);
    buildPrint();
    lnf.reg = pMedium; lnf.med = pMedium; lnf.bold = pBold;     // menus en Poppins, comme Octopus

    auto edited = [this] { proc.currentPreset = -1; };
    // index des commandes = learnDef du processeur (0 Rate, 1 Depth, 2 Mode, 3 Sync, 4 footswitch)
    rateKnob.onRightClick  = [this] { showContextMenu (0); };
    depthKnob.onRightClick = [this] { showContextMenu (1); };
    modeKnob.onRightClick  = [this] { showContextMenu (2); };
    foot.onRightClick      = [this] { showContextMenu (4); };
    rateKnob.onUserChange = depthKnob.onUserChange = modeKnob.onUserChange = edited;
    foot.onPressChange = [this] { askRepaint (scaled (footRect)); };
    for (auto* c : std::initializer_list<Component*> { &rateKnob, &depthKnob, &modeKnob, &foot })
        addAndMakeVisible (c);

    for (int i = 0; i < numValueIds; ++i) lastValues[i] = proc.raw (valueIds[i]);
    lastPresetCounter = proc.presetCounter.load();
    lastMidiCount = proc.midiCounter.load();
    ledLevel = proc.raw ("active") > 0.5f ? 1.0f : 0.0f;

    // taille par defaut = taille minimale (impossible de reduire en dessous), proportions bloquees
    const int defaultW = roundToInt ((float) defaultH * baseW / baseH);
    setResizable (true, true);
    setResizeLimits (defaultW, defaultH, roundToInt ((float) maxH * baseW / baseH), maxH);
    if (auto* cons = getConstrainer())
        cons->setFixedAspectRatio ((double) baseW / (double) baseH);
    setOpaque (true);
    setSize (defaultW, defaultH);
    // taille des nouvelles fenetres : celle choisie dans le menu « Default size (new windows) »
    setScaledHeight (sizeHeight (WigaWindowSize::defaultIndex (JucePlugin_Name, numSizes)));
    rebuildCaches();
    startTimerHz (30);
}

PipelineAudioProcessorEditor::~PipelineAudioProcessorEditor() { stopTimer(); setLookAndFeel (nullptr); }

//==============================================================================
int PipelineAudioProcessorEditor::sizeHeight (int idx)
{
    const int h[numSizes] = { (int) defaultH, roundToInt (refH * 0.75f), (int) refH };
    return h[jlimit (0, numSizes - 1, idx)];
}

void PipelineAudioProcessorEditor::setScaledHeight (int h)
{
    h = jlimit ((int) defaultH, (int) maxH, h);
    setSize (roundToInt ((float) h * baseW / baseH), h);
}

Rectangle<int> PipelineAudioProcessorEditor::scaled (Rectangle<float> r) const
{
    const float s = (float) getHeight() / baseH;
    return r.transformedBy (AffineTransform::scale (s)).getSmallestIntegerContainer();
}

float PipelineAudioProcessorEditor::physicalScale() const
{
    if (forcedScale > 0.0f) return forcedScale;
    return jlimit (1.0f, 4.0f, (float) Component::getApproximateScaleFactorForComponent (this));
}

void PipelineAudioProcessorEditor::showStatus() { statusUntil = Time::getMillisecondCounterHiRes() + 2500.0; }

//==============================================================================
// caches d'affichage : fond et calque lumineux a la taille de la fenetre (reconstruits par le timer seulement)
//==============================================================================
void PipelineAudioProcessorEditor::rebuildCaches (float sc)
{
    if (sc <= 0.0f) sc = cacheScale > 0.0f ? cacheScale : physicalScale();
    const int w = getWidth(), h = getHeight();
    if (w <= 0 || h <= 0) return;
    if (w == cacheW && h == cacheH && std::abs (sc - cacheScale) < 0.01f && bgScaled.isValid()) return;
    cacheW = w; cacheH = h; cacheScale = sc;

    // fond a la resolution physique de l'ecran, puis couche vectorielle (vagues, serigraphie, logo) dessinee par-dessus :
    // nette a toutes les tailles (Retina / 4K), calculee ici une fois (timer), jamais dans paint()
    const int pw = roundToInt ((float) w * sc), ph = roundToInt ((float) h * sc);
    Image composed (Image::ARGB, pw, ph, true);
    {
        Graphics g (composed);
        g.setImageResamplingQuality (Graphics::highResamplingQuality);
        g.drawImage (background, Rectangle<float> (0.0f, 0.0f, (float) pw, (float) ph));
        g.addTransform (AffineTransform::scale ((float) ph / baseH));
        drawVectorLayer (g);
    }
    bgScaled = composed;

    const float s = (float) h / baseH;
    const int tw = roundToInt (layout::glowRect.getWidth() * s * sc), th = roundToInt (layout::glowRect.getHeight() * s * sc);
    glowLedS = (tw >= glowLed.getWidth()) ? glowLed : glowLed.rescaled (tw, th, Graphics::highResamplingQuality);
    repaint();
}

void PipelineAudioProcessorEditor::resized()
{
    // anti-gel : jamais de setSize ici ; les limites du constrainer suffisent
    rateKnob.setBounds  (scaled (square (layout::ratePos,  knobHalf)));
    depthKnob.setBounds (scaled (square (layout::depthPos, knobHalf)));
    modeKnob.setBounds  (scaled (square (layout::modePos,  modeHalf)));
    foot.setBounds (scaled (square (layout::footPos, layout::footHit)));
    resizeSettle = 4;
}

//==============================================================================
// Anti-gel v2 (NINE HANDS | DSP) :
//  1. moteur de rendu logiciel force sur Windows, applique a chaque nouvelle fenetre hote et reverifie toutes les secondes ;
//  2. aucun calcul lourd dans paint() : caches reconstruits par le timer (apres stabilisation de la taille / changement d'echelle) ;
//  3. chien de garde : redessin demande non servi depuis 1,5 s -> moteur de rendu reapplique, fenetre redessinee ;
//  4. cote audio : aucun appel a l'hote ni allocation depuis le thread audio (voir PluginProcessor).
void PipelineAudioProcessorEditor::useSoftwareRenderer()
{
    auto* peer = getPeer();
    if (peer != lastPeer) { lastPeer = peer; repaint(); }
   #if JUCE_WINDOWS
    if (peer != nullptr)
    {
        int sw = peer->getAvailableRenderingEngines().indexOf ("Software Renderer");
        if (sw < 0) sw = 0;
        if (peer->getCurrentRenderingEngine() != sw)
            peer->setCurrentRenderingEngine (sw);
    }
   #endif
}

void PipelineAudioProcessorEditor::parentHierarchyChanged() { useSoftwareRenderer(); }
void PipelineAudioProcessorEditor::visibilityChanged()      { useSoftwareRenderer(); if (isShowing()) repaint(); }

void PipelineAudioProcessorEditor::askRepaint (Rectangle<int> r)
{
    if (repaintAskedMs <= 0.0) repaintAskedMs = Time::getMillisecondCounterHiRes();
    repaint (r);
}

//==============================================================================
String PipelineAudioProcessorEditor::rateText (float v) const
{
    if (proc.raw ("sync") > 0.5f)
        return String (PipelineAudioProcessor::divisionName (PipelineAudioProcessor::divisionForRate (v)))
               + (proc.hostBpm.load() > 0.0 ? "" : "  (NO TEMPO)");
    const float hz = pipeline::rateToHz (v / 10.0f);
    return String (hz, hz < 1.0f ? 2 : 1) + " Hz";
}

String PipelineAudioProcessorEditor::buildStatusLine() const
{
    const int i = lastChanged;
    if (i < 0) return {};
    const float v = proc.raw (valueIds[i]);
    const int mode = jlimit (0, 7, roundToInt (proc.raw ("mode")));
    switch (i)
    {
        case 0:
            if (mode == pipeline::EnvR) return "RATE (SENSITIVITY)  " + String (roundToInt (v * 10.0f)) + " %";
            if (mode == pipeline::EnvP) return "RATE (BEND RANGE)  " + String (roundToInt (v * 10.0f)) + " %";
            return "RATE  " + rateText (v) + "   " + String (roundToInt (v * 10.0f)) + " %";
        case 1:
            if (mode == pipeline::EnvD) return "DEPTH (SENSITIVITY)  " + String (roundToInt (v * 10.0f)) + " %";
            if (mode == pipeline::EnvP)
            {
                const int wet = roundToInt (v * 10.0f);
                return "DEPTH (MIX)  " + (wet <= 0 ? String ("ALL DRY") : wet >= 100 ? String ("ALL WET") : String (100 - wet) + " / " + String (wet));
            }
            return "DEPTH  " + String (roundToInt (v * 10.0f)) + " %";
        case 2: return "MODE  " + PipelineAudioProcessor::modeNames()[jlimit (0, 7, roundToInt (v))];
        case 3: return v > 0.5f ? "TEMPO SYNC  ON" : "TEMPO SYNC  OFF";
        case 4: return v > 0.5f ? "EFFECT  ON" : "BYPASS";
        default: return v > 0.5f ? "FLEXI-SWITCH  ON" : "FLEXI-SWITCH  OFF";
    }
}

// au repos : ce que fait le vibrato en ce moment (mode, vitesse, ecart de hauteur crete)
String PipelineAudioProcessorEditor::buildInfoLine() const
{
    if (proc.raw ("active") < 0.5f) return "BYPASS";
    const int mode = jlimit (0, 7, roundToInt (proc.raw ("mode")));
    const auto name = PipelineAudioProcessor::modeNames()[mode];
    const String cents = String (CharPointer_UTF8 ("\xc2\xb1")) + String (roundToInt (peakCents)) + " c";
    if (mode == pipeline::EnvP) return name + "   BEND " + String (-roundToInt (peakCents)) + " c";
    if (mode == pipeline::EnvR) return name + "   " + cents;
    return name + "  " + rateText (proc.raw ("rate")) + "  " + cents;
}

String PipelineAudioProcessorEditor::buildPresetLine() const
{
    const int cp = proc.currentPreset.load();
    String s;
    if (cp >= 0 && cp < PipelineAudioProcessor::getNumFactoryPresets())
        s << "P" << (cp + 1) << "  " << PipelineAudioProcessor::getFactoryPreset (cp).name;
    else if (cp > 100) s << "User " << (cp - 100);
    else               s << "Edited";
    return s;
}

//==============================================================================
void PipelineAudioProcessorEditor::timerCallback()
{
    const double now = Time::getMillisecondCounterHiRes();
    if (getPeer() != lastPeer || now - lastRendererCheckMs > 1000.0) { lastRendererCheckMs = now; useSoftwareRenderer(); }

    if (resizeSettle > 0 && --resizeSettle == 0) rebuildCaches();
    else if (resizeSettle == 0 && now - lastScaleCheckMs > 250.0)
    {
        lastScaleCheckMs = now;
        const float sc = physicalScale();
        if (std::abs (sc - cacheScale) > 0.01f) rebuildCaches (sc);
    }

    if (repaintAskedMs > 0.0 && isShowing() && now - repaintAskedMs > 1500.0 && lastPaintMs < repaintAskedMs)
    {
        repaintAskedMs = 0.0;
        lastPeer = nullptr;
        useSoftwareRenderer();
        repaint();
    }

    // reperes des potards et du selecteur : redessines seulement s'ils ont bouge
    PedalKnob* knobs[2] = { &rateKnob, &depthKnob };
    const Point<float> kc[2] = { layout::ratePos, layout::depthPos };
    for (int k = 0; k < 2; ++k)
        if (std::abs (knobs[k]->getValue() - drawnKnob[k]) > 0.002f)
        {
            drawnKnob[k] = knobs[k]->getValue();
            askRepaint (scaled (square (kc[k], layout::knobR + 2.0f)));
        }
    if (modeKnob.tick()) askRepaint (scaled (square (layout::modePos, layout::modeR + 2.0f)));
    // etiquette du mode choisi : s'allume en bleu (fondu 0,35 a l'allumage, 0,22 a l'extinction, par image a 30 Hz)
    for (int i = 0; i < 8; ++i)
    {
        // allumee seulement quand l'effet est en marche (pedale coupee : toutes les etiquettes s'eteignent)
        const float t = (i == modeKnob.getPosition() && proc.raw ("active") > 0.5f) ? 1.0f : 0.0f;
        labelLit[i] += (t - labelLit[i]) * (t > labelLit[i] ? 0.35f : 0.22f);
        if (std::abs (labelLit[i] - t) < 0.004f) labelLit[i] = t;
        if (std::abs (labelLit[i] - drawnLabel[i]) > 0.003f)
        {
            drawnLabel[i] = labelLit[i];
            askRepaint (scaled (labelBox[i].expanded (5.0f)));
        }
    }

    // ligne d'etat : apparait quand un reglage bouge, reste 2,5 s puis s'efface
    int changed = -1, numChanged = 0;
    for (int i = 0; i < numValueIds; ++i)
    {
        const float v = proc.raw (valueIds[i]);
        if (std::abs (v - lastValues[i]) > 1.0e-4f) { lastValues[i] = v; changed = i; ++numChanged; }
    }
    const int pcount = proc.presetCounter.load();
    if (pcount != lastPresetCounter) { lastPresetCounter = pcount; numChanged = 0; }
    if (numChanged == 1 && changed != 4) { lastChanged = changed; showStatus(); learnLineUntil = 0.0; }
    if (rateKnob.isDragging())  { lastChanged = 0; showStatus(); learnLineUntil = 0.0; }
    if (depthKnob.isDragging()) { lastChanged = 1; showStatus(); learnLineUntil = 0.0; }

    // MIDI Learn : attente puis confirmation 2 s dans l'ecran
    const int lt = proc.learnTarget.load();
    const int learned = proc.lastLearned.exchange (-1);
    if (learned >= 0)
    {
        learnLine = String (PipelineAudioProcessor::learnDef (learned).name) + " = CC " + String (proc.ccMap[learned].load());
        learnLineUntil = now + 2000.0;
        statusUntil = jmax (statusUntil, learnLineUntil);
    }
    else if (lt >= 0)
    {
        learnLine = "MIDI LEARN: move a control for " + String (PipelineAudioProcessor::learnDef (lt).name);
        learnLineUntil = now + 200.0;
        statusUntil = jmax (statusUntil, now + 200.0);
    }
    const int mc = proc.midiCounter.load();
    if (mc != lastMidiCount) { lastMidiCount = mc; midiFlash = 8; }
    if (midiFlash > 0) --midiFlash;

    const float target = now < statusUntil ? 1.0f : 0.0f;
    statusAlpha += (target - statusAlpha) * (target > statusAlpha ? 0.45f : 0.12f);
    if (statusAlpha < 0.005f) statusAlpha = 0.0f;
    if (statusAlpha > 0.995f) statusAlpha = 1.0f;

    // ecart de hauteur crete (retombe en ~1 s) pour la ligne d'info
    const float c = std::abs (proc.shownCents.load());
    peakCents = jmax (c, peakCents * 0.93f);
    if (peakCents < 0.5f) peakCents = 0.0f;

    // LED : allumage / extinction en fondu (0,45 / 0,28 par image a 30 Hz)
    const bool on = proc.raw ("active") > 0.5f;
    ledLevel += ((on ? 1.0f : 0.0f) - ledLevel) * (on ? 0.45f : 0.28f);
    if (ledLevel < 0.003f) ledLevel = 0.0f;
    if (ledLevel > 0.997f) ledLevel = 1.0f;
    if (std::abs (ledLevel - drawnLed) > 0.004f)
    {
        drawnLed = ledLevel;
        askRepaint (scaled (layout::glowRect));
    }

    // oscilloscope : historique de l'enveloppe et de la hauteur (modes Env), phase du LFO, redessin a 30 Hz si actif
    {
        envHist[histPos] = jlimit (0.0f, 1.0f, proc.shownEnv.load());
        centsHist[histPos] = proc.shownCents.load();
        histPos = (histPos + 1) % histN;
        const double dt = lastScopeMs > 0.0 ? jlimit (0.0, 0.2, (now - lastScopeMs) * 0.001) : 0.0;
        lastScopeMs = now;
        const float hz = proc.raw ("sync") > 0.5f && proc.shownHz.load() > 0.0f ? proc.shownHz.load() : pipeline::rateToHz (proc.raw ("rate") / 10.0f);
        scopePhase = std::fmod (scopePhase + (double) hz * dt, 4096.0);
        if (proc.raw ("active") > 0.5f || scopeWasLive)
            askRepaint (scaled (scopeRect.expanded (4.0f)));
        scopeWasLive = proc.raw ("active") > 0.5f;
    }

    // l'info change souvent : rafraichie au plus toutes les 150 ms (lisible, pas de scintillement)
    const auto l1 = (learnLineUntil > 0.0 && now < learnLineUntil + 800.0 ? learnLine : buildStatusLine());
    String info = lastInfo;
    if (now >= infoNextMs) { info = buildInfoLine(); infoNextMs = now + 150.0; }
    const auto pl = buildPresetLine();
    const bool textChanged = l1 != lastLine1 || info != lastInfo;
    lastLine1 = l1; lastInfo = info;
    if (std::abs (statusAlpha - drawnStatus) > 0.003f || textChanged)
    {
        drawnStatus = statusAlpha;
        askRepaint (scaled (statusRect.expanded (4.0f)));
    }
    if (pl != lastPreset || hoverZone != drawnHover || midiFlash > 0)
    {
        lastPreset = pl; drawnHover = hoverZone;
        askRepaint (scaled (presetRect.expanded (3.0f)));
    }
}

//==============================================================================
void PipelineAudioProcessorEditor::drawLed (Graphics& g)
{
    // la facade recoit la lumiere de la LED : calque precalcule (fond x eclairement x couleur), avec canal alpha ;
    // puis la lentille allumee (photo de la LED a facettes, recoloree en bleu) en fondu
    if (ledLevel > 0.003f)
    {
        g.setOpacity (ledLevel);
        if (glowLedS.isValid()) g.drawImage (glowLedS, layout::glowRect);
        if (ledOn.isValid())    g.drawImage (ledOn, square (layout::ledPos, layout::ledS * 0.5f));
        g.setOpacity (1.0f);
    }
}

//==============================================================================
// Serigraphie vectorielle : construite une fois en chemins (unites du plugin)
//==============================================================================
void PipelineAudioProcessorEditor::buildPrint()
{
    printPath.clear();
    int idx = 0;
    for (const auto& t : layout::texts)
    {
        const Typeface::Ptr face = t.font == 1 ? pBold : (t.font == 2 ? pLight : pMedium);
        const Font font (FontOptions (face).withPointHeight (t.em));
        const String str (t.s);
        float total = 0.0f;
        for (int i = 0; i < str.length(); ++i)
            total += GlyphArrangement::getStringWidth (font, String::charToString (str[i])) + (i > 0 ? t.track : 0.0f);
        const float base = (font.getAscent() - font.getDescent()) * 0.5f;     // centre vertical entre ascendante et descendante
        GlyphArrangement ga;
        float x = -total * 0.5f;
        for (int i = 0; i < str.length(); ++i)
        {
            const String ch = String::charToString (str[i]);
            ga.addLineOfText (font, ch, x, base);
            x += GlyphArrangement::getStringWidth (font, ch) + t.track;
        }
        Path p; ga.createPath (p);
        p.applyTransform (AffineTransform::rotation (-t.rot * MathConstants<float>::pi / 180.0f).translated (t.x, t.y));
        const int li = idx - layout::modeLabelFirst;
        if (li >= 0 && li < 8) { labelPath[li] = p; labelBox[li] = p.getBounds(); }
        printPath.addPath (p);
        ++idx;
    }
    for (const auto& k : layout::ticks)
    {
        Path l; l.startNewSubPath (k.x0, k.y0); l.lineTo (k.x1, k.y1);
        PathStrokeType (k.w, PathStrokeType::curved, PathStrokeType::rounded).createStrokedPath (l, l);
        printPath.addPath (l);
    }
    for (const auto& v : layout::wavy)
    {
        Path l;
        const int n = 80;
        for (int i = 0; i <= n; ++i)
        {
            const float u = (float) i / (float) n;
            const float x = v.x0 + (v.x1 - v.x0) * u;
            const float y = v.y - v.amp * std::sin (MathConstants<float>::twoPi * v.periods * u);
            if (i == 0) l.startNewSubPath (x, y); else l.lineTo (x, y);
        }
        PathStrokeType (v.w, PathStrokeType::curved, PathStrokeType::rounded).createStrokedPath (l, l);
        printPath.addPath (l);
    }
    framePath.clear();
    framePath.addRoundedRectangle (layout::faceRect, layout::faceR);
}

// couche cuite dans le cache : vagues (hors commandes et ecran), cadre interieur, serigraphie, logo
void PipelineAudioProcessorEditor::drawVectorLayer (Graphics& g)
{
    if (waves != nullptr)
    {
        Graphics::ScopedSaveState ss (g);
        Path clip;
        clip.addRoundedRectangle (layout::faceRect, layout::faceR);
        g.reduceClipRegion (clip);
        waves->draw (g, 1.0f, AffineTransform::scale (layout::waveA, layout::waveC).translated (layout::waveB, layout::waveD));
    }
    g.setColour (inkCream.withAlpha (0.9f));
    g.strokePath (framePath, PathStrokeType (layout::faceLineW));
    g.setColour (inkCream);
    g.fillPath (printPath);
    if (logo != nullptr)
    {
        const auto vb = logo->getDrawableBounds();
        const float w = layout::logoW, h = w * vb.getHeight() / jmax (1.0f, vb.getWidth());
        logo->drawWithin (g, { layout::logoPos.x - w * 0.5f, layout::logoPos.y - h * 0.5f, w, h }, RectanglePlacement::centred, 0.95f);
    }
    // commandes (potards, LED eteinte, footswitch, jacks) et leurs ombres, au-dessus de la serigraphie et des vagues
    if (controls.isValid())
    {
        g.setOpacity (1.0f);                          // drawImage prend l'opacite de la couleur courante
        g.setImageResamplingQuality (Graphics::highResamplingQuality);
        g.drawImage (controls, Rectangle<float> (0.0f, 0.0f, baseW, baseH));
    }
    // barre de presets : filet fin (sur le verre de l'ecran, qui fait partie du calque des commandes)
    g.setColour (inkWhite.withAlpha (0.28f));
    g.drawRoundedRectangle (presetRect.reduced (0.5f), 4.0f, 1.0f);
}

// etiquette du mode choisi : ecriture LED bleue (halo doux + trait clair), en fondu
void PipelineAudioProcessorEditor::drawModeLabels (Graphics& g)
{
    for (int i = 0; i < 8; ++i)
        if (labelLit[i] > 0.003f)
        {
            const float a = labelLit[i];
            // meme bleu que la LED allumee : halo doux, corps sature, coeur plus clair
            g.setColour (ledBlue.withAlpha (0.12f * a));
            for (float r : { 3.0f, 1.8f })
                g.strokePath (labelPath[i], PathStrokeType (r, PathStrokeType::curved, PathStrokeType::rounded));
            g.setColour (ledBlue.withAlpha (a));
            g.fillPath (labelPath[i]);
            g.setColour (ledCore.withAlpha (0.35f * a));
            g.fillPath (labelPath[i], AffineTransform::translation (-0.25f, -0.25f));
        }
}

// potards moletes (photo du kit) : le corps, ses reflets et son ombre font partie du fond ;
// seuls le repere blanc du chapeau et le point blanc du moletage sont dessines, a l'angle exact
void PipelineAudioProcessorEditor::drawKnobs (Graphics& g)
{
    struct K { Point<float> c; float r, angle; bool dot; };
    const K ks[3] = { { layout::ratePos,  layout::knobR, knobAngle (rateKnob.getValue()),  true },
                      { layout::depthPos, layout::knobR, knobAngle (depthKnob.getValue()), true },
                      { layout::modePos,  layout::modeR, modeKnob.getShownAngle(),         false } };
    for (const auto& k : ks)
    {
        const float R = k.r;
        const float ux = std::sin (k.angle), uy = -std::cos (k.angle);
        Path line;
        line.startNewSubPath (k.c.x + ux * R * layout::idxR0, k.c.y + uy * R * layout::idxR0);
        line.lineTo          (k.c.x + ux * R * layout::idxR1, k.c.y + uy * R * layout::idxR1);
        const PathStrokeType stroke (R * layout::idxHalfW * 2.0f, PathStrokeType::curved, PathStrokeType::butt);
        g.setColour (Colours::black.withAlpha (0.40f));
        g.strokePath (line, stroke, AffineTransform::translation (R * 0.010f, R * 0.015f));
        g.setGradientFill (ColourGradient (Colour (0xfff6f6f8), k.c.x - R * 0.4f, k.c.y - R * 0.4f,
                                           Colour (0xffcfcfd3), k.c.x + R * 0.4f, k.c.y + R * 0.4f, false));
        g.strokePath (line, stroke);
        if (k.dot)
        {
            const Point<float> d (k.c.x + ux * R * layout::dotR, k.c.y + uy * R * layout::dotR);
            const float dr = R * layout::dotSize;
            g.setColour (Colours::black.withAlpha (0.5f));
            g.fillEllipse (d.x - dr + R * 0.01f, d.y - dr + R * 0.015f, dr * 2.0f, dr * 2.0f);
            g.setGradientFill (ColourGradient (Colours::white, d.x - dr * 0.4f, d.y - dr * 0.5f,
                                               Colour (0xffc2c2c6), d.x + dr, d.y + dr, true));
            g.fillEllipse (d.x - dr, d.y - dr, dr * 2.0f, dr * 2.0f);
        }
    }
}

void PipelineAudioProcessorEditor::drawFootswitch (Graphics& g)
{
    if (! foot.isPressed()) return;
    // bouton assombri tant qu'on appuie (comportement Echoflex)
    const auto c = layout::footPos;
    const float r = layout::footR * 1.02f;
    ColourGradient shade (Colours::black.withAlpha (0.40f), c.x, c.y, Colours::black.withAlpha (0.0f), c.x + r, c.y, true);
    shade.addColour (0.88, Colours::black.withAlpha (0.36f));
    g.setGradientFill (shade);
    g.fillEllipse (c.x - r, c.y - r, r * 2.0f, r * 2.0f);
}

// forme de la modulation de hauteur (memes formes que le moteur : vers le haut = hauteur qui monte)
static float scopeShape (int mode, double p)
{
    const double f = p - std::floor (p);
    switch (mode)
    {
        case pipeline::Triangle: return (float) (1.0 - 4.0 * std::abs (f - 0.5));
        case pipeline::Ramp:
        {
            const double a = 0.025, sus = -0.38;
            if (f < a) return (float) std::sin (0.5 * MathConstants<double>::pi * f / a);
            if (f < 0.80) return (float) (sus + (1.0 - sus) * std::exp (-(f - a) / 0.075));
            const double r = (f - 0.80) / 0.20, end = sus + (1.0 - sus) * std::exp (-(0.80 - a) / 0.075);
            return (float) (end * (1.0 - r * r * (3.0 - 2.0 * r)));
        }
        case pipeline::Square: return (float) (std::tanh (14.0 * std::sin (MathConstants<double>::twoPi * f)) / std::tanh (14.0));
        default: return (float) std::cos (MathConstants<double>::twoPi * f);
    }
}

// bruit lisse deterministe (mode Random) : valeurs aleatoires a chaque demi-cycle, raccord en S
static float scopeNoise (double p)
{
    auto h = [] (int64 i) { uint32 x = (uint32) (i * 2654435761u) ^ 0x9E3779B9u; x ^= x >> 15; x *= 0x2C1B3C6Du; x ^= x >> 12; return (float) (x & 0xFFFF) / 32767.5f - 1.0f; };
    const double q = p * 2.0;
    const int64 i = (int64) std::floor (q);
    const float t = (float) (q - (double) i), s = t * t * (3.0f - 2.0f * t);
    return h (i) + (h (i + 1) - h (i)) * s;
}

void PipelineAudioProcessorEditor::drawScope (Graphics& g, Rectangle<float> r)
{
    const bool on = proc.raw ("active") > 0.5f;
    const int mode = jlimit (0, 7, roundToInt (proc.raw ("mode")));
    const float depth = proc.raw ("depth") / 10.0f, rate = proc.raw ("rate") / 10.0f;
    const float mid = r.getCentreY(), half = r.getHeight() * 0.5f;

    // graticule discrete (axe central + reperes), comme un petit ecran d'oscilloscope
    g.setColour (lcd.withAlpha (0.10f));
    g.drawHorizontalLine (roundToInt (mid), r.getX(), r.getRight());
    for (int k = 1; k < 4; ++k)
    {
        const float x = r.getX() + r.getWidth() * (float) k / 4.0f;
        for (float y = r.getY(); y < r.getBottom(); y += 4.0f) g.fillRect (x, y, 0.8f, 1.6f);
    }

    const int N = 140;
    float hz = proc.raw ("sync") > 0.5f && proc.shownHz.load() > 0.0f ? proc.shownHz.load() : pipeline::rateToHz (rate);
    float window = jlimit (0.25f, 2.0f, 6.0f / jmax (0.05f, hz));     // au plus ~6 cycles visibles, au moins 0,25 s
    float amp = on ? (0.10f + 0.85f * std::pow (depth, 0.8f)) : 0.0f;

    auto histAt = [this] (const float* h, float u)                      // u = 0 (ancien) .. 1 (recent)
    {
        const float pos = u * (float) (histN - 1);
        const int i0 = (int) pos; const float t = pos - (float) i0;
        const float a0 = h[(histPos + i0) % histN], a1 = h[(histPos + jmin (histN - 1, i0 + 1)) % histN];
        return a0 + (a1 - a0) * t;
    };

    Path p;
    double envPhase = 0.0;
    for (int i = 0; i < N; ++i)
    {
        const float u = (float) i / (float) (N - 1);                      // gauche = passe, droite = maintenant
        float v = 0.0f;
        if (on)
        {
            const double ph = scopePhase - (double) ((1.0f - u) * window * hz);
            switch (mode)
            {
                case pipeline::Random:
                {
                    const float chaos = jlimit (0.0f, 1.0f, (depth - 0.12f) / 0.70f);
                    v = (1.0f - chaos) * std::cos ((float) (MathConstants<double>::twoPi * ph)) + chaos * scopeNoise (ph * (1.0 + 0.6 * chaos));
                    break;
                }
                case pipeline::EnvD:
                    // l'attaque ouvre la profondeur (DEPTH = sensibilite) : le sinus gonfle a chaque note
                    v = scopeShape (pipeline::Sine, ph) * jlimit (0.0f, 1.0f, histAt (envHist, u) * 1.4f) / jmax (0.1f, amp) * 0.9f;
                    break;
                case pipeline::EnvR:
                {
                    // l'attaque accelere le LFO : la frequence affichee suit l'enveloppe
                    const float e = histAt (envHist, u);
                    const float fh = 0.35f * std::pow (13.0f / 0.35f, e);
                    envPhase += (double) (fh * window / (float) (N - 1));
                    v = std::cos ((float) (MathConstants<double>::twoPi * envPhase));
                    break;
                }
                case pipeline::EnvP:
                    // plongee de hauteur a chaque attaque (historique reel), vers le bas
                    v = jlimit (-1.0f, 1.0f, histAt (centsHist, u) / 250.0f) / jmax (0.1f, amp) * 0.9f;
                    break;
                default:
                    v = scopeShape (mode, ph);
                    break;
            }
        }
        const float x = r.getX() + u * r.getWidth();
        const float y = mid - jlimit (-1.0f, 1.0f, v * amp) * half;
        if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y);
    }
    // trace lumineux : halo large et doux, puis trait fin plus clair (comme l'ecriture de l'ecran)
    g.setColour (lcd.withAlpha (on ? 0.10f : 0.05f));
    g.strokePath (p, PathStrokeType (5.0f, PathStrokeType::curved, PathStrokeType::rounded));
    g.setColour (lcd.withAlpha (on ? 0.22f : 0.08f));
    g.strokePath (p, PathStrokeType (2.8f, PathStrokeType::curved, PathStrokeType::rounded));
    g.setColour ((on ? lcd.brighter (0.25f) : lcd).withAlpha (on ? 0.95f : 0.30f));
    g.strokePath (p, PathStrokeType (1.4f, PathStrokeType::curved, PathStrokeType::rounded));
}

// police de la barre de presets : la plus grande (28 au maximum) qui fait tenir le plus long nom d'usine
Font PipelineAudioProcessorEditor::presetFont (float availW)
{
    if (presetFontAvail != availW)
    {
        presetFontAvail = availW;
        float h = 26.5f;
        for (; h > 14.0f; h -= 0.5f)
        {
            const Font f = Font (FontOptions (labelFace).withHeight (h)).withExtraKerningFactor (0.03f);
            float widest = 0.0f;
            for (int i = 0; i < PipelineAudioProcessor::getNumFactoryPresets(); ++i)
                widest = jmax (widest, GlyphArrangement::getStringWidth (f, "P" + String (i + 1) + "  " + PipelineAudioProcessor::getFactoryPreset (i).name));
            if (widest <= availW) break;
        }
        presetFontH = h;
    }
    return Font (FontOptions (labelFace).withHeight (presetFontH)).withExtraKerningFactor (0.03f);
}

void PipelineAudioProcessorEditor::drawDisplay (Graphics& g)
{
    // ligne du haut : reglage qui vient de bouger (fondu), sinon ce que fait le vibrato ; couleur bleu glace
    const float a = statusAlpha;
    const auto sr = textRect.toNearestInt();
    auto glowText = [&] (const String& t, Font f, float alpha)
    {
        g.setFont (f);
        g.setColour (lcd.withAlpha (0.15f * alpha));
        for (auto d : { Point<int> (-1, 0), Point<int> (1, 0), Point<int> (0, -1), Point<int> (0, 1) })
            g.drawFittedText (t, sr.translated (d.x, d.y), Justification::centredLeft, 1, 0.62f);
        g.setColour (lcd.withAlpha (alpha));
        g.drawFittedText (t, sr, Justification::centredLeft, 1, 0.62f);
    };
    const Font big (FontOptions (boldFace).withHeight (23.5f));
    drawScope (g, scopeRect);
    if (a < 0.999f) glowText (lastInfo, big.withExtraKerningFactor (0.05f), 0.92f * (1.0f - a));
    if (a > 0.0f)   glowText (lastLine1, big.withExtraKerningFactor (0.05f), a);

    // barre de presets (son cadre fait partie du fond) : fleches et nom
    const auto r = presetRect;
    if (hoverZone != 0)
    {
        g.setColour (Colours::white.withAlpha (0.05f));
        g.fillRoundedRectangle (r.reduced (1.5f), 4.0f);
    }
    const float aw = 28.0f;
    auto arrow = [&] (Rectangle<float> ar, bool left, bool hot)
    {
        Path p;
        const auto c = ar.getCentre();
        const float s = 4.3f;
        if (left) p.addTriangle (c.x + s * 0.6f, c.y - s, c.x + s * 0.6f, c.y + s, c.x - s * 0.8f, c.y);
        else      p.addTriangle (c.x - s * 0.6f, c.y - s, c.x - s * 0.6f, c.y + s, c.x + s * 0.8f, c.y);
        g.setColour (inkWhite.withAlpha (hot ? 1.0f : 0.72f));
        g.fillPath (p);
    };
    arrow (r.withWidth (aw), true, hoverZone == 1);
    arrow (r.withTrimmedLeft (r.getWidth() - aw), false, hoverZone == 3);
    // nom du preset en grand : taille commune choisie pour que le nom le plus long tienne entier (jamais tasse ni coupe)
    const auto nameArea = r.reduced (aw - 4.0f, 0.0f);
    g.setFont (presetFont (nameArea.getWidth() - 6.0f));
    g.setColour ((midiFlash > 0 ? lcd : inkWhite).withAlpha (hoverZone == 2 ? 1.0f : 0.92f));
    g.drawText (lastPreset, nameArea, Justification::centred, false);
}

void PipelineAudioProcessorEditor::paint (Graphics& g)
{
    lastPaintMs = Time::getMillisecondCounterHiRes();
    repaintAskedMs = 0.0;
    g.fillAll (Colour (0xff111112));          // autour des jacks : le fond de l'image est transparent
    // anti-gel : aucun rescale ici, on dessine le cache existant (ou l'original en attendant le timer)
    const Image& bg = bgScaled.isValid() ? bgScaled : background;
    g.setImageResamplingQuality (&bg == &background ? Graphics::highResamplingQuality : Graphics::lowResamplingQuality);
    if (bg.isValid()) g.drawImage (bg, getLocalBounds().toFloat());
    if (! bgScaled.isValid() && controls.isValid()) g.drawImage (controls, getLocalBounds().toFloat());

    const float s = (float) getHeight() / baseH;
    g.addTransform (AffineTransform::scale (s));
    drawLed (g);
    drawModeLabels (g);
    drawKnobs (g);
    drawFootswitch (g);
    drawDisplay (g);
}

//==============================================================================
// souris : barre de presets (fleches = precedent / suivant, nom = menu), etiquettes du selecteur, clic droit = menu
//==============================================================================
static int presetZoneAt (Point<float> p)
{
    if (! presetRect.contains (p)) return 0;
    if (p.x < presetRect.getX() + 28.0f) return 1;
    if (p.x > presetRect.getRight() - 28.0f) return 3;
    return 2;
}

int PipelineAudioProcessorEditor::modeLabelAt (Point<float> u) const
{
    for (int i = 0; i < 8; ++i)
        if (labelBox[i].expanded (6.0f, 5.0f).contains (u)) return i;
    return -1;
}

void PipelineAudioProcessorEditor::mouseMove (const MouseEvent& e)
{
    const float s = (float) getHeight() / baseH;
    const auto u = e.position / s;
    hoverZone = presetZoneAt (u);
    setMouseCursor (hoverZone != 0 || modeLabelAt (u) >= 0 ? MouseCursor::PointingHandCursor : MouseCursor::NormalCursor);
}

void PipelineAudioProcessorEditor::mouseExit (const MouseEvent&) { hoverZone = 0; }

void PipelineAudioProcessorEditor::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { showContextMenu(); return; }
    const float s = (float) getHeight() / baseH;
    const auto u = e.position / s;
    const int lbl = modeLabelAt (u);
    if (lbl >= 0) { modeKnob.moveTo (lbl); return; }
    switch (presetZoneAt (u))
    {
        case 1: stepPreset (-1); break;
        case 2: showPresetMenu(); break;
        case 3: stepPreset (1); break;
        default: break;
    }
}

void PipelineAudioProcessorEditor::stepPreset (int delta)
{
    const int n = PipelineAudioProcessor::getNumFactoryPresets();
    int cp = proc.currentPreset.load();
    if (cp < 0 || cp >= n) cp = delta > 0 ? -1 : 0;
    proc.applyFactoryPreset ((cp + delta + n) % n);
}

void PipelineAudioProcessorEditor::showPresetMenu()
{
    PopupMenu m;
    m.addSectionHeader ("Factory presets");
    for (int i = 0; i < PipelineAudioProcessor::getNumFactoryPresets(); ++i)
        m.addItem (100 + i, String (i + 1) + ". " + PipelineAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    m.addSeparator();
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    m.addSubMenu ("Load user preset", load);
    m.addSubMenu ("Save user preset", save);
    m.setLookAndFeel (&lnf);
    m.showMenuAsync (PopupMenu::Options().withTargetScreenArea (localAreaToGlobal (scaled (presetRect))),
        [safe = Component::SafePointer<PipelineAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& pr = safe->proc;
            if      (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
        });
}

void PipelineAudioProcessorEditor::addMidiMenu (PopupMenu& menu, int learnIdx)
{
    if (learnIdx < 0 || learnIdx >= PipelineAudioProcessor::numLearn)
        return;
    const int cc = proc.ccMap[learnIdx].load();
    const int lt = proc.learnTarget.load();
    const String name = PipelineAudioProcessor::learnDef (learnIdx).name;
    menu.addItem (1000 + learnIdx, "MIDI Learn: " + name + " (" + (cc >= 0 ? "CC " + String (cc) : String ("none")) + ")", true, lt == learnIdx);
    menu.addItem (1100 + learnIdx, "Clear MIDI: " + name, cc >= 0);
    if (lt >= 0) menu.addItem (1200, "Cancel MIDI learn");
    menu.addSeparator();
}

void PipelineAudioProcessorEditor::handleMidiMenu (int r)
{
    if (r >= 1000 && r < 1000 + PipelineAudioProcessor::numLearn)
        proc.learnTarget.store (proc.learnTarget.load() == r - 1000 ? -1 : r - 1000);   // re-cliquer annule
    else if (r >= 1100 && r < 1100 + PipelineAudioProcessor::numLearn) proc.ccMap[r - 1100].store (-1);
    else if (r == 1200) proc.learnTarget.store (-1);
    else if (r == 1201) { proc.learnTarget.store (-1); proc.resetMidiMap(); }
}

void PipelineAudioProcessorEditor::showContextMenu (int learnIdx)
{
    PopupMenu menu, sizes;
    addMidiMenu (menu, learnIdx);
    {
        const char* names[numSizes] = { "60 %", "75 %", "100 %" };
        const int def = WigaWindowSize::defaultIndex (JucePlugin_Name, numSizes);
        PopupMenu defSizes;
        for (int i = 0; i < numSizes; ++i)
        {
            sizes.addItem (1 + i, String (names[i]) + (i == def ? "  (default)" : ""), true, std::abs (getHeight() - sizeHeight (i)) <= 2);
            defSizes.addItem (60 + i, names[i], true, def == i);
        }
        sizes.addSeparator();
        sizes.addSubMenu ("Default size (new windows)", defSizes);
    }
    menu.addSubMenu ("Plugin size", sizes);
    menu.addSeparator();

    PopupMenu factory;
    for (int i = 0; i < PipelineAudioProcessor::getNumFactoryPresets(); ++i)
        factory.addItem (100 + i, String (i + 1) + ". " + PipelineAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    menu.addSubMenu ("Factory presets", factory);
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    menu.addSubMenu ("Load user preset", load);
    menu.addSubMenu ("Save user preset", save);
    menu.addSeparator();

    menu.addItem (40, "Tempo sync (RATE = note value)", true, proc.raw ("sync") > 0.5f);

    PopupMenu settings;
    settings.addItem (44, "Flexi-Switch: hold = momentary", true, proc.raw ("flexi") > 0.5f);
    settings.addSeparator();
    settings.addItem (41, "MIDI footswitch: each press toggles on / off (default)", true, proc.raw ("midiFsMode") < 0.5f);
    settings.addItem (42, "MIDI footswitch latching (127 = on / 0 = off)", true, proc.raw ("midiFsMode") > 0.5f);
    menu.addSubMenu ("Settings", settings);

    PopupMenu midi;
    for (int i = 0; i < PipelineAudioProcessor::numLearn; ++i)
    {
        const int cc = proc.ccMap[i].load();
        midi.addItem (1000 + i, "Learn: " + String (PipelineAudioProcessor::learnDef (i).name)
                                 + " (" + (cc >= 0 ? "CC " + String (cc) : String ("none")) + ")",
                      true, proc.learnTarget.load() == i);
    }
    midi.addSeparator();
    if (proc.learnTarget.load() >= 0) midi.addItem (1200, "Cancel MIDI learn");
    midi.addItem (1201, "Clear all MIDI assignments");
    midi.addSeparator();
    midi.addItem (902, "Mode: 8 zones / Tempo sync: 64+ on", false);
    midi.addItem (906, "CC n+32 = fine (14-bit) for knobs on CC 0-31", false);
    midi.addItem (907, "Program Change 1-" + String (PipelineAudioProcessor::getNumFactoryPresets()) + "  Factory presets", false);
    menu.addSubMenu ("MIDI map", midi);
    menu.addSeparator();
    menu.addItem (999, "Pipeline vibrato v" + String (JucePlugin_VersionString) + " - NINE HANDS | DSP", false);

    menu.setLookAndFeel (&lnf);
    menu.showMenuAsync (PopupMenu::Options().withMousePosition(),    // menu clic droit : toujours la ou l'on clique
        [safe = Component::SafePointer<PipelineAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& ed = *safe;
            auto& pr = ed.proc;
            if      (r >= 1 && r <= numSizes) ed.setScaledHeight (sizeHeight (r - 1));
            else if (r >= 60 && r < 60 + numSizes)
            {
                WigaWindowSize::setDefaultIndex (JucePlugin_Name, r - 60);   // toutes les nouvelles fenetres de ce plugin
                ed.setScaledHeight (sizeHeight (r - 60));                    // et cette fenetre tout de suite
            }
            else if (r == 40) { pr.setParamValue ("sync", pr.raw ("sync") > 0.5f ? 0.0f : 1.0f); }
            else if (r == 41) pr.setParamValue ("midiFsMode", 0.0f);
            else if (r == 42) pr.setParamValue ("midiFsMode", 1.0f);
            else if (r == 44) pr.setParamValue ("flexi", pr.raw ("flexi") > 0.5f ? 0.0f : 1.0f);
            else if (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
            else if (r >= 1000) ed.handleMidiMenu (r);
        });
}
