// genere par tools/make_art.py - ne pas modifier a la main (repere 617.5 x 900.0 = fond 1235 x 1800 px / 2)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    constexpr float frameW = 617.50f, frameH = 900.00f;   // pedale plein cadre (jacks aux bords gauche / droit)
    const juce::Point<float> ratePos { 160.70f, 182.49f }, depthPos { 456.80f, 182.49f }, modePos { 308.75f, 369.29f };
    const float knobR = 60.67f, modeR = 51.07f;   // rayon exterieur du moletage
    const float knobSpriteHalf = 106.18f, modeSpriteHalf = 89.37f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    // repere du potard (photo) : rayons x rayon exterieur
    const float idxR0 = 0.0303f, idxR1 = 0.6152f, idxHalfW = 0.0197f, dotR = 0.8424f, dotSize = 0.0424f;
    const juce::Point<float> ledPos { 308.75f, 56.60f }; const float ledS = 49.96f;
    const juce::Rectangle<float> glowRect { 227.85f, -24.27f, 161.80f, 161.80f };
    const juce::Point<float> footPos { 308.75f, 787.42f }; const float footR = 38.31f, fsS = 192.13f, footHit = 50.56f;
    const juce::Rectangle<float> screenRect { 79.51f, 609.89f, 459.10f, 108.19f }, rowRect { 88.61f, 616.97f, 440.90f, 47.53f }, barRect { 94.67f, 668.55f, 428.76f, 34.38f };
    const juce::Rectangle<float> boxRect { 21.87f, 0.00f, 573.76f, 900.00f };   // boitier
    const juce::Rectangle<float> faceRect { 37.04f, 15.17f, 543.43f, 869.66f }; const float faceR = 19.21f, faceLineW = 1.72f;   // cadre interieur
    const float jackY = 526.60f;
    // serigraphie vectorielle : texte, police (0 medium, 1 bold, 2 light), taille em, espacement, centre, rotation (degres)
    struct Txt { const char* s; int font; float em, track, x, y, rot; };
    const Txt texts[] = {
        { "RATE", 0, 19.21f, 3.44f, 160.70f, 90.47f, 0.00f },
        { "DEPTH", 0, 19.21f, 3.44f, 456.80f, 90.47f, 0.00f },
        { "MODE", 0, 16.18f, 3.24f, 308.75f, 255.29f, 0.00f },
        { "SINE", 0, 13.65f, 1.01f, 258.47f, 441.92f, 0.00f },
        { "TRI", 0, 13.65f, 1.01f, 205.90f, 396.02f, 0.00f },
        { "RAMP", 0, 13.65f, 1.01f, 212.76f, 329.44f, 0.00f },
        { "SQR", 0, 13.65f, 1.01f, 272.18f, 290.10f, 0.00f },
        { "RAND", 0, 13.65f, 1.01f, 344.75f, 290.10f, 0.00f },
        { "ENV D", 0, 13.65f, 1.01f, 405.88f, 329.44f, 0.00f },
        { "ENV R", 0, 13.65f, 1.01f, 411.60f, 396.02f, 0.00f },
        { "ENV P", 0, 13.65f, 1.01f, 358.46f, 441.92f, 0.00f },
        { "PIPELINE", 1, 66.74f, 4.04f, 308.75f, 526.60f, 0.00f },
        { "PITCH VIBRATO", 2, 18.20f, 7.58f, 308.75f, 578.30f, 0.00f },
        { "OUT", 0, 13.15f, 1.62f, 50.18f, 526.60f, 90.00f },
        { "IN", 0, 13.15f, 1.62f, 567.32f, 526.60f, 90.00f }
    };
    constexpr int modeLabelFirst = 3;   // texts[modeLabelFirst + i] = etiquette du mode i
    struct Tick { float x0, y0, x1, y1, w; };
    const Tick ticks[] = { { 125.81f, 242.92f, 121.77f, 249.92f, 1.92f }, { 100.27f, 217.38f, 95.02f, 220.41f, 1.92f }, { 90.92f, 182.49f, 84.86f, 182.49f, 1.92f }, { 100.27f, 147.60f, 95.02f, 144.57f, 1.92f }, { 125.81f, 122.06f, 122.78f, 116.81f, 1.92f }, { 160.70f, 112.71f, 160.70f, 104.62f, 1.92f }, { 195.59f, 122.06f, 198.62f, 116.81f, 1.92f }, { 221.13f, 147.60f, 226.38f, 144.57f, 1.92f }, { 230.47f, 182.49f, 236.54f, 182.49f, 1.92f }, { 221.13f, 217.38f, 226.38f, 220.41f, 1.92f }, { 195.59f, 242.92f, 199.63f, 249.92f, 1.92f }, { 421.91f, 242.92f, 417.87f, 249.92f, 1.92f }, { 396.37f, 217.38f, 391.12f, 220.41f, 1.92f }, { 387.03f, 182.49f, 380.96f, 182.49f, 1.92f }, { 396.37f, 147.60f, 391.12f, 144.57f, 1.92f }, { 421.91f, 122.06f, 418.88f, 116.81f, 1.92f }, { 456.80f, 112.71f, 456.80f, 104.62f, 1.92f }, { 491.69f, 122.06f, 494.72f, 116.81f, 1.92f }, { 517.23f, 147.60f, 522.48f, 144.57f, 1.92f }, { 526.58f, 182.49f, 532.64f, 182.49f, 1.92f }, { 517.23f, 217.38f, 522.48f, 220.41f, 1.92f }, { 491.69f, 242.92f, 495.73f, 249.92f, 1.92f }, { 280.18f, 418.77f, 276.64f, 424.90f, 1.92f }, { 254.15f, 386.13f, 247.39f, 388.21f, 1.92f }, { 257.27f, 344.50f, 250.90f, 341.43f, 1.92f }, { 287.88f, 316.10f, 285.29f, 309.51f, 1.92f }, { 329.62f, 316.10f, 332.21f, 309.51f, 1.92f }, { 360.23f, 344.50f, 366.60f, 341.43f, 1.92f }, { 363.35f, 386.13f, 370.11f, 388.21f, 1.92f }, { 337.32f, 418.77f, 340.86f, 424.90f, 1.92f } };
    struct Wavy { float x0, x1, y, amp, periods, w; };
    const Wavy wavy[] = { { 152.09f, 184.75f, 578.30f, 2.43f, 2.50f, 1.62f }, { 432.75f, 465.41f, 578.30f, 2.43f, 2.50f, 1.62f } };
    const juce::Point<float> logoPos { 308.75f, 865.62f }; const float logoW = 169.89f;
    // vagues (PipelineWaves.svg) : x' = waveA * x + waveB, y' = waveC * y + waveD (unites du plugin)
    const float waveA = 0.668422f, waveB = -104.0005f, waveC = 0.628317f, waveD = -141.0534f;
}
