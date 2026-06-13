#pragma once
#include <Arduino.h>

#define LOG_CAPACITY 20

struct LogEntry {
    char          topic[48];
    char          payload[64];
    unsigned long ms;
};

class CircularLog {
public:
    void push(const char* topic, const char* payload) {
        LogEntry& e = _buf[_head];
        e.ms = millis();
        strlcpy(e.topic,   topic,   sizeof(e.topic));
        strlcpy(e.payload, payload, sizeof(e.payload));
        _head = (_head + 1) % LOG_CAPACITY;
        if (_size < LOG_CAPACITY) _size++;
    }

    String rowsHTML() const {
        String out;
        out.reserve(_size * 90);
        int start = (_size == LOG_CAPACITY) ? _head : 0;
        for (int i = 0; i < _size; i++) {
            const LogEntry& e = _buf[(start + i) % LOG_CAPACITY];
            out += F("<tr><td>"); out += e.ms / 1000;
            out += F("s</td><td>"); out += e.topic;
            out += F("</td><td>"); out += e.payload;
            out += F("</td></tr>");
        }
        return out;
    }

    int size() const { return _size; }

private:
    LogEntry _buf[LOG_CAPACITY] = {};
    int      _head = 0;
    int      _size = 0;
};

extern CircularLog logger;
