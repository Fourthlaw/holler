# Controller (Raspberry Pi 5)

Not started. Services planned (see docs/design.md, section 2):

- Plex Media Server for the music library (here or on another machine)
- Plexamp headless as the house Plex player, feeding Snapserver through an ALSA loopback
- Snapserver for synchronized music
- Intercom server: PTT arbitration, Opus relay, priority pages
- Mosquitto MQTT broker with per-device credentials
- Web app (Flask or FastAPI): music, volumes, schedules, phone pairing
- Scheduler for alarms and announcements
