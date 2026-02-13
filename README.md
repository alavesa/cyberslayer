# CyberSlayer

A DOOM-inspired cybersecurity combat game for the [Disobey 2026 Badge](https://github.com/disobeyfi/disobey-badge-2025-game-firmware).

Rip and tear through a corporate network — from Guest WiFi to Core Router. Built in MicroPython on an ESP32-S3 with 512KB RAM.

> Work in progress. It runs on my badge and that's what counts.

![20260213_032423](https://github.com/user-attachments/assets/0ebe9071-0708-4f24-a75b-b5a79e69c819)

## Gameplay

You breach a corporate network across 10 zones. Each zone has a different cyber threat with unique abilities. Pick the right weapon, exploit weaknesses, manage your ammo, and survive.

### Weapons

| Weapon | Damage | Ammo | Description |
|--------|--------|------|-------------|
| Ping | 8 | Unlimited | Basic attack — trace the network |
| Nmap | 15 | Limited | Port scanner — resupplied between levels |
| Metasploit | 30 | Rare | Exploit framework — powerful but scarce |

Hit an enemy's weakness for **2x critical damage**.

### Enemies

| Zone | Enemy | HP | Special Ability |
|------|-------|----|-----------------|
| Guest WiFi | Script Kiddie | 12 | — |
| DMZ | Trojan | 20 | — |
| Web Server | Worm | 25 | Replicates every 3 turns |
| Email Gateway | Phisher | 22 | — |
| File Server | Ransomware | 35 | Encrypts your weapons (halves damage) |
| Active Directory | Rootkit | 38 | — |
| Database | SQLi Worm | 32 | Replicates every 3 turns |
| SCADA | Zero-Day | 35 | — |
| C-Suite | Social Engineer | 28 | Encrypts your weapons |
| Core Router | APT | 55 | Adapts to repeated attacks |

### Ranks

Earn ranks based on your best level reached:

| Level | Rank |
|-------|------|
| 0 | Script Kiddie |
| 2 | Packet Pusher |
| 4 | Shell Jockey |
| 6 | Root Rider |
| 8 | Zero-Day Hunter |
| 10 | Digital Oracle |

### Between Levels

- HP heals (scales with level)
- Nmap ammo resupplied (+2)
- Metasploit ammo at select levels
- Shield granted at select levels

### LEDs

The badge's NeoPixel LEDs track your progress:
- Each cleared zone lights up a green LED
- Combat flashes red on hit
- Victory: rainbow cascade
- Defeat: red flash then fade to dark

## Hardware

- **Badge**: Disobey 2025 Badge
- **MCU**: ESP32-S3 WROOM-2 (240 MHz, 512KB RAM)
- **Display**: 1.9" TFT 320x170 (ST7789)
- **LEDs**: 8x SK6812MINI NeoPixel
- **Input**: 3-button navigation (left/right/select)
- **Framework**: [micropython-micro-gui](https://github.com/peterhinch/micropython-micro-gui)

## Deploy to Badge

### Prerequisites

Flash the [Disobey 2025 Badge firmware](https://github.com/disobeyfi/disobey-badge-2025-game-firmware) to your badge first.

### Install via mpremote

Connect the badge via USB, then from this repo:

```bash
# Create directories
mpremote mkdir :badge
mpremote mkdir :badge/games

# Copy files
mpremote cp boot.py :boot.py
mpremote cp main.py :main.py
mpremote cp badge/__init__.py :badge/__init__.py
mpremote cp badge/games/__init__.py :badge/games/__init__.py
mpremote cp badge/games/cyberslayer.py :badge/games/cyberslayer.py

# Reset badge
mpremote reset
```

CyberSlayer launches automatically on boot.

### Development mode

If using the badge firmware repo with `make repl_with_firmware_dir`:

```python
>>> from bdg.repl_helpers import load_app
>>> load_app("badge.games.cyberslayer", "SlayerIntro")
```

## File Structure

```
boot.py                         # Standalone launcher
main.py                         # Dev mode launcher
badge/
  __init__.py
  games/
    __init__.py
    cyberslayer.py               # The game
```

## Acknowledgments

- Paula Alavesa and Eija Alavesa
- [Disobey](https://disobey.fi/) badge team
- [micropython-micro-gui](https://github.com/peterhinch/micropython-micro-gui) by Peter Hinch
