/*********
  Rui Santos & Sara Santos - Random Nerd Tutorials
  Complete project details at https://RandomNerdTutorials.com/getting-started-esp32-c3-super-mini/
*********/

#include <Arduino.h>
#include <cmath>

#ifndef PI_F
#define PI_F 3.14159265358979323846f
#endif

unsigned long lastTime = 0;
unsigned long timerInterval = 100; // ms antar baris

static float phase1 = 0.0f;
static float phase2 = 0.0f;
static float phase3 = 0.0f;

void setup() {
  Serial.begin(115200);
}

void loop() {
  if ((millis() - lastTime) >= timerInterval) {
    lastTime = millis();

    const float dt = timerInterval / 1000.0f;
    const float tSec = lastTime / 1000.0f;
    const float w = 2.0f * PI_F * tSec;

    // Channel 1: offset 25, amplitudo puncak ≤25 → rentang 0.00 … 50.00
    float amp1 = 12.5f + 12.0f * sinf(0.08f * w + 0.3f);           // ~0.5 … 24.5
    float f1 = 0.18f + 0.32f * (0.5f + 0.5f * sinf(0.05f * w));    // Hz, positif
    phase1 += 2.0f * PI_F * f1 * dt;
    float ch1 = 25.0f + amp1 * sinf(phase1);

    // Channel 2: pusat 0, amplitudo puncak ≤20 → -20.00 … 20.00
    float amp2 = 10.0f + 10.0f * sinf(0.06f * w + 1.1f);           // 0 … 20
    float f2 = 0.12f + 0.28f * (0.5f + 0.5f * sinf(0.04f * w + 2.f));
    phase2 += 2.0f * PI_F * f2 * dt;
    float ch2 = amp2 * sinf(phase2);

    // Channel 3: pusat 0, amplitudo puncak ≤40 → -40.00 … 40.00
    float amp3 = 20.0f + 20.0f * sinf(0.07f * w + 2.4f);          // 0 … 40
    float f3 = 0.10f + 0.35f * (0.5f + 0.5f * sinf(0.045f * w + 0.7f));
    phase3 += 2.0f * PI_F * f3 * dt;
    float ch3 = amp3 * sinf(phase3);

    Serial.printf("%.2f,%.2f,%.2f,%.2f\n", tSec, ch1, ch2, ch3);
  }
}
