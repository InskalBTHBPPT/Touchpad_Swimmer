/*********
  Rui Santos & Sara Santos - Random Nerd Tutorials
  Complete project details at https://RandomNerdTutorials.com/getting-started-esp32-c3-super-mini/
*********/

#include <Arduino.h>

unsigned long lastTime = 0;
unsigned long timerDelay = 20;

void setup() {
  Serial.begin(115200);
  // pinMode(ledPin, OUTPUT);
}

void loop()
{
    if ((millis() - lastTime) >= timerDelay) {
        lastTime = millis();
        Serial.println(millis());
    }
}