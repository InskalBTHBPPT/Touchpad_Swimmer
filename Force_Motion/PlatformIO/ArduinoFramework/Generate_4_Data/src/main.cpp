/*********
  Generator time-series sinusoidal untuk uji Swimmer Force Motion Monitoring.
  Format serial: waktu_s, force_kg, roll_deg, pitch_deg, battery_pct
*********/

#include <Arduino.h>
#include <cmath>

#ifndef PI_F
#define PI_F 3.14159265358979323846f
#endif

unsigned long lastTime = 0;
unsigned long timerInterval = 50; // ms antar baris

static float phase1 = 0.0f;
static float phase2 = 0.0f;
static float phase3 = 0.0f;

static const float battery_pct = 87.3f;

void setup() {
  Serial.begin(115200);
}

void loop() {
  if ((millis() - lastTime) >= timerInterval) {
    lastTime = millis();

    const float dt = timerInterval / 1000.0f;
    const float tSec = lastTime / 1000.0f;
    const float w = 2.0f * PI_F * tSec;

    // Force (Kg): offset 35, amplitudo puncak ≤35 → rentang 0.00 … 70.00
    float amp1 = 17.5f + 17.5f * sinf(0.08f * w + 0.3f);           // ~0.0 … 35.0
    float f1 = 0.18f + 0.32f * (0.5f + 0.5f * sinf(0.05f * w));    // Hz, positif
    phase1 += 2.0f * PI_F * f1 * dt;
    float force_kg = 35.0f + amp1 * sinf(phase1);

    // Roll (deg): pusat 0, amplitudo puncak ≤60 → -60.00 … 60.00
    float amp2 = 30.0f + 30.0f * sinf(0.06f * w + 1.1f);           // 0 … 60
    float f2 = 0.12f + 0.28f * (0.5f + 0.5f * sinf(0.04f * w + 2.f));
    phase2 += 2.0f * PI_F * f2 * dt;
    float roll_deg = amp2 * sinf(phase2);

    // Pitch (deg): pusat 0, amplitudo puncak ≤60 → -60.00 … 60.00
    float amp3 = 30.0f + 30.0f * sinf(0.07f * w + 2.4f);          // 0 … 60
    float f3 = 0.10f + 0.35f * (0.5f + 0.5f * sinf(0.045f * w + 0.7f));
    phase3 += 2.0f * PI_F * f3 * dt;
    float pitch_deg = amp3 * sinf(phase3);

    Serial.printf("%.2f,%.2f,%.2f,%.2f,%.1f\n", tSec, force_kg, roll_deg, pitch_deg, battery_pct);
  }
}
