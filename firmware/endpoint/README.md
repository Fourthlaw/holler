# Holler endpoint firmware (ESP32-S3)

Not started. One firmware for the in-wall and tabletop endpoints, built with ESP-IDF.

Planned pieces (see docs/design.md, sections 3.1.2 and 3.4.3):

- Snapcast client for music (based on the community ESP32 snapclient)
- Intercom: Opus over UDP/RTP multicast, PTT capture, local ducking
- Audio processing: EQ, crossover, bass boost, limiter (esp-dsp)
- MQTT over TLS for control and telemetry
- Button gestures and status LED (green only; red is driven by hardware)
- Signed OTA updates

The firmware can read the mic mute and PTT state but has no way to change them. Keep it that way.
