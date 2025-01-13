#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include <Arduino.h>
#include <algorithm>

// Network settings
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* udpAddress = "192.168.0.9";  // Server IP
const int udpPort = 3003;

// Pin Definitions
#define I2S_WS 22    // Word Select (WS) pin
#define I2S_SD 21    // Serial Data (SD) pin
#define I2S_SCK 19    // Serial Clock (SCK) pin
#define SAMPLE_RATE 44100  // CD quality
#define BUFFER_SIZE 736    // Matches MTU size for 16-bit samples
#define LED_PIN 2  // Built-in LED on ESP32

#define MAX_UDP_PACKET_SIZE 1472  // Standard MTU minus headers
#define UDP_SEND_DELAY 5          // ms between packets

WiFiUDP udp;

void setup() {
    Serial.begin(9600);  // Adjusted baud rate
    delay(1000);  // Give serial time to initialize
    Serial.println("I2S Microphone Test");
    
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected");
    
    const i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,  // Changed to 16-bit
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,   // Changed for grounded L/R pin
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,        // Increased for smoother streaming
        .dma_buf_len = BUFFER_SIZE,
        .use_apll = true,         // Enable APLL for better clock accuracy
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = -1,
        .data_in_num = I2S_SD
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("Failed to install I2S driver: %d\n", err);
        while(1);
    }
    
    err = i2s_set_pin(I2S_NUM_0, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("Failed to set I2S pins: %d\n", err);
        while(1);
    }

    // Add debug output
    Serial.printf("I2S Config: SCK=%d, WS=%d, SD=%d, Rate=%d\n", 
                 I2S_SCK, I2S_WS, I2S_SD, SAMPLE_RATE);
}

void loop() {
    int16_t samples[BUFFER_SIZE];
    size_t bytes_read = 0;
    
    esp_err_t err = i2s_read(I2S_NUM_0, samples, sizeof(samples), &bytes_read, portMAX_DELAY);
    if (err == ESP_OK && bytes_read > 0) {
        digitalWrite(LED_PIN, HIGH);
        udp.beginPacket(udpAddress, udpPort);
        udp.write((uint8_t*)samples, bytes_read);
        udp.endPacket();
        digitalWrite(LED_PIN, LOW);
    }
}
