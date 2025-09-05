/////////////////////////////////////////////////////////////////
/*
  Broadcasting Your Voice with ESP32-S3 & INMP441
  For More Information: https://youtu.be/qq2FRv0lCPw
  Created by Eric N. (ThatProject)
*/
/////////////////////////////////////////////////////////////////

/*
- Device
ESP32-S3 DevKit-C
https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html

- Required Library
Arduino ESP32: 2.0.9

Arduino Websockets: 0.5.3
https://github.com/gilmaimon/ArduinoWebsockets
*/

#include <driver/i2s.h>
#include <WiFi.h>
#include <ArduinoWebsockets.h>

#define I2S_SD 21
#define I2S_WS 22
#define I2S_SCK 19
#define I2S_PORT I2S_NUM_0

// Reduce buffer count and length for lower latency
#define bufferCnt 5      // Reduced from 10
#define bufferLen 512    // Reduced from 1024
int16_t sBuffer[bufferLen];

const int LED_BUILTIN = 2;  // Built-in LED on ESP32 is on GPIO2
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const char* websocket_server_host = "192.168.0.7";
const uint16_t websocket_server_port = 3003;  // <WEBSOCKET_SERVER_PORT>

using namespace websockets;
WebsocketsClient client;
bool led_on = false;
bool led_to_blink = false;

void onEventsCallback(WebsocketsEvent event, String data) {
  if (event == WebsocketsEvent::ConnectionOpened) {
    Serial.println("Connection Opened");
  } else if (event == WebsocketsEvent::ConnectionClosed) {
    Serial.println("Connection Closed");
  } else if (event == WebsocketsEvent::GotPing) {
    Serial.println("Got a Ping!");
    client.pong();  // Must respond to keep connection alive
  } else if (event == WebsocketsEvent::GotPong) {
    Serial.println("Got a Pong!");
  }
}

void i2s_install() {
  // Set up I2S Processor configuration
  const i2s_config_t i2s_config = {
    .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
    //.sample_rate = 44100,
    .sample_rate = 16000,
    .bits_per_sample = i2s_bits_per_sample_t(16),
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1, // Higher priority
    .dma_buf_count = bufferCnt,
    .dma_buf_len = bufferLen,
    .use_apll = false
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
}

void i2s_setpin() {
  // Set I2S pin configuration
  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = -1,
    .data_in_num = I2S_SD
  };

  i2s_set_pin(I2S_PORT, &pin_config);
}

void loop() {
    // Handle WebSocket events
    client.poll();
    delay(10);
}

void connectWiFi() {
  Serial.println("Connecting to WiFi: ");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
}

void connectWSServer() {
  Serial.println("Connecting to Websocket Server: ");
  while (!client.connect(websocket_server_host, websocket_server_port, "/")) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Websocket Connected!");
}


void micTask(void* parameter) {
    i2s_install();
    i2s_setpin();
    i2s_start(I2S_PORT);

    unsigned long lastPing = 0;
    unsigned long lastBlinkStart = 0;
    const unsigned long PING_INTERVAL = 20000; // 20s ping interval
    const unsigned int BLINK_DURATION = 100;   // LED on duration in ms
    const unsigned int BLINK_GAP = 3000; // Minimum gap between blinks in ms
    size_t bytesIn = 0;

    while (1) {
        if (WiFi.status() != WL_CONNECTED) {
            connectWiFi();
        }
        if (!client.available()) {
            connectWSServer();
        }

        // Send ping every 20s
        if (millis() - lastPing > PING_INTERVAL) {
            client.ping();
            lastPing = millis();
        }

        esp_err_t result = i2s_read(I2S_PORT, &sBuffer, bufferLen, &bytesIn, portMAX_DELAY);
        if (result == ESP_OK) {
            led_to_blink = client.sendBinary((const char*)sBuffer, bytesIn);
        }
        else {
          led_to_blink = false;
        }
  
        // LED blink logic
        if(led_on) {
            if (millis() - lastBlinkStart > BLINK_DURATION) {
              digitalWrite(LED_BUILTIN, LOW); // Turn off LED
              led_on = false;
            }
        }
        else {
          if (led_to_blink && (millis() - lastBlinkStart > BLINK_GAP)) {
              digitalWrite(LED_BUILTIN, HIGH); // Turn on LED
              lastBlinkStart = millis();
              led_on = true;
              led_to_blink = false;
          }
        }
    }
}

void setup() {
  Serial.begin(9600);

  pinMode(LED_BUILTIN, OUTPUT);
  connectWiFi();
  client.onEvent(onEventsCallback);
  connectWSServer();
  xTaskCreatePinnedToCore(micTask, "micTask", 10000, NULL, 1, NULL, 1);
}