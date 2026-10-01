# Whole-Home Intercom + Music System Design

## 1. Goals

- Whole-home synchronized music playback, same program in all rooms.
- Intercom: any room can press PTT and page all rooms. No per-room routing.
- Music ducking: music level drops (or mutes) while intercom audio plays, then restores.
- Low hardware cost and low in-wall complexity for standard rooms.
- Upgradeable: some rooms can use higher-fidelity stereo endpoints.
- All endpoints digitally controllable (volume, mute, overrides) from a central controller.
- Privacy by design: a room microphone is powered only while someone in that room holds PTT and the room's mic mute is off. Both conditions are enforced in hardware. No software path, including compromised firmware, can enable a microphone.
- Remote intercom: family phones can page the house and hear house pages from anywhere, without a VPN and without opening any inbound port at home. Remote access covers the intercom only, not the music stream or house controls.

---

## 2. System architecture

### 2.1 Central controller (Raspberry Pi 5)

**Hardware**

- Raspberry Pi 5.
- Wired Ethernet.
- On UPS power, same as the PoE switch (see 3.1.1 Power).

**Roles**

1. **Music distribution**
   - Runs Snapserver for synchronized multi-room audio.
   - Sources: local music library (same storage Plex uses; Snapserver is the player), internet radio, TTS, alert tones.
   - Snapcast buffers audio (default about 1 s) to keep rooms in sync. That is fine for music and is the reason intercom uses a separate path.

2. **Intercom server**
   - Low-latency path, separate from Snapcast.
   - Transport: Opus over UDP/RTP multicast on the endpoint VLAN. Target end-to-end latency under 150 ms.
   - Arbitration: first endpoint to press PTT holds the channel. Any other endpoint that presses PTT while the channel is held gets a "busy" LED indication and does not transmit. A priority page does not pre-empt a page already in progress; it waits for the channel like any other.
   - Relays the active talker's audio to all other endpoints. The talking endpoint does not receive its own audio.

3. **Control and orchestration**
   - Web application (Flask or FastAPI):
     - Play/pause, source select, global volume.
     - Per-endpoint volume and mute.
     - Schedules and alarms.
     - Intercom status.
   - Endpoint control over MQTT (Mosquitto broker on the Pi) with per-device credentials.
   - REST/WebSocket API for the web UI and integrations.

4. **Scheduling and alarms**
   - Scheduler for morning alarms, timed announcements, and quiet-hours windows.
   - Alarm events play a stream or sound file through Snapserver and can apply a system volume override (see 3.1.2 volume rules).

### 2.2 Network and security

- Endpoints live on a dedicated IoT VLAN. Only the controller is reachable from that VLAN; endpoints cannot reach the internet.
- MQTT with TLS and a unique username/password (or client cert) per endpoint. Endpoints ignore commands from any other source.
- OTA firmware images are signed (ESP-IDF secure boot / signed app images). Endpoints reject unsigned images.
- No inbound services on endpoints beyond what the audio and control protocols require.
- Nothing at home accepts inbound connections from the internet. Remote intercom (2.3) runs over an outbound connection from the Pi.

### 2.3 Remote intercom (iPhone app via a cloud rendezvous server)

**Scope:** intercom only. A remote phone can page the house and hear house pages. It cannot join the music stream, change volumes, read room state, or reach any admin or firmware function. Music and house controls stay on the local network and the local web app.

**Pieces**

| Piece | Runs on | Job |
|---|---|---|
| Rendezvous server | Small cloud VPS (smallest tier, about $5 a month) | Relays setup messages between the Pi and phones, runs a TURN relay (coturn) for when a direct path fails, and sends Apple push notifications to wake phones |
| Remote intercom gateway | Pi 5 | Holds the outbound connection to the rendezvous server, terminates the phone's WebRTC audio, and bridges it to and from the house intercom |
| Intercom app | iPhone | Push-to-talk app built on Apple's PushToTalk framework (iOS 16 and later) and WebRTC |

**Connection model**

- The Pi keeps one outbound secure WebSocket (TLS on 443) open to the rendezvous server. That is the only connection home makes to the internet for this feature. No port forwarding, no inbound rules, no VPN.
- The phone also connects to the rendezvous server over a secure WebSocket, only when it needs to: when the user presses TALK, or when a push says a page is starting.
- Audio runs over WebRTC between the phone and the Pi: Opus, mono, about 24 to 32 kbps, encrypted end to end with DTLS-SRTP.
- Both sides first try a direct path (ICE with STUN, which punches through most home NATs). When that fails, common on cellular networks, the audio relays through TURN on the rendezvous server. Either way the server never holds the media keys.

**Trust model: the cloud server is untrusted**

WebRTC encryption is only as good as the setup messages that carry each side's DTLS fingerprint. A compromised server could swap fingerprints and sit in the middle. So setup is authenticated end to end, independent of the server:

- **Pairing on the home network:** each phone is paired once, in person, on the LAN. The Pi's local web UI shows a QR code; the app scans it. The phone and the Pi exchange Ed25519 public keys. The Pi records the phone's key, name, and permissions.
- **Signed setup messages:** every offer, answer, and session message is signed by its sender's device key and carries a nonce and timestamp (replay protection).
- **Fingerprint binding:** the DTLS fingerprint is inside the signed message. Each side rejects a connection whose actual fingerprint does not match a signed message from a paired device.
- **Result:** the rendezvous server sees who is talking to whom and when, plus encrypted packets. It cannot listen, inject audio, or impersonate a phone or the house.

