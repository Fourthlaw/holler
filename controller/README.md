# Controller (Raspberry Pi 5)

Not started. Services planned (see docs/design.md, section 2):

- Music source, one of two modes:
  - Plex mode: Plex Media Server for the library (here or on another machine) and Plexamp headless as the house player, feeding Snapserver through an ALSA loopback
  - Share mode: MPD playing from a network share into a Snapserver pipe, with a music page in the web app
- Snapserver for synchronized music
- Intercom server: PTT arbitration, Opus relay, priority pages
- Mosquitto MQTT broker with per-device credentials
- Web app (Flask or FastAPI): music, volumes, schedules, phone pairing
- Scheduler for alarms and announcements
