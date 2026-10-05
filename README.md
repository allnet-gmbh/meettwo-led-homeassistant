# MeetTwo LED for Home Assistant

Home Assistant integration for the LED border of **MeetTwo** devices. The integration talks to the
**MeetTwo LED API** app running on the device. Everything stays in the local network; no cloud is involved.

## Features

- **Auto-discovery:** devices in the network are found automatically via Zeroconf/mDNS.
- **Light entity:** on/off, RGB color, brightness and effects
  (`blink`, `strobe`, `breathe`, `rainbow`, `cycle`, `fade`).
- **Effect speed:** a number entity for the effect speed.
- **Action `meettwo_led.set_effect`:** effects with a color list, speed and brightness, for automations.
- **Diagnostic entities:** *LED hardware* (problem sensor) and *Last error*.
- **Optional password:** supported, including re-authentication when the password changes.
- **Follows IP changes:** a new IP address is picked up automatically through discovery.
- **Reconfigure and options:** change host, port or password, and set the update interval.
- **Languages:** English and German.

## Requirements

- **Home Assistant:** 2025.2 or newer (tested with 2026.2 and 2026.9).
- **MeetTwo LED API app:** a version that provides a device id. Check that `http://<device-ip>:8080/api/help`
  contains `deviceId`.
- **Network:** Home Assistant and the MeetTwo device must be able to reach each other. Auto-discovery
  additionally needs both to be in the same network segment (multicast/mDNS).

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮), choose **Custom repositories**, add
   `https://github.com/allnet-gmbh/meettwo-led-homeassistant` and choose category **Integration**.
2. Search for **MeetTwo LED** and install it.
3. Restart Home Assistant.

### Manual

Copy `custom_components/meettwo_led` into the `custom_components` folder of your Home Assistant
configuration, so you have `<config>/custom_components/meettwo_led/manifest.json`. Then restart Home Assistant.

## Setup

**Automatically:** after the restart, Home Assistant shows **"New devices discovered: MeetTwo LED"**
under *Settings → Devices & services*. Click **Add**. If a password is set in the app, you are asked for it.

**Manually:** go to *Settings → Devices & services → Add integration → MeetTwo LED* and enter:

| Field | Description |
|---|---|
| Host | IP address of the device (shown in the MeetTwo LED API app) |
| Port | HTTP port of the app (default `8080`) |
| Password | Only if a password is set in the app |

**Device name:** the name set in the app (*Device name*) becomes the device name in Home Assistant.
With several devices, give each one a clear name, for example the room name, **before** adding it.

**Options:** under *Configure* you can change the update interval (default 10 s).
*Reconfigure* changes host, port or password.

## Entities

For a device named "Meeting Room":

| Entity | Type | Description |
|---|---|---|
| `light.meeting_room` | Light | On/off, RGB color, brightness, effects. Attributes `speed` and `colors` show the effect settings. |
| `number.meeting_room_effect_speed` | Number (config) | Effect speed in ms, 50–600000 |
| `binary_sensor.meeting_room_led_hardware` | Binary sensor (diagnostic, problem) | `on` if the LED hardware is not available or the last write failed |
| `sensor.meeting_room_last_error` | Sensor (diagnostic) | Last hardware error, empty if none |

What `speed` means depends on the effect:

| Effect | `speed` = |
|---|---|
| `blink` | full on + off period |
| `strobe` | time between flashes |
| `breathe` | full fade in + fade out |
| `rainbow` | duration of one rainbow cycle |
| `cycle` | time per color (hard switch) |
| `fade` | time per color (smooth cross-fade) |

> The LED border has 16 levels per color channel, so very similar colors or brightness values can look the same.

## Action `meettwo_led.set_effect`

`light.turn_on` can start effects, but it cannot set a color list or a speed. The integration's own
action can:

| Field | Required | Description |
|---|---|---|
| `effect` | yes | `off` (static color), `blink`, `strobe`, `breathe`, `rainbow`, `cycle`, `fade` |
| `color` | no | Base color for `blink`, `strobe` and `breathe`: a name (`red`, `darkorange`, …), `#RRGGBB` or `r,g,b` |
| `colors` | no | List of colors for `cycle` and `fade` |
| `speed` | no | Speed in ms (50–600000) |
| `brightness_pct` | no | Brightness 0–100 % |

All color names of the app can be used. Open `http://<device-ip>:8080/api/colors` to see the full list.

## Examples

**Room status from a calendar:**

```yaml
automation:
  - alias: "Meeting room busy"
    triggers:
      - trigger: state
        entity_id: calendar.meeting_room
        to: "on"
    actions:
      - action: meettwo_led.set_effect
        target:
          entity_id: light.meeting_room
        data:
          effect: breathe
          color: red
          speed: 3000
          brightness_pct: 80

  - alias: "Meeting room free"
    triggers:
      - trigger: state
        entity_id: calendar.meeting_room
        to: "off"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.meeting_room
        data:
          rgb_color: [0, 255, 0]
          brightness_pct: 60
          effect: "off"
```

**Alarm, red/blue:**

```yaml
action: meettwo_led.set_effect
target:
  entity_id: light.meeting_room
data:
  effect: cycle
  colors: [red, blue]
  speed: 300
```

**Smooth color fade:**

```yaml
action: meettwo_led.set_effect
target:
  entity_id: light.meeting_room
data:
  effect: fade
  colors: [red, "#FF8800", yellow, green, blue]
  speed: 2000
```

## Troubleshooting

| Problem | Solution |
|---|---|
| Device is not discovered | Is the MeetTwo LED API app running? Are Home Assistant and the device in the same network segment? Home Assistant in Docker needs `network_mode: host` for discovery. Otherwise add the device manually. |
| "Failed to connect" | Check IP and port in the app; open `http://<ip>:<port>/api/help` in a browser. |
| "Re-authentication required" | The password in the app was changed or removed. Enter the new one, or leave the field empty if no password is set anymore. |
| Changes made outside HA show up late | The state is polled. Lower the update interval in the options. |
| *LED hardware* reports a problem | Check the *Last error* sensor and the app on the device. |

**Debug logging:**

```yaml
logger:
  logs:
    custom_components.meettwo_led: debug
```

*Settings → Devices & services → MeetTwo LED → ⋮ → Download diagnostics* exports the device
state with the password removed.

## Development

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest
```

The API is described in the `README.md` of the Android app repository.