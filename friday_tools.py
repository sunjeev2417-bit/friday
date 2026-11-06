import os
import subprocess
import webbrowser
import platform
import psutil
from pathlib import Path
from urllib.parse import quote_plus

# Prime psutil CPU measurement once at startup for non-blocking readings
psutil.cpu_percent(interval=None)


APP_COMMANDS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "settings": "ms-settings:",

    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
}
def open_app(name):
    name = name.lower().strip()

    command = APP_COMMANDS.get(name)

    if not command:
        return f"I don't have a safe launch command for {name}, boss."

    try:
        if command.endswith(":"):
            os.startfile(command)
        else:
            subprocess.Popen(command, shell=True)

        return f"Opening {name}, boss."

    except Exception as e:
        return f"I couldn't open {name}: {e}"


def open_website(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        webbrowser.open(url)
        return f"Opening {url}, boss."

    except Exception as e:
        return f"I couldn't open that website: {e}"


def web_search(query):
    try:
        url = "https://www.google.com/search?q=" + quote_plus(query)
        webbrowser.open(url)
        return f"Searching the web for {query}, boss."

    except Exception as e:
        return f"I couldn't perform the search: {e}"
def open_special_folder(name):
    folders = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
    }

    folder = folders.get(name.lower().strip())

    if not folder:
        return f"I don't know that Windows folder, boss."

    try:
        if not folder.exists():
            return f"I couldn't find your {name} folder, boss."

        os.startfile(str(folder))
        return f"Opening {name}, boss."

    except Exception as e:
        return f"I couldn't open {name}: {e}"


def open_folder(path):
    try:
        folder = Path(path).expanduser().resolve()

        if not folder.exists():
            return f"I couldn't find that folder, boss."

        os.startfile(str(folder))
        return f"Opening the folder, boss."

    except Exception as e:
        return f"I couldn't open that folder: {e}"


def launch_program(command):
    try:
        subprocess.Popen(command, shell=True)
        return f"Launching it now, boss."

    except Exception as e:
        return f"I couldn't launch it: {e}"
def get_cpu_usage():
    try:
        cpu = psutil.cpu_percent(interval=None)
        return f"CPU usage is {cpu} percent, boss."
    except Exception as e:
        return f"I couldn't read CPU usage: {e}"


def get_memory_usage():
    try:
        memory = psutil.virtual_memory()

        used_gb = memory.used / (1024 ** 3)
        total_gb = memory.total / (1024 ** 3)

        return (
            f"RAM usage is {memory.percent} percent. "
            f"I'm using {used_gb:.1f} gigabytes out of "
            f"{total_gb:.1f} gigabytes, boss."
        )

    except Exception as e:
        return f"I couldn't read RAM usage: {e}"

def get_storage_usage():
    try:
        drive = Path.home().anchor or "C:\\"
        disk = psutil.disk_usage(drive)

        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)

        return (
            f"Storage usage on drive {drive} is {disk.percent} percent. "
            f"{used_gb:.1f} gigabytes used, "
            f"{free_gb:.1f} gigabytes free, "
            f"out of {total_gb:.1f} gigabytes total, boss."
        )

    except Exception as e:
        return f"I couldn't read storage usage: {e}"
def get_pc_status():
    try:
        # CPU
        cpu = psutil.cpu_percent(interval=None)

        # RAM
        memory = psutil.virtual_memory()
        ram_percent = memory.percent
        ram_used_gb = memory.used / (1024 ** 3)
        ram_total_gb = memory.total / (1024 ** 3)

        # Storage
        drive = Path.home().anchor or "C:\\"
        disk = psutil.disk_usage(drive)
        storage_percent = disk.percent
        storage_free_gb = disk.free / (1024 ** 3)
        storage_total_gb = disk.total / (1024 ** 3)

        # Battery
        battery = psutil.sensors_battery()

        if battery is not None:
            battery_text = f"{battery.percent:.0f}%"
            if battery.power_plugged:
                battery_text += " and charging"
        else:
            battery_text = "not detected"

        return (
            f"PC status, boss. "
            f"CPU is {cpu:.1f} percent. "
            f"RAM is {ram_percent:.1f} percent used "
            f"({ram_used_gb:.1f} out of {ram_total_gb:.1f} GB). "
            f"Storage is {storage_percent:.1f} percent used "
            f"with {storage_free_gb:.1f} GB free out of {storage_total_gb:.1f} GB. "
            f"Battery is {battery_text}."
        )

    except Exception as e:
        return f"I couldn't check the PC status: {e}"


def get_battery_status():
    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return "I couldn't detect a battery on this system, boss."

        percent = battery.percent

        if battery.power_plugged:
            status = "charging"
        else:
            status = "on battery"

        return f"Battery is at {percent:.0f} percent and currently {status}, boss."

    except Exception as e:
        return f"I couldn't read the battery status: {e}"


def get_system_info():
    try:
        return (
            f"System: {platform.system()} {platform.release()}. "
            f"Machine: {platform.machine()}. "
            f"Processor: {platform.processor()}, boss."
        )

    except Exception as e:
        return f"I couldn't read system information: {e}"


# =========================
# SYSTEM CONTROLS
# =========================

def set_volume_up():
    try:
        import ctypes

        # Increase Windows master volume
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)

        return "Volume increased, boss."

    except Exception as e:
        return f"I couldn't increase the volume: {e}"