**Paging from the phone**

1. User presses TALK in the app (or the system PTT button). The app connects to the rendezvous server and sends a signed offer to the Pi.
2. The Pi verifies the signature and the phone's permissions, then requests the house intercom channel exactly as a room endpoint would. If another room holds the channel, the app shows busy.
3. Audio flows phone to Pi over WebRTC; the Pi relays it onto the house intercom multicast. Rooms duck music and play it like any other page.
4. Priority page from a phone works only if that phone's permissions allow it.

**Hearing house pages on the phone**

1. A room starts a page. The Pi begins buffering the audio and asks the rendezvous server to push to each subscribed phone.
2. The rendezvous server sends an Apple PushToTalk push. iOS wakes the app and shows the system talk UI, even when the phone is locked.
3. The app connects and the Pi plays the buffered page from the start, then live. Expect about 1 to 2 seconds of added delay on the phone for the first page after the app wakes.
4. Each phone can turn its page subscription off (for example at night or at work).

**Permissions (set per phone, at the Pi)**

| Permission | Default |
|---|---|
| Page the house | on |
| Priority page | off |
| Receive house pages | on |
| Music, volumes, room state, admin | not available remotely, for any phone |

Revoking a phone at the Pi takes effect immediately; the rendezvous server only ever holds public keys and push tokens.

**Mic privacy is unchanged.** Nothing remote can open a room microphone. A house page reaches a phone only because someone in a room is holding TALK, and the room mics stay behind the hardware PTT and mute latch circuit (3.1.1).

**Rendezvous server hardening**

- Open ports: 443/tcp (WebSocket and TLS), 3478 udp/tcp (STUN/TURN), and a narrow UDP relay port range for TURN. Nothing else.
- TURN credentials are short-lived and issued per session (the TURN REST credential scheme), so a leaked credential expires in minutes.
- Rate limits on connections, setup messages, and push requests per device.
- The Pi authenticates to the server with its own device key; the server accepts only the paired Pi and paired phones.
- No house control endpoints exist on the server, so there is nothing there to abuse even if it is taken over.
- Minimal logging (device IDs and timestamps, no audio), automatic security updates, and a rebuild-from-script setup so the box can be replaced quickly.

**Build notes**

- Pi side: Pion (Go) or aiortc (Python) for WebRTC.
- iPhone side: the standard WebRTC framework plus Apple's PushToTalk framework. This needs a paid Apple developer account ($99 a year), which also allows installing on family phones through TestFlight.
- Phase 1, on the LAN only: a small web page served by the Pi that does WebRTC paging from Safari. It proves the gateway and signing scheme with no app and no cloud server.
- Phase 2: the rendezvous server and the native iPhone app.

---

## 3. Endpoint types

### 3.1 Standard endpoint (in-wall mono, ESP32-S3)

**Use case:** typical rooms needing intercom and background music.

#### 3.1.1 Hardware

**MCU**

- ESP32-S3 with PSRAM (for example ESP32-S3-WROOM-1 N8R8).
- Preferred: an ESP32-S3 board with onboard Ethernet and PoE (Waveshare and LilyGO both make these). See Power.
- The S3 has two I2S peripherals: I2S0 drives the amplifier, I2S1 reads the microphone.

**Amplifier**

- Preferred: Adafruit I2S 3W Class D Amplifier Breakout (MAX98357A).
  - I2S input with built-in DAC and Class-D amp.
  - Up to about 3.2 W into 4 ohms at 5 V.
  - About 19.4 x 17.8 x 3 mm.
  - SD pin can select left, right, or (L+R)/2 in hardware, so downmix can happen in the chip.
  - GAIN pin sets fixed gain (default 9 dB). Set per build after listening tests.
- Alternates (functionally equivalent): SparkFun I2S Audio Breakout (MAX98357A), DFRobot DFR0954 (MAX98357A).

**Speaker (2 in. class, 4 ohm)**

Sensitivity matters more than power handling here, since the amp only delivers about 3 W.

| Driver | Size | Impedance | RMS | Sensitivity | Response | Notes |
|---|---|---|---|---|---|---|
| Dayton Audio CE52N-4 | 2 in. | 4 ohm | 5 W | 85 dB | 120 Hz - 20 kHz | **Preferred.** Good balance of output and low end. |
| Dayton Audio CE53N-4 | 2 in. | 4 ohm | 10 W | 87 dB | 200 Hz - 20 kHz | Louder alternate for large rooms; less bass. |
| Dayton Audio CE48-4 | 2 in. | 4 ohm | 5 W | 79 dB | 120 Hz - 20 kHz | Budget option. About 6 dB quieter than CE52N-4 at the same power. |
| Dayton Audio CE58N-10 | 2 in. | 10 ohm | 15 W | - | - | Not recommended. At 10 ohms the amp delivers well under half its 4 ohm output. |

Confirm depth on the spec sheet before finalizing the bracket.

**Speaker sizing limits (double-gang box)**

- Diameter: 2 to 2.5 in. recommended, about 3 in. maximum.
- Depth: 1 to 1.5 in. recommended, about 2 in. maximum.

**Microphone**

- Preferred: INMP441 I2S MEMS microphone module (ElectroPeak, about $1.75).
  - Omnidirectional, bottom port, digital I2S output, no external preamp or ADC.
  - Outputs 24-bit data in a 32-bit I2S slot. Firmware must shift accordingly.
- Alternates: generic INMP441 modules (same pinout), ICS-43434 modules.

**Mic mounting and isolation**

