#pragma once
#include <EEPROM.h>
#include "config.h"

#define EEPROM_SIZE  256
#define EEPROM_MAGIC 0xAB12CD34

struct StoredConfig {
    uint32_t magic;
    char     ssid[64];
    char     password[64];
    char     mqttServer[64];
    uint16_t mqttPort;
};

static void eepromLoad() {
    EEPROM.begin(EEPROM_SIZE);
    StoredConfig sc;
    EEPROM.get(0, sc);
    if (sc.magic != EEPROM_MAGIC) {
        Serial.println("EEPROM: no saved config, using compiled defaults");
        return;
    }
    cfg.ssid       = sc.ssid;
    cfg.password   = sc.password;
    cfg.mqttServer = sc.mqttServer;
    cfg.mqttPort   = sc.mqttPort;
    Serial.printf("EEPROM: loaded ssid='%s' mqtt='%s:%d'\n",
                  sc.ssid, sc.mqttServer, sc.mqttPort);
}

static void eepromSave() {
    StoredConfig sc;
    sc.magic = EEPROM_MAGIC;
    strlcpy(sc.ssid,       cfg.ssid.c_str(),       sizeof(sc.ssid));
    strlcpy(sc.password,   cfg.password.c_str(),   sizeof(sc.password));
    strlcpy(sc.mqttServer, cfg.mqttServer.c_str(), sizeof(sc.mqttServer));
    sc.mqttPort = cfg.mqttPort;
    EEPROM.put(0, sc);
    if (EEPROM.commit()) {
        Serial.println("EEPROM: config saved");
    } else {
        Serial.println("EEPROM: commit failed");
    }
}

static void eepromClear() {
    EEPROM.begin(EEPROM_SIZE);
    // Invalidate magic so next boot uses compiled defaults
    uint32_t blank = 0x00000000;
    EEPROM.put(0, blank);
    EEPROM.commit();
    Serial.println("EEPROM: cleared");
}