def set_volume_down():
    try:
        import ctypes

        # Decrease Windows master volume
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)

        return "Volume decreased, boss."

    except Exception as e:
        return f"I couldn't decrease the volume: {e}"


def toggle_mute():
    try:
        import ctypes

        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)

        return "Mute toggled, boss."

    except Exception as e:
        return f"I couldn't toggle mute: {e}"


def lock_pc():
    try:
        import ctypes

        ctypes.windll.user32.LockWorkStation()

        return "Locking the PC, boss."

    except Exception as e:
        return f"I couldn't lock the PC: {e}"


def sleep_pc():
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Start-Sleep -Milliseconds 500; "
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.Application]::SetSuspendState("
                "'Suspend', $false, $false)"
            ],
            shell=False
        )

        return "Putting the PC to sleep, boss."

    except Exception as e:
        return f"I couldn't put the PC to sleep: {e}"


def restart_pc():
    try:
        subprocess.Popen(
            ["shutdown", "/r", "/t", "30"],
            shell=False
        )

        return (
            "Restart scheduled in 30 seconds, boss. "
            "Say cancel restart if you change your mind."
        )

    except Exception as e:
        return f"I couldn't schedule the restart: {e}"


def shutdown_pc():
    try:
        subprocess.Popen(
            ["shutdown", "/s", "/t", "30"],
            shell=False
        )

        return (
            "Shutdown scheduled in 30 seconds, boss. "
            "Say cancel shutdown if you change your mind."
        )

    except Exception as e:
        return f"I couldn't schedule the shutdown: {e}"


def cancel_shutdown():
    try:
        subprocess.Popen(
            ["shutdown", "/a"],
            shell=False
        )

        return "Shutdown or restart cancelled, boss."

    except Exception as e:
        return f"I couldn't cancel the shutdown: {e}"


def get_detailed_system_info():
    try:
        memory = psutil.virtual_memory()

        total_ram_gb = memory.total / (1024 ** 3)

        drive = Path.home().anchor or "C:\\"
        disk = psutil.disk_usage(drive)

        total_storage_gb = disk.total / (1024 ** 3)
        free_storage_gb = disk.free / (1024 ** 3)

        return (
            f"System details, boss. "
            f"Windows {platform.release()}. "
            f"Machine type is {platform.machine()}. "
            f"Processor is {platform.processor()}. "
            f"You have {total_ram_gb:.1f} GB of RAM. "
            f"Drive {drive} has {total_storage_gb:.1f} GB total "
            f"with {free_storage_gb:.1f} GB free. "
            f"Computer name is {platform.node()}."
        )

    except Exception as e:
        return f"I couldn't read the detailed system information: {e}"
def get_pc_health():
    try:
        cpu = psutil.cpu_percent(interval=None)

        memory = psutil.virtual_memory()
        ram_percent = memory.percent

        drive = Path.home().anchor or "C:\\"
        disk = psutil.disk_usage(drive)
        storage_percent = disk.percent

        battery = psutil.sensors_battery()

        # ---------------------------------------------
        # Determine CPU condition
        # ---------------------------------------------

        if cpu >= 90:
            cpu_status = "very high"
        elif cpu >= 75:
            cpu_status = "high"
        elif cpu >= 50:
            cpu_status = "moderate"
        else:
            cpu_status = "low"

        # ---------------------------------------------
        # Determine RAM condition
        # ---------------------------------------------

        if ram_percent >= 90:
            ram_status = "very high"
        elif ram_percent >= 80:
            ram_status = "high"
        elif ram_percent >= 60:
            ram_status = "moderate"
        else:
            ram_status = "normal"

        # ---------------------------------------------
        # Determine storage condition
        # ---------------------------------------------

        if storage_percent >= 90:
            storage_status = "critically full"
        elif storage_percent >= 80:
            storage_status = "getting full"
        elif storage_percent >= 70:
            storage_status = "moderately used"
        else:
            storage_status = "healthy"

        # ---------------------------------------------
        # Battery
        # ---------------------------------------------

        if battery is None:
            battery_text = "Battery was not detected."

        else:
            battery_percent = battery.percent

            if battery.power_plugged:
                battery_text = (
                    f"Battery is at {battery_percent:.0f} percent "
                    f"and charging."
                )
            else:
                battery_text = (
                    f"Battery is at {battery_percent:.0f} percent "
                    f"and running on battery."
                )

        # ---------------------------------------------
        # Overall assessment
        # ---------------------------------------------

        warnings = []

        if cpu >= 75:
            warnings.append("CPU usage is high")

        if ram_percent >= 80:
            warnings.append("RAM usage is high")

        if storage_percent >= 80:
            warnings.append("storage is getting full")

        if not warnings:
            overall = "Your PC is running normally, boss."
        else:
            overall = (
                "Your PC is running, but I noticed "
                + " and ".join(warnings)
                + ", boss."
            )

        return (
            f"{overall} "
            f"CPU usage is {cpu:.1f} percent, which is {cpu_status}. "
            f"RAM usage is {ram_percent:.1f} percent, which is {ram_status}. "
            f"Storage usage is {storage_percent:.1f} percent, "
            f"which is {storage_status}. "
            f"{battery_text}"
        )

    except Exception as e:
        return f"I couldn't analyze PC health: {e}"


if __name__ == "__main__":
    print("Friday tools: ONLINE")