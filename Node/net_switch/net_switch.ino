#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266WebServer.h>

#include "config.h"
#include "logger.h"
#include "eeprom_store.h"
#include "wifi_manager.h"
#include "mqtt_handler.h"
#include "web_server.h"

// ── Global objects ───────────────────────────────────────────────────────────
RuntimeConfig    cfg;
CircularLog      logger;
WiFiClient       espWifiClient;
PubSubClient     mqtt(espWifiClient);
ESP8266WebServer server(80);

bool          inAPMode       = false;
bool          needsReconnect = false;
unsigned long reconnectAt    = 0;

const int PIN_LIGHT = D5;
const int PIN_FAN   = D2;

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n--- ESP NetSwitch boot ---");

    pinMode(PIN_LIGHT, OUTPUT);
    pinMode(PIN_FAN,   OUTPUT);

    eepromLoad(); // populate cfg from EEPROM before first WiFi attempt

    if (wifiConnect()) {
        inAPMode = false;
    } else {
        inAPMode = true;
        wifiStartAP();
    }

    mqttInit();
    webServerSetup();
}

// ── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
    server.handleClient();

    // Deferred reconnect — gives HTTP response time to flush before WiFi drops
    if (needsReconnect && reconnectAt == 0) {
        reconnectAt = millis() + 800;
    }
    if (reconnectAt > 0 && millis() >= reconnectAt) {
        needsReconnect = false;
        reconnectAt    = 0;
        mqtt.disconnect();
        WiFi.disconnect(true);
        delay(300);
        if (wifiConnect()) {
            inAPMode = false;
        } else {
            inAPMode = true;
            wifiStartAP();
        }
    }

    // MQTT keep-alive (only in station mode)
    if (!inAPMode) {
        if (!mqtt.connected()) {
            static unsigned long lastAttempt = 0;
            if (millis() - lastAttempt > 5000) {
                lastAttempt = millis();
                mqttReconnect();
            }
        }
        mqtt.loop();
    }
}
