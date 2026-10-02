# Holler remote intercom

Not started. See docs/design.md, section 2.3.

| Folder | Runs on | Job |
|---|---|---|
| `gateway/` | Pi 5 | WebRTC audio to phones, bridged to the house intercom |
| `rendezvous/` | Cloud VPS | Signaling, TURN relay (coturn), push. Untrusted: never holds media keys. Rendezvous mode only |
| `ios/` | iPhone | Push-to-talk app (Swift, WebRTC, PushToTalk framework) |
| `android/` | Android phone | Push-to-talk app (Kotlin, WebRTC, foreground service, FCM) |

Two ways for a phone to reach the house:

- **Rendezvous mode (default):** the Pi and the phone both connect out to the rendezvous server. No inbound port at home.
- **Direct mode (lower security):** the router forwards two ports to the gateway. No hosted server, but a service at home is exposed to the internet.

Pairing, signed setup messages, and end-to-end audio encryption are the same in both.

Build order: a LAN-only web paging page served by the gateway first, then rendezvous mode and one native app, then the second app and direct mode.

Remote access covers the intercom only, not music or house controls.
