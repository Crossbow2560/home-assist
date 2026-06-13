#pragma once
#include <ESP8266WiFi.h>
#include "config.h"

#define WIFI_TIMEOUT_MS 15000

static bool wifiConnect() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(cfg.ssid.c_str(), cfg.password.c_str());
    Serial.printf("Connecting to '%s'", cfg.ssid.c_str());
    uint32_t t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < WIFI_TIMEOUT_MS) {
        delay(500);
        Serial.print('.');
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("WiFi OK: %s\n", WiFi.localIP().toString().c_str());
        return true;
    }
    Serial.println("WiFi failed — starting AP");
    return false;
}

static void wifiStartAP() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.printf("AP up: SSID='%s' pass='%s' -> http://192.168.4.1\n", AP_SSID, AP_PASS);
}
