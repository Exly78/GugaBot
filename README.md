# GugaBot

A Discord bot for remote Windows PC monitoring and control. Built for educational purposes and learning about Windows APIs, Discord bots, and system automation.

> **Disclaimer:** This project is intended for educational use only. Only use this on machines you own or have explicit permission to access. Unauthorized use is illegal.

---

## Features

- Screenshot & webcam capture
- System info (CPU, RAM, disk)
- Process management (list, kill)
- Keyboard & mouse control (lock, type, block keys)
- Volume control & desktop notifications
- Wallpaper changer
- CPU/GPU stress test
- Audio playback
- Open URLs and applications
- Auto-update from GitHub on startup
- Persistent startup via Windows Task Scheduler

---

## Installation

1. Download `setup.bat`
2. Run it as Administrator
3. It will automatically:
   - Install Python if missing
   - Download all bot files
   - Install dependencies
   - Register a startup task
   - Launch the bot

That's it. The bot will start automatically on every login.

---

## Setup (for developers)

1. Clone the repo
2. Create a `config.txt` file:
```
YOUR_BOT_TOKEN
DISCORD_USER_ID1,DISCORD_USER_ID2
```
3. Run `encrypt.py` to generate `token.enc` and `dependencies.txt`
4. Push everything except `config.txt` to GitHub
5. Run `setup.bat` on the target machine

---

## Commands

| Command | Description |
|---|---|
| `!ping` / `/ping` | Check if bot is alive |
| `!ss` / `/ss` | Take a screenshot |
| `!cam` / `/cam` | Webcam photo |
| `!sysinfo` / `/sysinfo` | CPU, RAM, disk usage |
| `!idle` / `/idle` | How long PC has been idle |
| `!procs [filter]` / `/procs` | List running processes |
| `!clip` / `/clip` | Get clipboard contents |
| `!run <cmd>` / `/run` | Run a shell command |
| `!kill <name>` / `/kill` | Kill a process |
| `!type <text>` / `/type` | Type text via keyboard |
| `!vol <0-100>` / `/vol` | Set system volume |
| `!notify <msg>` / `/notify` | Send a desktop notification |
| `!wallpaper <url>` / `/wallpaper` | Change desktop wallpaper |
| `!lock [seconds]` / `/lock` | Block keyboard & mouse |
| `!unlock` / `/unlock` | Unblock keyboard & mouse |
| `!blockkey <key> [s]` / `/blockkey` | Block a specific key |
| `!freeze [seconds]` / `/freeze` | Max out CPU & GPU |
| `!soundboard` / `/soundboard` | Play audio file on PC |
| `!website <url>` / `/website` | Open URL in browser |
| `!stream start/stop` / `/stream` | Stream screenshots to Discord |
| `!shutdown` / `/shutdown` | Shut down the PC |
| `!reboot` / `/reboot` | Reboot the PC |
| `!startup` / `/startup` | Register startup task |
| `!update` / `/update` | Force update from GitHub |

---

## Requirements

- Windows 10/11
- Python 3.11+
- A Discord bot token ([discord.com/developers](https://discord.com/developers))

---

## Dependencies

Installed automatically by `setup.bat`:
```
discord.py psutil pillow opencv-python pyautogui sounddevice soundfile aiohttp cryptography
```

---

## License

MIT
