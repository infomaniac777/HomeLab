#include <Arduino.h>

const int LED_BUILTIN = 2;  // Built-in LED on ESP32 is on GPIO2
String command;
bool isBlinking = true;
const int delay_interval = 500e3;

void setup() {
    Serial.begin(9600);
    pinMode(LED_BUILTIN, OUTPUT);
    Serial.println("Enter commands: 'ON' to turn LED on, 'OFF' to turn LED off, 'BLINK' to start/stop rapid blinking");
}

void loop() {
    /*
    if (Serial.available()) {
        command = Serial.readStringUntil('\n');
        
        if (command == "ON") {
            digitalWrite(LED_BUILTIN, HIGH);
            Serial.println("LED turned ON");
        }
        else if (command == "OFF") {
            digitalWrite(LED_BUILTIN, LOW);
            Serial.println("LED turned OFF");
        }
        else if (command == "BLINK") {
            isBlinking = !isBlinking;
            if (isBlinking) {
                Serial.println("Rapid blinking started");
            } else {
                Serial.println("Rapid blinking stopped");
                digitalWrite(LED_BUILTIN, LOW);
            }
        }
    } 
    */

    if (isBlinking) {
        float temp_celsius = temperatureRead();
        Serial.print("ESP32 Temperature: ");
        Serial.print(temp_celsius);
        Serial.println("°C");
        digitalWrite(LED_BUILTIN, HIGH);
        delayMicroseconds(100e3); 
        digitalWrite(LED_BUILTIN, LOW);
        delayMicroseconds(2e6);
    }
}