- The double-gang box acts as the speaker's enclosure, so the mic must be sealed from the inside of the box.
- Mount the module so its port lines up with a 2 to 3 mm hole in the plate. Seal around the port with a foam or silicone gasket so the mic hears only the room.
- Place the mic as far from the speaker as the plate allows.
- Secure the breakout mechanically and strain-relieve the wires.

**Mic privacy circuit (all endpoints with a microphone)**

The microphone is powered only when both of these are true, and each is decided by hardware:

1. PTT is physically held.
2. The mic mute latch is off.

Circuit:

- **Two switches in series on the mic supply.** INMP441 VDD feeds through two load switches (or P-channel MOSFETs) in series. The first is driven directly by the PTT switch contact. The second is driven directly by the mute latch. Either one open means no power to the mic.
- **Mute latch.** The MIC MUTE button (momentary tact switch) goes through an RC debounce and a Schmitt trigger into a D flip-flop (74LVC1G74 class) wired to toggle (/Q fed back to D). Each press flips mute on or off.
- **Power-up state is muted.** An RC on the flip-flop's preset input forces mute on at power-up. After a full power loss, the mic stays off until someone presses MIC MUTE.
- **No back-powering through the data lines.** A powered-down mic can be partly powered through its I2S pins by the ESP32's clocks. SCK, WS, and SD pass through a small logic buffer with Ioff (74LVC class) that is itself powered from the switched mic rail. When the rail is off, the buffer is high-impedance and the mic is fully dead. SD has a pull-down on the ESP32 side.
- **Hardware glow.** The red element of the status LED is driven directly from the mute latch output through a resistor. Red means the mic is disconnected, and firmware cannot fake it or turn it off.
- **Firmware can read, not write.** The ESP32 reads the PTT line and the mute state on input-only GPIOs through series resistors. No GPIO connects to the latch clock, D, preset, or clear inputs, or to either load switch enable. Verify this with a continuity check on every board before it goes into an enclosure.
- After the mic rail turns on, allow for the INMP441 startup time (tens of ms) before treating samples as valid.

**Controls (moving button caps over tact switches)**

- Four PCB-mounted 6x6 mm tactile switches: `VOL_DOWN`, `PTT`, `VOL_UP`, `MIC_MUTE`.
- `VOL_DOWN` and `VOL_UP` are SPST-NO to ground on GPIOs with internal pull-ups. `PTT` and `MIC_MUTE` drive the mic privacy circuit directly; the ESP32 only reads them.

Plate design:

- Each button is a separate printed cap that moves in an opening in the plate. Nothing flexes; the plate stays rigid.
- The cap slides in a short guide collar on the back of the plate (0.3 mm clearance per side), is kept from falling out by a flange under the collar, and has a stem that rests on its tact switch. The switch provides the return spring and the click.
- Caps are loaded from behind before the switch board goes on, so they are captive and there are no visible fasteners.
- Layout, left to right: `VOL_DOWN`, `PTT`, `VOL_UP`, with `MIC_MUTE` set apart from the other three so it is not pressed by accident. The in-wall plate layout needs a revision to fit the fourth button.
- Touch marks engraved in the cap tops: a dish on PTT, minus and plus on volume, a slashed ring on MIC MUTE.
- Print plate and caps in PETG. Caps print top-down so the touch surface is the smooth bed side.

The tabletop endpoint (3.4) uses the same cap design at a larger size; its generator is the reference implementation.

**Status LED (optional, indirect)**

- Bicolor (red/green) LED on the PCB behind the speaker grille or a diffused window. Indirect light only.
- Driven at very low current (0.1 to 0.5 mA) through large series resistors so it is bedroom-safe.
- **Red is hardware-only:** driven by the mic mute latch, steady soft glow while the mic is disconnected. Firmware has no control over it.
- **Green is firmware:**
  - Off in normal operation.
  - On while volume buttons are pressed; fades out about 1 s after the last press.
  - Slow pulse while the speaker is muted.
  - Quick blinks if PTT is pressed while another room holds the channel, or while the mic is muted.
- The red glow cannot be disabled per room, since it is the visible proof that the mic is off. Green can be disabled per room in firmware.

**Power**

Preferred: PoE.

- 802.3af PoE to each endpoint, either on an ESP32-S3 board with integrated PoE or through a PoE splitter to 5 V.
- Benefits: one Class 2 cable per room, wired sync and control, central UPS backup, no line voltage in the wall at the endpoint.
- Budget: ESP32-S3 Wi-Fi/Ethernet peaks plus a 3 W amp into 4 ohms. Plan for 5 V at 2 A at the endpoint. 802.3af covers this.

Alternate: local 5 V supply.

- Isolated 120 V to 5 V, 2 A minimum supply in a separate, accessible box.
- Line-voltage and Class 2 wiring are not in the same box unless separated by a listed barrier.

**Mechanical**

- Box: double-gang new-work box, about 4 x 4 in., 2.5 to 3.5 in. deep, about 34 cu. in.
- The box doubles as a sealed speaker enclosure. Seal the cable entry so the enclosure stays closed.
- 3D-printed parts:
  - **Speaker bracket:** holds the driver, aligns it with the grille, routes wires, and provides standoffs for the MCU and amp boards.
  - **Wall plate:**
    - Round speaker grille sized to the chosen driver.
    - Mic port hole aligned with the gasketed INMP441.
    - Four button openings with guide collars for the moving caps (TALK, VOL -, VOL +, MIC MUTE).
    - Optional diffused LED window.
    - Optional service door for USB access during flashing and debug.

