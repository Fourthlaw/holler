# Holler endpoint firmware (ESP32-S3)

Not started. One firmware for both endpoint types, built with ESP-IDF, with two build targets:

| Target | Board | Network | Audio out |
|---|---|---|---|
| Tabletop | ESP32-S3-DevKitC-1 | Wi-Fi | Two amp channels, software crossover, battery reporting |
| In-wall | ESP32-S3 with Ethernet and PoE (Waveshare ESP32-S3-ETH) | Wired Ethernet (W5500) | One amp channel |

Planned pieces (see docs/design.md, sections 3.1.2 and 3.4.3):

- Snapcast client for music (based on the community ESP32 snapclient)
- Intercom: Opus over UDP/RTP multicast, PTT capture, local ducking, priority pages
- Audio processing: EQ, crossover, bass boost, limiter, and background mode (esp-dsp)
- MQTT over TLS for control and telemetry
- Five buttons: TALK and its double-press gesture, volume, and the BACKGROUND toggle. MIC MUTE is read only
- Status glow: the firmware drives green only, and only in answer to a button press. Red is driven by hardware
- Signed OTA updates

The firmware can read the mic mute and PTT state but has no way to change them. Keep it that way.
