# Remote intercom

Not started. See docs/design.md, section 2.3.

| Folder | Runs on | Job |
|---|---|---|
| `gateway/` | Pi 5 | Outbound connection to the rendezvous server; WebRTC audio to phones, bridged to the house intercom |
| `rendezvous/` | Cloud VPS | Signaling, TURN relay (coturn), Apple push. Untrusted: never holds media keys |
| `ios/` | iPhone | Push-to-talk app (Swift, WebRTC, PushToTalk framework) |

Build order: a LAN-only web paging page served by the gateway first, then the rendezvous server and the iPhone app.

Remote access covers the intercom only, not music or house controls.