#### 3.1.2 Firmware

**Base**

- ESP-IDF.
- Music: community Snapcast client for ESP32 (CarlosDerSeher/snapclient). There is no official ESP32 Snapclient.
- Intercom: Opus decode/encode, UDP/RTP.
- Control: MQTT over TLS.

**State**

- `music_volume` (0-100)
- `music_mute` (bool)
- `intercom_volume` (0-100)
- `intercom_mute` (bool, "do not disturb")
- `system_override_volume` (0-100 or unset)
- `system_mute` (bool)
- `duck_level` (dB, for example -20 dB, or full mute)
- `priority_floor` (0-100, default 70): minimum playback level for a priority page
- `night_lock` (bool, per room): hard quiet that even a priority page respects
- `mic_muted` (bool, **read-only**): mirrors the hardware mute latch; firmware cannot change it

**Button gestures**

| Gesture | Action |
|---|---|
| Hold TALK | Normal page to all rooms |
| Double-press TALK (tap, then press and hold within about 400 ms) | Priority page (see below) |
| VOL + / VOL - | Step `music_volume`; auto-repeat on hold |
| Hold VOL + and VOL - together about 0.75 s | Toggle `music_mute` (speaker only) |
| MIC MUTE | Toggle the hardware mic mute latch. Firmware sees the change but plays no part in it. |

A normal PTT starts on the first press, so the double-press gesture adds no delay to ordinary pages. A tap that is released quickly sends nothing.

If TALK is pressed while the mic is muted, the endpoint does not request the channel. It blinks green and plays a short local "mic is muted" chirp.

**Priority page**

- Sent with the double-press TALK gesture.
- Receiving rooms play it at `max(intercom_volume, priority_floor)`, so it overrides low volume settings.
- It breaks through `music_mute` and `intercom_mute`.
- It does not override `night_lock`. That is for rooms where nothing should ever play, such as a sleeping child's room.
- The controller keeps an allow-list of endpoints permitted to send priority pages, rate-limits them, and logs each one.

**Volume rules (in priority order)**

1. `system_mute` silences everything.
2. `night_lock` silences everything except `system_override_volume` alarms the room is subscribed to.
3. If `system_override_volume` is set (alarms, announcements), it applies to the override source only. It never raises music in a room above that room's `music_volume`.
4. A priority page plays at `max(intercom_volume, priority_floor)` and ignores `intercom_mute` and `music_mute`.
5. A normal page plays at `intercom_volume` unless `intercom_mute` is set. Whether it breaks through `music_mute` is a per-room setting (default: yes).
6. Music plays at `music_volume` unless `music_mute` is set, and drops by `duck_level` while intercom audio is playing.

All volume values map to gain on a dB curve (for example 0 to 100 maps to -60 dB to 0 dB, with 0 as true mute), not a linear scale.

**Tasks**

- **Network task**
  - Ethernet (preferred) or Wi-Fi with reconnect.
  - Connects to Snapserver, the intercom multicast group, and the MQTT broker.

- **Audio mix and playback task**
  - Receives and decodes the Snapcast stream (FLAC, Opus, or PCM).
  - Receives and decodes intercom Opus packets.
  - Downmix to mono either in firmware `(L+R)/2` or in the MAX98357A via the SD pin.
  - Ducking is local: when intercom packets arrive, music gain ramps down by `duck_level` over about 50 ms; it ramps back up about 500 ms after the last intercom packet. No controller round trip.
  - Mixes both streams, applies gain, writes to I2S0 via DMA.

- **Intercom capture task**
  - On PTT press: if `mic_muted`, refuse locally (see gestures). Otherwise request the channel (normal or priority) from the intercom server. If granted, mute local speaker output, wait for mic startup, capture from I2S1, encode Opus, transmit.
  - If denied: blink busy indication, do not transmit.
  - On PTT release: stop transmit, release channel, restore local speaker.

- **Button and LED task**
  - Debounce all four zones and decode the gestures above.
  - VOL_UP / VOL_DOWN: step `music_volume` (for example 5 per press).
  - Drive LED per the behavior above and per-room LED policy.

- **Control and telemetry**
  - Accepts commands only over authenticated MQTT.
  - Commands: set music/intercom volume and mute, set or clear system override, set system mute, set per-room policy. There is no command for the mic mute; it exists only as a button.
  - Reports: online status, PTT events, volume and mute state, `mic_muted`, firmware version, errors.
  - Signed OTA updates.

---

### 3.2 HiFi endpoint (Pi Zero 2 W + stereo speakers)

**Use case:** rooms where music quality matters more than in-wall simplicity.

**Hardware**

- Raspberry Pi Zero 2 W (or Pi 3/4 if wired Ethernet is wanted without an adapter).
- Stereo DAC/amp HAT (HiFiBerry MiniAmp for small speakers, HiFiBerry Amp2/Amp4 for larger passive speakers), or a DAC HAT feeding powered speakers.
- Pair of in-wall, in-ceiling, or bookshelf speakers matched to the amp.

**Software**

- Snapclient for music.
- Intercom client for receive. A USB or I2S mic plus a PTT button can be added if the room needs to page.
- Same MQTT control model and volume rules as the standard endpoint.

### 3.3 HiFi system endpoint (existing stereo or AVR)

**Use case:** living room or other space with an existing receiver.

**Hardware**

- Raspberry Pi with a DAC HAT (or USB DAC) feeding an AVR analog or digital input.

