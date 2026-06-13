#pragma once
#include <Arduino.h>

struct RuntimeConfig {
    String   ssid       = "REDACTED_WIFI_SSID";
    String   password   = "REDACTED_WIFI_PASS";
    String   mqttServer = "192.168.x.x";
    uint16_t mqttPort   = 1883;
};

// AP mode identity — compile-time only, never written to flash
#define AP_SSID "ESP-NetSwitch"
#define AP_PASS "REDACTED_AP_PASS"   // min 8 chars for WPA2

extern RuntimeConfig cfg;
