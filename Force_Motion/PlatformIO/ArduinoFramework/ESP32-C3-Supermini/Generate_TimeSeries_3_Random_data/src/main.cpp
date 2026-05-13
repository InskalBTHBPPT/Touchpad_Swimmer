/*********
  Rui Santos & Sara Santos - Random Nerd Tutorials
  Complete project details at https://RandomNerdTutorials.com/getting-started-esp32-c3-super-mini/
*********/

#include <Arduino.h>

unsigned long lastTime = 0;
unsigned long timerInterval = 100; // ms antar baris

void setup() {
  Serial.begin(115200);
  randomSeed(esp_random());
}

void loop() {
  if ((millis() - lastTime) >= timerInterval) {
    lastTime = millis();

    // Dua desimal: bangkitkan dalam "sen" lalu bagi 100
    float randomData1 = random(0, 5001) / 100.0f;       // 0.00 … 50.00
    float randomData2 = random(-2000, 2001) / 100.0f;  // -20.00 … 20.00
    float randomData3 = random(-4000, 4001) / 100.0f;  // -40.00 … 40.00

    float tSec = lastTime / 1000.0f;
    Serial.printf("%.2f,%.2f,%.2f,%.2f\n", tSec, randomData1, randomData2, randomData3);
  }
}
