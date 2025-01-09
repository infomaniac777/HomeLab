#include <driver/i2s.h>
#include <Arduino.h>

#define I2S_WS 22
#define I2S_SD 21
#define I2S_SCK 19
#define SAMPLE_RATE 4000
#define BUFFER_SIZE 1024

void setup() {
    Serial.begin(9600);  // Increase baud rate
    delay(1000);  // Give serial time to initialize
    Serial.println("Starting I2S Microphone test...");
    
    const i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = BUFFER_SIZE,
        .use_apll = false,
        .tx_desc_auto_clear = false,
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
}

void loop() {
    int32_t samples[BUFFER_SIZE];
    size_t bytes_read = 0;
    
    esp_err_t err = i2s_read(I2S_NUM_0, samples, sizeof(samples), &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
        Serial.printf("Failed to read I2S data: %d\n", err);
        delay(1000);
        return;
    }
    
    // Calculate average amplitude with scaling
    int32_t sum = 0;
    for(int i = 0; i < BUFFER_SIZE; i++) {
        // Scale down 32-bit value and take absolute value
        int32_t scaled = abs(samples[i] >> 16);  // Scale down to 16-bit
        sum += scaled;
        
        if (i < 10) {  // Print first 10 samples only
            Serial.printf("Sample[%d]: Raw=%ld, Scaled=%ld\n", i, samples[i], scaled);
        }
    }
    int32_t average = sum / BUFFER_SIZE;
    
    // Print a visual meter with adjusted scale
    Serial.print("Level: ");
    for(int i = 0; i < (average >> 8); i++) {  // Adjust divisor as needed
        Serial.print("*");
    }
    Serial.println();
    
    delay(100);  // Shorter delay for more responsive readings
}