**Software**

- Snapclient for music.
- Intercom receive optional. If enabled, the AVR must be on and set to the right input for pages to be heard. HDMI-CEC or IR control can switch it.

### 3.4 Tabletop endpoint (desktop, USB-C, battery-backed)

**Use case:** rooms where an in-wall box is not practical (rentals, desks, nightstands, the shop), or where the endpoint should stay up through a power blip.

Same electronics and firmware as the standard endpoint (3.1), in a printed desktop enclosure with a folded transmission line, USB-C power, and a battery that carries it through outages.

#### 3.4.1 Form factor

- Low slab, small-router style.
- Outer size: **250 W x 173 D x 84 H mm** (base 81 mm + 3 mm lid). Fits the A1's 256 x 256 mm bed.
- Height is set by the front-firing 2.5 in. woofer (70 mm square frame) and its magnetic grille ring. The tweeter fits beside it without changing the box size.
- Layout, viewed from the front:
  - Left three quarters: transmission line, with the woofer and a small tweeter side by side in a recess on the front face, behind one removable cloth grille.
  - Right third: electronics bay (amp, ESP32-S3, battery, charger), mic port and light bar on the front face, four button caps in the lid above.
- The top shows only the four button caps: no screws or other hardware. The lid is held by six M3 screws that come up through the bottom, where the four adhesive feet also go.
  - Rear: line mouth slots and USB-C power.

#### 3.4.2 Acoustic design: folded transmission line

The back wave of the driver loads a folded, tapered quarter-wave line (the same idea as the Bose Wave waveguide, at a much smaller scale). The line reinforces output around its quarter-wave frequency, which lifts the low end of a small driver that rolls off quickly below its resonance. It will not make deep bass from a 2.5 in. driver, but with the line tuned near the driver's 109 Hz resonance it gives voices real body and background music a usable low end.

