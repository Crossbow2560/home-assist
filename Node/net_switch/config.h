#pragma once
#include <Arduino.h>
#include "secrets.h"   // WIFI_SSID, WIFI_PASS, MQTT_SERVER, AP_PASS (see secrets.h.example)

struct RuntimeConfig {
    String   ssid       = WIFI_SSID;
    String   password   = WIFI_PASS;
    String   mqttServer = MQTT_SERVER;
    uint16_t mqttPort   = 1883;
};

// AP mode identity — compile-time only, never written to flash
#define AP_SSID "ESP-NetSwitch"
// AP_PASS comes from secrets.h (min 8 chars for WPA2)

extern RuntimeConfig cfg;
