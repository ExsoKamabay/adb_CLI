#!/usr/bin/env python3
"""
ADB Pairing CLI - Cross-platform tool to pair and control Android devices.

Fitur:
1. List devices
2. Start ADB server
3. Stop ADB server
4. Pair device
5. Connect device
6. Enable tcpip
7. Open shell
8. Run command
9. Install APK
10. Push file
11. Pull file
12. Reboot
13. Disconnect
14. Help
15. try screen mirroring (scrcpy)
"""

import os
import sys
import subprocess
import platform
import shlex
from pathlib import Path
from typing import Optional, Tuple
from shutil import which

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

console = Console()
APP_ROOT = Path.home() / ".adb_cli"


# ---------------------------
# Utility
# ---------------------------
def run_adb(args: list[str], capture_output=True) -> Tuple[int, str, str]:
    adb = which_adb()
    cmd = [adb] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        raise FileNotFoundError("ADB tidak ditemukan. Pastikan adb terpasang atau unduh otomatis.")
    except Exception as e:
        return 1, "", str(e)


def get_os_tag() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    elif system == "darwin":
        return "darwin"
    elif system == "linux":
        return "linux"
    return system


def which_adb() -> str:
    exe = "adb.exe" if os.name == "nt" else "adb"
    found = which(exe)
    if found:
        return found
    adb_dir = APP_ROOT / "platform-tools"
    adb_path = adb_dir / exe
    if adb_path.exists():
        return str(adb_path)
    return exe


def ensure_adb():
    exe = which_adb()
    if which(exe):
        return exe
    adb_dir = APP_ROOT / "platform-tools"
    adb_path = adb_dir / ("adb.exe" if os.name == "nt" else "adb")
    if adb_path.exists():
        return str(adb_path)
    console.print("[yellow]ADB tidak ditemukan. Silakan pasang manual (platform-tools).[/yellow]")
    return exe


# ---------------------------
# ADB Actions
# ---------------------------
def list_devices():
    rc, out, err = run_adb(["devices", "-l"])
    if rc == 0:
        table = Table(title="ADB Devices")
        table.add_column("Serial")
        table.add_column("Info")
        lines = out.splitlines()
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(maxsplit=1)
            serial = parts[0]
            info = parts[1] if len(parts) > 1 else ""
            table.add_row(serial, info)
        console.print(table)
    else:
        console.print(f"[red]Error: {err or out}[/red]")


def start_server():
    rc, out, err = run_adb(["start-server"])
    console.print(f"[green]{out or 'Server started'}[/green]" if rc == 0 else f"[red]{err}[/red]")


def stop_server():
    rc, out, err = run_adb(["kill-server"])
    console.print(f"[green]{out or 'Server stopped'}[/green]" if rc == 0 else f"[red]{err}[/red]")


def _pick_serial_interactive() -> Optional[str]:
    rc, out, err = run_adb(["devices"])
    if rc != 0:
        console.print(f"[red]Error: {err or out}[/red]")
        return None
    lines = out.splitlines()[1:]
    serials = [line.split()[0] for line in lines if line.strip() and "device" in line]
    if not serials:
        console.print("[red]Tidak ada device tersedia.[/red]")
        return None
    if len(serials) == 1:
        return serials[0]
    for idx, s in enumerate(serials, start=1):
        console.print(f"{idx}. {s}")
    choice = Prompt.ask("Pilih device", default="1")
    try:
        return serials[int(choice) - 1]
    except Exception:
        return serials[0]


def pair_device():
    hostport = Prompt.ask("Masukkan ip:port untuk pair (contoh 192.168.0.5:37099)")
    pin = Prompt.ask("Masukkan kode PIN")
    rc, out, err = run_adb(["pair", hostport, pin])
    if rc == 0 and "Successfully" in out:
        console.print(f"[green]{out}[/green]")
        host = hostport.split(":")[0]
        rc2, out2, err2 = run_adb(["connect", f"{host}:5555"])
        if rc2 == 0:
            console.print(f"[green]{out2}[/green]")
        else:
            console.print(f"[yellow]Pair ok, tapi connect gagal:[/yellow] {err2 or out2}")
    else:
        console.print(f"[red]Pair gagal:[/red] {err or out}")


def connect_device():
    hostport = Prompt.ask("Masukkan host/IP:port")
    rc, out, err = run_adb(["connect", hostport])
    if rc == 0:
        console.print(f"[green]{out}[/green]")
    else:
        console.print(f"[red]Connect gagal:[/red] {err or out}")


def enable_tcpip():
    port = Prompt.ask("Masukkan port tcpip (default 5555)", default="5555")
    rc, out, err = run_adb(["tcpip", port])
    if rc == 0:
        console.print(f"[green]{out}[/green]")
    else:
        console.print(f"[red]Gagal set tcpip:[/red] {err or out}")


def open_shell():
    serial = _pick_serial_interactive()
    if not serial:
        return
    console.print(f"[green]Opening interactive shell to {serial}. Ketik 'exit' untuk keluar.[/green]")
    adb = which_adb()
    try:
        subprocess.run([adb, "-s", serial, "shell"])
    except KeyboardInterrupt:
        console.print("\n[yellow]Shell interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting shell:[/red] {e}")


