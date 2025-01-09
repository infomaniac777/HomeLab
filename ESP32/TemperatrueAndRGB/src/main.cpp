#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <WebSocketsClient.h>

const int LED_BUILTIN = 2;  // Built-in LED on ESP32 is on GPIO2
const int tempPin = 15;     // DS18B20 data pin

// WiFi settings
const char* ssid = getenv("WIFI_SSID");
const char* password = getenv("WIFI_PASSWORD");

// WebSocket settings
const char* websocketServer = "192.168.0.7";  // Your server IP
const int websocketPort = 3100;
const char* websocketPath = "/esp32_temp";

WebSocketsClient webSocket;  // Change to WebSocketsClient
float lastTemperature = 0;
bool serverConnected = false;
unsigned long lastTemperatureReadTime = 0;

// Setup temperature sensor
OneWire oneWire(tempPin);
DallasTemperature sensors(&oneWire);

void multiBlinkLED(int blinks) {
    for(int i = 0; i < blinks; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
        if(i < blinks - 1) delay(200);
    }
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_CONNECTED:
            serverConnected = true;
            Serial.printf("Connected to WS server at %s:%d%s\n", websocketServer, websocketPort, websocketPath);
            break;
        case WStype_DISCONNECTED:
            serverConnected = false;
            Serial.println("Disconnected from server");
            multiBlinkLED(3);  // Disconnection indication
            break;
        case WStype_ERROR:
            serverConnected = false;
            Serial.println("Connection error");
            break;
    }
}

void setup() {
  Serial.begin(9600);
  sensors.begin();
  pinMode(LED_BUILTIN, OUTPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    multiBlinkLED(2);
    delay(500);
    Serial.println("Connecting to Wifi ...");
  }
  Serial.println("\nConnected to WiFi");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  webSocket.begin(websocketServer, websocketPort, websocketPath);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

void loop() {
    if(WiFi.status() == WL_CONNECTED) {
        webSocket.loop();
        
        if (serverConnected) {
            sensors.requestTemperatures();
            float tempC = sensors.getTempCByIndex(0);
            
            if (tempC != DEVICE_DISCONNECTED_C) {
                String json = "{\"temperature\":" + String(tempC, 2) + "}";
                webSocket.sendTXT(json);
                multiBlinkLED(1);  // Data sent indication
                delay(5000);
            }
            else {
              Serial.println("Error reading temperature");
            }
        }
    } else {
        multiBlinkLED(2);
        WiFi.begin(ssid, password);
        delay(5000);
    }
}