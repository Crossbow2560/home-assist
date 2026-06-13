#pragma once
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include "logger.h"
#include "eeprom_store.h"

extern ESP8266WebServer server;
extern PubSubClient     mqtt;
extern bool             inAPMode;
extern bool             needsReconnect;
extern const int        PIN_LIGHT;
extern const int        PIN_FAN;

static String pageWrap(const char* title, const String& body) {
    String p;
    p.reserve(640 + body.length());
    p  = F("<!DOCTYPE html><html><head>"
           "<meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           "<style>"
           "body{font-family:sans-serif;max-width:620px;margin:22px auto;padding:0 14px}"
           "nav a{margin-right:14px;text-decoration:none;font-weight:bold}"
           "table{border-collapse:collapse;width:100%}"
           "td,th{border:1px solid #ccc;padding:8px;text-align:left}"
           "input[type=text],input[type=password],input[type=number]"
           "{width:100%;padding:6px;margin:4px 0 10px;box-sizing:border-box}"
           "input[type=submit]{padding:8px 20px;cursor:pointer}"
           "label{font-weight:bold;font-size:.9em}"
           ".ok{color:#1a7f1a}.err{color:#c22}.note{color:#666;font-size:.85em}"
           "</style><title>");
    p += title;
    p += F(" | NetSwitch</title></head><body>"
           "<h2>ESP NetSwitch</h2>"
           "<nav><a href='/'>Status</a><a href='/config'>Config</a><a href='/logs'>Logs</a></nav><hr>");
    p += body;
    p += F("</body></html>");
    return p;
}

// ── Status dashboard ────────────────────────────────────────────────────────
static void handleRoot() {
    bool wifiOk = WiFi.status() == WL_CONNECTED;
    bool mqttOk = mqtt.connected();

    String body;
    body.reserve(500);
    body  = F("<h3>Status</h3><table>"
              "<tr><th style='width:40%'>Parameter</th><th>Value</th></tr>");

    body += F("<tr><td>Mode</td><td>");
    body += inAPMode
        ? F("<span class='err'>&#9888; AP — connect to ESP-NetSwitch and visit <a href='http://192.168.4.1/config'>192.168.4.1/config</a></span>")
        : F("<span class='ok'>&#10003; Station</span>");
    body += F("</td></tr>");

    body += F("<tr><td>WiFi</td><td class='");
    body += wifiOk ? F("ok'>") : F("err'>");
    if (wifiOk) { body += WiFi.localIP().toString(); body += F(" ("); body += cfg.ssid; body += ')'; }
    else          body += F("Not connected");
    body += F("</td></tr>");

    body += F("<tr><td>MQTT</td><td class='");
    body += mqttOk ? F("ok'>&#10003; Connected") : F("err'>&#10005; Disconnected");
    body += F("</td></tr>");

    body += F("<tr><td>MQTT server</td><td>"); body += cfg.mqttServer; body += ':'; body += cfg.mqttPort; body += F("</td></tr>");
    body += F("<tr><td>Light (D5)</td><td>"); body += digitalRead(PIN_LIGHT) == LOW  ? F("ON") : F("OFF"); body += F("</td></tr>");
    body += F("<tr><td>Fan (D2)</td><td>");   body += digitalRead(PIN_FAN)   == HIGH ? F("ON") : F("OFF"); body += F("</td></tr>");
    body += F("<tr><td>Uptime</td><td>"); body += millis() / 1000; body += F("s</td></tr>");
    body += F("<tr><td>Free heap</td><td>"); body += ESP.getFreeHeap(); body += F(" B</td></tr>");
    body += F("</table>");

    server.send(200, F("text/html"), pageWrap("Status", body));
}

// ── Config page (GET) ───────────────────────────────────────────────────────
static void handleConfig() {
    String body;
    body.reserve(600);
    body  = F("<h3>WiFi &amp; MQTT Configuration</h3>"
              "<p class='note'>Changes apply immediately in RAM. On power cycle the device reverts to compiled defaults.</p>"
              "<form method='POST' action='/config'>"
              "<label>SSID</label>"
              "<input type='text' name='ssid' value='");
    body += cfg.ssid;
    body += F("'>"
              "<label>Password <span class='note'>(leave blank to keep current)</span></label>"
              "<input type='password' name='pass' placeholder='unchanged'>"
              "<label>MQTT Server</label>"
              "<input type='text' name='mqtt' value='");
    body += cfg.mqttServer;
    body += F("'>"
              "<label>MQTT Port</label>"
              "<input type='number' name='port' value='");
    body += cfg.mqttPort;
    body += F("'>"
              "<input type='submit' value='Apply &amp; Reconnect'>"
              "</form>"
              "<hr><form method='POST' action='/reset' "
              "onsubmit=\"return confirm('Clear saved config and revert to defaults on next boot?')\">"
              "<input type='submit' value='Clear EEPROM' style='background:#c22;color:#fff'>"
              "</form>");

    server.send(200, F("text/html"), pageWrap("Config", body));
}

// ── Config page (POST) ──────────────────────────────────────────────────────
static void handleConfigPost() {
    if (server.hasArg("ssid") && server.arg("ssid").length() > 0)
        cfg.ssid = server.arg("ssid");
    if (server.hasArg("pass") && server.arg("pass").length() > 0)
        cfg.password = server.arg("pass");
    if (server.hasArg("mqtt") && server.arg("mqtt").length() > 0)
        cfg.mqttServer = server.arg("mqtt");
    if (server.hasArg("port") && server.arg("port").toInt() > 0)
        cfg.mqttPort = (uint16_t)server.arg("port").toInt();

    String body = F("<p class='ok'>&#10003; Config saved to RAM. Reconnecting&hellip;</p>"
                    "<p><a href='/'>Back to Status</a></p>");
    eepromSave(); // persist before WiFi drops

    server.send(200, F("text/html"), pageWrap("Config", body));
    server.handleClient(); // flush response before WiFi drops

    needsReconnect = true;
}

// ── EEPROM clear (POST /reset) ───────────────────────────────────────────────
static void handleReset() {
    eepromClear();
    String body = F("<p class='ok'>&#10003; EEPROM cleared. Compiled defaults will be used on next boot.</p>"
                    "<p><a href='/'>Back to Status</a></p>");
    server.send(200, F("text/html"), pageWrap("Reset", body));
}

// ── Logs page ───────────────────────────────────────────────────────────────
static void handleLogs() {
    String body;
    body.reserve(300 + logger.size() * 90);
    body  = F("<h3>MQTT Log</h3>"
              "<meta http-equiv='refresh' content='5'>"
              "<table>"
              "<tr><th>Uptime</th><th>Topic</th><th>Payload</th></tr>");
    if (logger.size() == 0)
        body += F("<tr><td colspan='3' class='note'>No messages received yet.</td></tr>");
    else
        body += logger.rowsHTML();
    body += F("</table><p class='note'>Auto-refreshes every 5 s &mdash; last ");
    body += logger.size();
    body += F(" of "); body += LOG_CAPACITY; body += F(" slots used.</p>");

    server.send(200, F("text/html"), pageWrap("Logs", body));
}

// ── Init ────────────────────────────────────────────────────────────────────
static void webServerSetup() {
    server.on("/",       HTTP_GET,  handleRoot);
    server.on("/config", HTTP_GET,  handleConfig);
    server.on("/config", HTTP_POST, handleConfigPost);
    server.on("/logs",   HTTP_GET,  handleLogs);
    server.on("/reset",  HTTP_POST, handleReset);
    server.begin();
    Serial.println("HTTP server on :80");
}