def run_command_on_device():
    serial = _pick_serial_interactive()
    if not serial:
        return
    command = Prompt.ask("Masukkan perintah shell (contoh: ls /sdcard)")
    if not command:
        console.print("[red]Perintah kosong.[/red]")
        return
    args = shlex.split(command)
    rc, out, err = run_adb(["-s", serial, "shell"] + args)
    if rc == 0:
        console.print(Panel(Text(out or "(no output)"), title="Output", border_style="green"))
    else:
        console.print(f"[red]Error:[/red] {err or out}")


def install_apk():
    apk_path = Prompt.ask("Masukkan path ke file APK (lokal)")
    if not apk_path or not os.path.isfile(apk_path):
        console.print("[red]File APK tidak ditemukan.[/red]")
        return
    serial = _pick_serial_interactive()
    if not serial:
        return
    console.print(f"[green]Installing {apk_path} to {serial} ...[/green]")
    rc, out, err = run_adb(["-s", serial, "install", "-r", apk_path])
    if rc == 0:
        console.print(f"[green]Install success:[/green]\n{out}")
    else:
        console.print(f"[red]Install failed:[/red] {err or out}")


def push_file():
    src = Prompt.ask("Path file sumber (PC)")
    if not src or not os.path.exists(src):
        console.print("[red]File sumber tidak ditemukan.[/red]")
        return
    dst = Prompt.ask("Path tujuan di device (contoh: /sdcard/Download/)")
    serial = _pick_serial_interactive()
    if not serial:
        return
    console.print(f"[green]Pushing {src} -> {serial}:{dst}[/green]")
    rc, out, err = run_adb(["-s", serial, "push", src, dst])
    if rc == 0:
        console.print(f"[green]Push success:[/green]\n{out}")
    else:
        console.print(f"[red]Push failed:[/red] {err or out}")


def pull_file():
    remote = Prompt.ask("Path file di device (contoh: /sdcard/Download/file.txt)")
    if not remote:
        console.print("[red]Path remote kosong.[/red]")
        return
    dst = Prompt.ask("Path tujuan di PC (lokal)")
    if not dst:
        console.print("[red]Path tujuan kosong.[/red]")
        return
    serial = _pick_serial_interactive()
    if not serial:
        return
    console.print(f"[green]Pulling {serial}:{remote} -> {dst}[/green]")
    rc, out, err = run_adb(["-s", serial, "pull", remote, dst])
    if rc == 0:
        console.print(f"[green]Pull success:[/green]\n{out}")
    else:
        console.print(f"[red]Pull failed:[/red] {err or out}")


def reboot_device():
    serial = _pick_serial_interactive()
    if not serial:
        return
    mode = Prompt.ask("Mode reboot? (normal/bootloader/recovery)", default="normal")
    args = ["-s", serial, "reboot"]
    if mode and mode != "normal":
        args.append(mode)
    rc, out, err = run_adb(args)
    if rc == 0:
        console.print("[green]Reboot command sent.[/green]")
    else:
        console.print(f"[red]Reboot failed:[/red] {err or out}")


def disconnect_device():
    host = Prompt.ask("Masukkan host/IP:port untuk disconnect (atau kosong untuk all)", default="")
    if host:
        rc, out, err = run_adb(["disconnect", host])
    else:
        rc, out, err = run_adb(["disconnect"])
    if rc == 0:
        console.print(f"[green]{out or 'Disconnected.'}[/green]")
    else:
        console.print(f"[red]Disconnect failed:[/red] {err or out}")


def show_help():
    help_text = """
[bold cyan]Panduan Penggunaan Menu ADB[/bold cyan]

1. List devices -> adb devices -l
2. Start ADB server -> adb start-server
3. Stop ADB server -> adb kill-server
4. Pair device -> adb pair <ip:port> <PIN>, lalu script mencoba connect otomatis ke ip:5555
5. Connect device -> adb connect <ip:port>
6. Enable tcpip -> adb tcpip 5555
7. Open shell -> adb -s <serial> shell
8. Run command -> adb -s <serial> shell <cmd>
9. Install APK -> adb -s <serial> install -r app.apk
10. Push file -> adb -s <serial> push <src> <dst>
11. Pull file -> adb -s <serial> pull <remote> <local>
12. Reboot -> adb -s <serial> reboot [bootloader|recovery]
13. Disconnect -> adb disconnect [<ip:port>|all]
14. try screen mirroring -> jalankan scrcpy untuk mirror layar device
"""
    console.print(Panel(Text(help_text), title="Help Menu", border_style="blue"))