| Parameter | Value |
|---|---|
| Driver | Dayton Audio CE70PR-4, 2.5 in. (Fs 109 Hz, Qts 0.63, Vas 0.52 L, Sd 24.6 cm2, Xmax 4.0 mm, 85 dB, 38.6 mm deep, 41.2 mm with terminals) |
| Line type | Offset-driver, tapered quarter-wave line, folded into 4 legs |
| Internal height | 78.6 mm |
| Leg widths | 53 / 42 / 36 / 31 mm |
| Cross-section | 41.7 / 33.0 / 28.3 / 24.5 cm2 (about 1.7 x Sd tapering to 1.0 x Sd) |
| Centerline length | about 730 mm (about 750 mm with mouth end correction) |
| Quarter-wave tuning | about 115 Hz, just above driver Fs |
| Driver offset | about 135 mm from the closed end (18 percent of line length; offset position helps suppress the line's 3rd harmonic peak) |
| Line volume | about 2.4 L |
| Mouth | Vertical slots in the rear wall near the end of leg 4, about 50 mm wide, open area about equal to the leg 4 cross-section |

Why this driver (compared with the 2 in. CE52N-4 used earlier):

- About 9 times the displacement before it runs out of travel (Xmax 4.0 mm vs 0.85 mm, twice the cone area).
- Resonance 109 Hz instead of 164 Hz, so the line tunes half an octave lower.
- Same 85 dB sensitivity, so the 3 W amp drives it just as loud. Power and battery are unchanged.
- Qts 0.63 suits a transmission line. The 3 in. CE78PF-4 was rejected: its Qts of 0.99 makes a line boomy, and its 1.4 mm Xmax gives up most of the size advantage.
- Trade-off: top end rolls off around 13 kHz. Fine for voice and background music.

Construction details:

- The closed end of the line is at the separator wall (right end of leg 1). The driver sits toward the left end of leg 1, so a short closed stub sits behind it on one side and the long line runs out the other.
- Turns use 45 degree deflectors at the outer corners to reduce reflections. The front-left corner of leg 1 is left square because the driver recess sits there.
- The lid has 1.2 mm grooves that the line walls and separator wall seat into. Run a thin bead of silicone or 1 mm foam tape in the grooves at assembly so the legs are sealed from each other. Leaks between legs shorten the effective line.
- Damping: lightly stuff the closed stub and the first half of leg 1 with polyfill. Start with about 6 to 8 grams and tune by ear and measurement. More stuffing smooths the midrange ripple and lowers output at the tuning frequency.
- Tuning knobs if it needs adjustment after measuring: leg widths (taper), stuffing amount, and mouth open area. All are parameters in the generator script.
- Firmware EQ: a gentle high-pass around 80 to 90 Hz keeps the driver from wasting excursion below the line's useful range.

**Tweeter**

- Dayton Audio ND16FA-6, 5/8 in. neodymium soft dome: 6 ohm, Fs 2125 Hz, 88 dB, response 3.5 to 27 kHz, 32.5 mm faceplate, 25 mm cutout, 14.5 mm deep.
- Sits to the right of the woofer at the same height, 53 mm center to center. That spacing is well under one wavelength at the crossover frequency, so the two drivers blend cleanly.
- It is a sealed-back dome, so it can sit in leg 1 of the line without its back wave mattering.
- The crossover, levels, and time alignment are all done in software on the ESP32-S3 (see 3.4.3, Audio processing). There is no passive crossover.

**Driver mounting and grille**

- The front face has a 129 x 76 mm rounded-rectangle recess, 4.5 mm deep, in front of both drivers. The baffle at the bottom of the recess is 5 mm thick.
- The driver mounts from the front with no printed grillwork in the way. Its 70 x 70 mm square frame (R7 corners) drops into a 3 mm counterbore so the frame face is flush with the recess floor. The baffle cutout is 64 mm.
- Four M4 screws through the frame's corner holes (4.2 mm holes on a 79 mm circle, a 55.9 mm square pattern) thread into M4 heat-set inserts in bosses behind the baffle.
- The tweeter faceplate drops into a 33 mm counterbore (3 mm deep) so it is flush with the recess floor, and is held with a thin bead of silicone or a ring of VHB tape. The ND16FA-6 has no screw holes.
- **Grille ring:** a separate 4.5 mm thick printed frame that sits in the recess, flush with the front face. Its opening is one smooth shape that wraps both drivers (a 64 mm circle over the woofer blending into a 30 mm circle over the tweeter). One piece of speaker cloth is hot-glued to its back in a 0.6 mm deep land 5 mm wide around the opening.
- **Magnets:** four 6 x 3 mm disc magnets in the back of the ring meet four in the recess floor: two beside the woofer at the left end, two beside the tweeter at the right end, all outside the driver frames. Glue them in with matched polarity (mark one face of each magnet before gluing, and test-fit the ring before the glue sets).
- A small pry notch at the bottom edge of the recess lets you get a fingernail behind the ring to pull it off.
- Speaker cloth: thin, acoustically transparent grille cloth. Stretch it tight before gluing so it does not buzz.

#### 3.4.3 Electronics

Same as the standard endpoint unless noted.

- **MCU:** ESP32-S3-DevKitC-1 (N8R8). Wi-Fi, since the tabletop unit has no Ethernet. The DevKitC has no mounting holes, so it sits on ledges in a tray with snap lips.
- **Amps:** two MAX98357A breakouts on one I2S bus. The SD pin selects the channel on each board: one plays the left slot (woofer), the other the right slot (tweeter). Both sit on trays at the front of the bay. Speaker leads run through a small pass-through in the separator wall, then along the floor of leg 1 to the drivers. Seal the pass-through with hot glue or silicone after wiring.
- **Tweeter protection:** a 10 to 22 uF film capacitor in series with the tweeter. The software crossover normally keeps bass out of the tweeter, but this blocks it in hardware too, in case of a firmware fault, a turn-on thump, or a bad filter setting. Size it so its corner is well below the crossover (about 1 to 1.5 kHz with the 6 ohm tweeter).
- **Mic:** INMP441 module, sealed to a 2.6 mm front port with a foam gasket, held in slide rails. Powered through the mic privacy circuit in 3.1.1 (PTT and the mute latch, both in hardware).
- **Buttons:** four separate printed button caps in openings in the lid, over the electronics bay. Each cap moves; nothing about the lid flexes.

| Button | Cap size | Center (x, y from front-left) | Cap top mark |
|---|---|---|---|
| TALK | 40 x 24 mm | (218.6, 26.0) | shallow dish, about 11 mm across |
| VOL - | 18 x 14 mm | (206.1, 58.0) | engraved minus |
| VOL + | 18 x 14 mm | (231.1, 58.0) | engraved plus |
| MIC MUTE | 24 x 12 mm | (218.6, 86.0) | engraved ring with a slash |

  - TALK is nearest the front edge and largest. MIC MUTE is at the back, set apart so it is not hit by accident.
  - Stack, top to bottom: cap top 0.6 mm above the lid surface; cap body through the 3 mm lid and a 4 mm guide collar (0.3 mm clearance per side, chamfered opening at the top); a 1.5 mm retaining flange under the collar; a 4 mm stem that rests 0.05 mm above the tact switch actuator.
  - The tact switch is the return spring. At rest the switch pushes the cap up until the flange meets the collar. Pressing moves the cap about 0.3 mm to the click.
  - Caps drop into the openings from below before the button board is installed, so they are captive with no visible fasteners.
  - Button board: perfboard about 54 x 86 mm on four 10.25 mm lid standoffs (M2 holes at 49 mm across, rows at y = 15.5 and 94.0 mm). Switch actuator tops must sit at 75.75 mm above the bottom of the base, which the standoff length sets for a 5.0 mm tall switch. Switch positions on the board match the cap centers above.
  - If the switches in hand are a different height, change `SWITCH_H` in the generator and re-run; the standoff length follows.
- **Audio processing (on the ESP32-S3):** the decoded stream is processed per sample block before it goes to the I2S amps:

```
Snapcast stereo -> mono downmix -+-> room/driver EQ (parametric) -> crossover, LR4 at about 4.5 kHz
Intercom Opus  -> ducking mix   -+       |                                  |
                                          woofer: high-pass 80-90 Hz,      tweeter: level trim (about -3 dB),
                                          volume-dependent bass boost,     small delay for time alignment
                                          limiter                          (about 2 samples at 48 kHz)
                                          -> I2S left slot (woofer amp)    -> I2S right slot (tweeter amp)
```

  - Crossover: 4th-order Linkwitz-Riley at about 4.5 kHz, a little over twice the tweeter's 2125 Hz resonance. The woofer is still clean there (it runs to 13 kHz).
  - Level: the tweeter is about 3 dB more sensitive than the woofer, so it is trimmed down.
  - Bass boost tracks volume (more boost at low volume, backing off as volume rises) and the limiter keeps the woofer inside its 4 mm excursion. This is the same approach that makes small commercial smart speakers sound bigger than they are.
  - All settings are biquad coefficients stored in flash and adjustable over MQTT, so the endpoint can be tuned after it is built.
  - Tuning method: measure each driver in the finished box with a measurement mic (for example a miniDSP UMIK-1 with the free REW software), set the EQ and crossover from the measurements, and save the result as the endpoint's profile.
  - CPU: about 20 biquads at 48 kHz is a small load for the S3 using Espressif's esp-dsp library.
- **Light bar:** a 22 x 3.5 mm thin-skin slot (0.6 mm left) in the front face, with a small printed light box behind it so the LEDs do not light up the inside of the bay. The red element glows steadily while the mic is muted, driven by hardware. Green is firmware status (3.1.1). Nothing shows when the LEDs are off.

#### 3.4.4 Power, battery backup, and hum

**Power path**

```
USB-C 5 V in -> power-path Li-ion charger -> 1S 18650 cell
                        |
                        +-> system rail (3.6-4.4 V) -> 5 V synchronous boost (2 A class) -> ESP32-S3 5V pin, MAX98357A VDD
```

- The charger must be a **power-path (load sharing)** type, such as a TI BQ24074-based board. With power path, the system runs from USB when it is present and from the battery the instant it is not, with no switchover gap and no reboot. Avoid cheap "power bank" modules (IP5306 class): many shut off at light load or glitch during switchover.
- Boost to 5 V so the amp keeps its full output on battery. Size it for the amp's peak current (about 0.8 A into 4 ohms at full output) plus the ESP32's Wi-Fi peaks.
- Sense lines to the ESP32: USB present (VBUS through a divider) and battery voltage (ADC through a divider).

**Runtime**

| Case | System draw | Runtime on one 2500 mAh 18650 (about 9 Wh, 85 percent boost efficiency) |
|---|---|---|
| Idle on Wi-Fi, no audio | about 0.5 W | about 15 hours |
| Background music | about 1.0 W | about 7 hours |
| Loud, continuous | about 2.5 W | about 3 hours |

The 10 to 15 minute requirement is met with a large margin. A smaller LiPo pouch would also meet it, but an 18650 costs about the same and gives hours.

**Behavior on power loss**

- Endpoint reports `on_battery` over MQTT and keeps running.
- Optional: cap music volume while on battery to stretch runtime. Intercom and alerts stay at normal volume.
- Below a low-battery threshold, report `battery_low`, then shut down cleanly before the charger's cutoff.
- The endpoint staying up is only useful if the Wi-Fi access point, switch, and Pi controller are on a UPS too. Plan that as part of this feature.

**Hum and isolation**

- The audio path is digital all the way to the amp (I2S into the MAX98357A), so there is no analog line for 60 Hz to couple into.
- A USB-C wall charger is already galvanically isolated from the AC line. No extra isolation stage is needed.
- Hum in small powered speakers usually comes from one of three things, and this design avoids each:
  - **Ground loops:** need two grounded connections with an analog link between them. This unit has one power input and no analog audio connections.
  - **Noisy chargers:** cheap chargers leak switching and common-mode noise. Use a UL-listed, two-prong (Class II) charger from a known brand. The battery-buffered power path also smooths what gets through.
  - **Supply ripple at the amp:** add a ferrite bead and a 470 uF low-ESR capacitor at the amp's VDD, run a star ground, keep the boost converter away from the speaker leads, and keep the speaker leads short and twisted.

#### 3.4.5 Enclosure and printing (Bambu Lab A1)

**Parts**

| Part | Print orientation | Supports | Notes |
|---|---|---|---|
| `base.stl` | Floor on the bed, open side up | None | Line walls, separator wall, trays, rails, bosses all print vertically. Grille holes are diamond-shaped so they self-support. |
| `lid.stl` | Top face on the bed | None | Grooves, lip, standoffs, guide collars, and the six 75 mm pillars point up. |
| `button_caps.stl` | Cap tops on the bed (all four on one plate) | None | Touch marks print on the smooth bed side. The flange underside is a 45 degree chamfer, so it needs no support. |
| `grille_ring.stl` | Front face on the bed | None | Magnet pockets and the cloth land face up. |

All parts fit the A1's 256 x 256 mm bed. The base (250 x 173 mm) is the largest; leave the bed's default margins and center it.

**Material and settings**

- **PETG.** The A1 is an open-frame printer, so ASA and ABS will warp at this size.
- 0.4 mm nozzle, 0.2 mm layers. The 2.4 mm walls print as solid perimeters; set wall loops high enough (6 at 0.42 mm line width) that the walls have no infill gaps, which keeps them stiff and acoustically dead.
- Base: confirm in the slicer preview that the 0.6 mm light bar skin is solid.
- Caps: test-fit one cap in its opening before printing the full lid. If it binds, raise `CAP_CLEAR`; if it rattles, lower it.
- Lid pillars are 75 mm tall and 9 mm across. They print fine in PETG on the A1, but slow the outer walls a little for the top half of the pillars if they wobble, since the bed moves under them.
- Expect roughly 450 to 500 g of PETG for the base and about 190 g for the lid.
- Print one cap and a small test piece of the lid (one opening with its collar, one pillar end) to check cap fit and insert fit before committing to the full lid.

**Hardware**

| Item | Qty | Use |
|---|---|---|
| M3 heat-set insert, 4.0 mm bore, 6 mm deep | 6 | Ends of the lid pillars |
| M3 x 8 socket head screw | 6 | Up through the bottom into the pillars (counterbored, heads sit below the surface) |
| Dayton Audio ND16FA-6 tweeter | 1 | Beside the woofer |
| MAX98357A breakout (second) | 1 | Tweeter channel |
| 10 to 22 uF film capacitor | 1 | In series with the tweeter |
| M4 heat-set insert, 5.6 mm bore, 6 mm deep | 4 | Driver mounting bosses behind the baffle |
| M4 x 10 pan or button head screw | 4 | Driver, through the frame corner holes |
| 6 x 3 mm neodymium disc magnet | 8 | Grille ring (4) and recess floor (4) |
| Acoustic grille cloth, about 120 x 70 mm | 1 | Hot-glued to the back of the grille ring |
| M2 x 5 self-tapping screw | 4 | Button perfboard to lid standoffs |
| 12 mm self-adhesive bumper feet | 4 | Foot rings in the bottom (0.8 mm deep seats) |
| 6x6 mm tact switch | 4 | TALK, VOL -, VOL +, MIC MUTE |
| Foam gasket tape (1 mm) | 1 | Under the driver frame, and the mic port |
| Polyfill | a few grams | Line damping |
| Small zip ties | 2 | Battery holder strap |

**Assembly order**

1. Install heat-set inserts: 6 x M3 in the lid pillar ends, 4 x M4 in the driver bosses.
2. Glue the magnets into the recess floor and the grille ring (matched polarity). Glue the cloth to the ring.
3. Run the speaker leads from the bay through the pass-through and out the driver cutout. Solder them to the woofer, put gasket tape on the frame, and screw it in from the front. Wire the tweeter (with its series capacitor) and seat it in its counterbore with silicone or VHB.
4. Seal the pass-through.
5. Add polyfill to the closed end and leg 1.
6. Fit the amp, ESP32, charger, battery holder, USB-C breakout, mic module, and LED.
7. Turn the lid over, drop the four caps into their openings, and screw the button board onto the standoffs. The board holds the caps in.
8. Run silicone or foam tape in the lid grooves, set the lid on (the pillars drop into the floor sockets), flip the unit, and drive the six screws up through the bottom.
9. Stick the four bumper feet in the foot rings, and press the grille ring into the recess.
10. Before closing: continuity-check that no ESP32 GPIO connects to the mute latch inputs or either mic load switch enable.

#### 3.4.6 Open items

- **Mic privacy board:** lay out the latch, series load switches, Ioff buffer, and LED driver on the button board or a small daughterboard, and confirm the power-up-muted behavior.
- **Verify against parts in hand:** CE70PR-4 frame thickness (counterbore is 3.0 mm) and basket diameter at the baffle (cutout is 64 mm; the spec sheet shows 60 to 63.8); ND16FA-6 faceplate thickness (counterbore is 3.0 mm); INMP441 board width and thickness; 18650 holder footprint (pocket is 21.1 x 78.1 mm); tact switch height (board standoffs assume 5.0 mm); USB-C breakout board width (frame is 15 mm).
- **Charger and boost:** pick specific boards and update the tray size (charger tray is 26 x 22 mm).
- **Measure the line:** in-box frequency response near field at the driver and at the mouth, then adjust stuffing and taper.
- **Tuning range:** the line is about 115 Hz in a box that fits the A1 bed. Going lower needs a fifth leg (deeper box) or a printer with a bigger bed.

**Source:** `tabletop_endpoint.py` generates all four STLs. Every dimension above is a named parameter at the top of the script.

---

## 4. Audio and sync model

- Music: Snapcast. All clients play the same stream with synchronized timing. Snapcast buffer latency is accepted for music.
- Intercom: separate low-latency multicast Opus stream. Not synchronized across rooms; latency matters more than tight sync for voice.
- Ducking and mixing happen on each endpoint, so music and intercom are independent at the server.
- Alarms and announcements: played as a Snapserver stream (synchronized) with a system volume override.

## 5. Mechanical design notes for HiFi endpoints

- Pi and amp HAT mounted in a low-voltage location (closet, media cabinet, or ventilated in-wall enclosure) with speaker wire run to the speakers.
- Ventilation required for the amp HAT under sustained load.
- Use in-wall-rated (CL2 or CL3) speaker wire for any run inside walls.

## 6. Software architecture summary

| Component | Runs on | Purpose |
|---|---|---|
| Snapserver | Pi 5 | Synchronized music |
| Intercom server | Pi 5 | PTT arbitration and Opus relay |
| Mosquitto | Pi 5 | Authenticated endpoint control |
| Web app (Flask/FastAPI) | Pi 5 | UI, schedules, API |
| Scheduler | Pi 5 | Alarms and announcements |
| Standard endpoint firmware | ESP32-S3 | Playback, mix, duck, PTT capture, controls |
| Same firmware, plus battery/USB-present reporting | ESP32-S3 (tabletop) | As above, on Wi-Fi with battery backup |
| Snapclient + intercom client | HiFi endpoints | Playback and optional paging |
| Remote intercom gateway (Pion or aiortc) | Pi 5 | WebRTC to phones, bridged to the house intercom (2.3) |
| Rendezvous server (signaling, coturn, push) | Cloud VPS | Connects phones and the Pi; sees only encrypted media (2.3) |
| Intercom app (Swift, WebRTC, PushToTalk) | iPhone | Remote paging and hearing pages (2.3) |

## 7. Future extensions

- Room-to-room calls (direct routing instead of all-call).
- Home Assistant integration through MQTT.
- Doorbell and alert integration (play chime and TTS to all rooms).
- Per-room source selection (different music in different zones).
- RGB LED status for additional states.
