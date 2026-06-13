#pragma once
#include <PubSubClient.h>
#include <ESP8266WiFi.h>
#include "config.h"
#include "logger.h"

extern PubSubClient mqtt;
extern const int    PIN_LIGHT;
extern const int    PIN_FAN;

static void mqttCallback(char* topic, byte* payload, unsigned int len) {
    char msg[65] = {};
    strlcpy(msg, (char*)payload, min((unsigned int)64, len + 1));

    Serial.printf("[MQTT] %s: %s\n", topic, msg);
    logger.push(topic, msg);

    if (strcmp(topic, "room/light/main") == 0) {
        digitalWrite(PIN_LIGHT, strcmp(msg, "ON") == 0 ? LOW : HIGH);
    } else if (strcmp(topic, "room/fan") == 0) {
        digitalWrite(PIN_FAN,   strcmp(msg, "ON") == 0 ? HIGH : LOW);
    }
}

static void mqttInit() {
    mqtt.setCallback(mqttCallback);
}

static bool mqttReconnect() {
    mqtt.setServer(cfg.mqttServer.c_str(), cfg.mqttPort);
    Serial.print("MQTT connecting...");
    if (mqtt.connect("ESP8266Client")) {
        Serial.println("OK");
        mqtt.subscribe("room/light/main");
        mqtt.subscribe("room/fan");
        return true;
    }
    Serial.printf("failed rc=%d\n", mqtt.state());
    return false;
}
