#pragma once
#include <Arduino.h>

struct RuntimeConfig {
    String   ssid       = "Deepak 4G";
    String   password   = "Nishit123!";
    String   mqttServer = "192.168.0.107";
    uint16_t mqttPort   = 1883;
};

// AP mode identity — compile-time only, never written to flash
#define AP_SSID "ESP-NetSwitch"
#define AP_PASS "configure1"   // min 8 chars for WPA2

extern RuntimeConfig cfg;