# ---------------------------
# Scrcpy helper
# ---------------------------
def ensure_scrcpy() -> Optional[str]:
    exe = "scrcpy.exe" if os.name == "nt" else "scrcpy"

    # cek PATH
    found = which(exe)
    if found:
        return found

    # cek cache folder lokal
    scrcpy_dir = APP_ROOT / "scrcpy"
    if os.name == "nt":
        exe_path = scrcpy_dir / "scrcpy-win64-v2.7" / "scrcpy.exe"
    else:
        exe_path = scrcpy_dir / "scrcpy"
    if exe_path.exists():
        return str(exe_path)

    # download/install jika tidak ada
    console.print("[yellow]scrcpy tidak ditemukan, mencoba menginstall...[/yellow]")
    os_tag = get_os_tag()
    scrcpy_dir.mkdir(parents=True, exist_ok=True)

    if os_tag == "windows":
        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-win64-v2.7.zip"
        import requests, zipfile
        zip_path = scrcpy_dir / "scrcpy.zip"
        console.print("[cyan]Mengunduh scrcpy untuk Windows...[/cyan]")
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        f.write(chunk)
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(scrcpy_dir)
            exe_path = scrcpy_dir / "scrcpy-win64-v2.7" / "scrcpy.exe"
            if exe_path.exists():
                return str(exe_path)
        except Exception as e:
            console.print(f"[red]Gagal download scrcpy: {e}[/red]")
            return None

    elif os_tag == "linux":
        console.print("[cyan]Mencoba install scrcpy via apt...[/cyan]")
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y", "scrcpy"], check=True)
            return which("scrcpy")
        except Exception as e:
            console.print(f"[red]Gagal install scrcpy di Linux: {e}[/red]")
            return None

    elif os_tag == "darwin":
        console.print("[cyan]Mencoba install scrcpy via brew...[/cyan]")
        try:
            subprocess.run(["brew", "install", "scrcpy"], check=True)
            return which("scrcpy")
        except Exception as e:
            console.print(f"[red]Gagal install scrcpy di macOS: {e}[/red]")
            return None

    return None


def try_screen_mirroring():
    scrcpy_path = ensure_scrcpy()
    if not scrcpy_path:
        console.print("[red]scrcpy tidak tersedia.[/red]")
        return

    # cek device ADB
    rc, out, _ = run_adb(["devices"])
    lines = out.splitlines()[1:]
    devices = [line for line in lines if "device" in line and not line.startswith("*")]
    if not devices:
        console.print("[red]Tidak ada device ADB terhubung.[/red]")
        return

    console.print("[green]Menjalankan scrcpy...[/green]")
    try:
        subprocess.run([scrcpy_path])
    except Exception as e:
        console.print(f"[red]Gagal menjalankan scrcpy: {e}[/red]")


# ---------------------------
# Menu & Main Loop
# ---------------------------
def show_menu():
    table = Table(title="[green]ADB Pairing CLI[/green]", show_header=False,highlight=True,width=50,expand=True)
    options = [
        ("[cyan]1[/cyan]", "List devices"),
        ("[cyan]2[/cyan]", "Start ADB server"),
        ("[cyan]3[/cyan]", "Stop ADB server"),
        ("[cyan]4[/cyan]", "Pair device"),
        ("[cyan]5[/cyan]", "Connect device"),
        ("[cyan]6[/cyan]", "Enable tcpip"),
        ("[cyan]7[/cyan]", "Open shell"),
        ("[cyan]8[/cyan]", "Run command"),
        ("[cyan]9[/cyan]", "Install APK"),
        ("[cyan]10[/cyan]", "Push file"),
        ("[cyan]11[/cyan]", "Pull file"),
        ("[cyan]12[/cyan]", "Reboot device"),
        ("[cyan]13[/cyan]", "Disconnect device"),
        ("[cyan]14[/cyan]", "try screen mirroring"),
        ("[cyan]15[/cyan]", "[cyan]Help[/cyan]"),
        ("[cyan]0[/cyan]", "[bold red]Exit[/bold red]"),
    ]
    for no, desc in options:
        table.add_row(no, desc)
    console.print(table)



def main_loop():
    ensure_adb()
    while True:
        console.clear()
        show_menu()
        choice = Prompt.ask("\n[bold]Pilih nomor aksi[/bold]", default="1")
        try:
            if choice == "1":
                list_devices()
            elif choice == "2":
                start_server()
            elif choice == "3":
                stop_server()
            elif choice == "4":
                pair_device()
            elif choice == "5":
                connect_device()
            elif choice == "6":
                enable_tcpip()
            elif choice == "7":
                open_shell()
            elif choice == "8":
                run_command_on_device()
            elif choice == "9":
                install_apk()
            elif choice == "10":
                push_file()
            elif choice == "11":
                pull_file()
            elif choice == "12":
                reboot_device()
            elif choice == "13":
                disconnect_device()
            elif choice == "14":
                try_screen_mirroring()
            elif choice == "15":
                show_help()
            elif choice == "0":
                if Confirm.ask("Yakin mau keluar?"):
                    console.print("[bold]Sampai jumpa![/bold]")
                    break
            else:
                console.print("[red]Pilihan tidak dikenal.[/red]")
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Dibatalkan oleh user.[/yellow]")
            break

        console.print("\n[dim]Tekan Enter untuk kembali ke menu...[/dim]")
        try:
            input()
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Keluar.[/yellow]")
            break


if __name__ == "__main__":
    main_loop()
