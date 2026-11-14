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

    bool on = strcmp(msg, "ON") == 0;
    if (strcmp(topic, "room/light/main") == 0) {
        digitalWrite(PIN_LIGHT, on ? LOW : HIGH);
    } else if (strcmp(topic, "room/fan") == 0) {
        digitalWrite(PIN_FAN,   on ? HIGH : LOW);
    } else {
        return;
    }

    // Confirm on <topic>/state so the Pi bridge knows the switch acted.
    // Copy the topic first: it points into the client buffer that publish() reuses.
    String stateTopic = String(topic) + "/state";
    mqtt.publish(stateTopic.c_str(), on ? "ON" : "OFF", true);
}

static void mqttInit() {
    mqtt.setCallback(mqttCallback);
}

static bool mqttReconnect() {
    mqtt.setServer(cfg.mqttServer.c_str(), cfg.mqttPort);
    Serial.print("MQTT connecting...");
    // The broker publishes "offline" for us if the connection drops.
    if (mqtt.connect("ESP8266Client", "room/switch/status", 1, true, "offline")) {
        Serial.println("OK");
        mqtt.publish("room/switch/status", "online", true);
        mqtt.subscribe("room/light/main");
        mqtt.subscribe("room/fan");
        return true;
    }
    Serial.printf("failed rc=%d\n", mqtt.state());
    return false;
}
