import argparse
import atexit
import logging
import re
import signal
import subprocess
import threading
import magic
from os import getcwd as pwd, remove
from os import path as op
from sys import exit
from time import sleep

import adbutils
import adbutils.shell
from rich.console import Console
from rich.prompt import Prompt
from rich_argparse import RichHelpFormatter

from . import Files
from . import fastboot
from . import files
from ._version import VERSION
from .utils import get_port, repartition, get_progress, logger, console

exit_counter = 0

adb: adbutils.AdbClient | None = None


def handle_sigint(*_) -> None:
    global exit_counter
    if exit_counter == 2:
        console.log("CTRL+C pressed 3 times. Exiting")
        exit(1)
    else:
        console.log(f"Press CTRL+C {2 - exit_counter} more {'time' if exit_counter == 1 else 'times'} to exit")
        exit_counter += 1


def exit_handler(*_) -> None:
    global adb
    if adb is not None:
        with console.status("[cyan]Stopping adb server", spinner="line", spinner_style="white"):
            adb.server_kill()


def main() -> int:
    global adb

    signal.signal(signal.SIGINT, handle_sigint)
    atexit.register(exit_handler)

    parser = argparse.ArgumentParser(
        description="Linux on Nabu deployer",
        formatter_class=lambda prog: RichHelpFormatter(
            prog,
            max_help_position=37
        )
    )

    parser.add_argument(
        "-v", "--version",
        help="show version and exit",
        action="store_true"
    )

    parser.add_argument(
        "-d", "--device-serial",
        help="device serial"
    )

    parser.add_argument(
        "-u", "--username",
        help="linux user name"
    )

    parser.add_argument(
        "-p", "--password",
        help="linux user password"
    )

    parser.add_argument(
        "RootFS",
        help="root fs image",
        default=None, nargs="?"
    )

    parser.add_argument(
        "-S", "--part-size",
        help="linux partition size in percents"
    )
    parser.add_argument(
        "--debug",
        help="enable debug output",
        action="store_true"
    )

    args = parser.parse_args()

    if args.version:
        console.log(f"Version: {VERSION}")
        return 0

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.RootFS:
        rootfs = op.abspath(args.RootFS)
        try:
            rootfs_magic = magic.Magic(mime=True).from_file(rootfs)
            logger.debug(f"RootFS magic: {rootfs_magic}")
            if rootfs_magic not in ["application/octet-stream", "inode/blockdevice"]:
                console.log("Invalid RootFS image")
                return 1
        except FileNotFoundError:
            console.log("RootFS image not found!")
            return 1
    else:
        console.log(parser.parse_args("-h".split()))

    while True:
        try:
            adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
            adb.make_connection()
        except adbutils.errors.AdbTimeout:
            with console.status("[cyan]Starting adb server", spinner="line", spinner_style="white"):
                try:
                    proc = subprocess.Popen("adb start-server",
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                            )
                    stdout, stderr = proc.communicate()
                except FileNotFoundError:
                    console.log("Failed to start adb server")
                    console.log("Adb binary not found in path")
                    adb = None
                    return 1
                else:
                    if proc.wait() != 0:
                        console.log("Failed to start adb server")
                        console.log(stdout)
                        adb = None
                        return 1
        else:
            break

    fb_list = fastboot.list_devices()
                fastboot.wait_for_bootloader(serial)
        if not fastboot.check_device(serial):
            fastboot.reboot(serial)
        parts_status = fastboot.check_parts(serial)
    username = args.username
    while username is None:
        username_pattern = r"^[a-z0-9](?!.*[-._?])[a-z0-9]{1,18}[a-z0-9]$"
        username = Prompt.ask("Username for linux")
        if not re.match(username_pattern, username):
            console.log("Incorrect username specified. Please set correct one")
            username = None

    password = args.password
    while password is None:
        password_pattern = r"^[a-z0-9?._-]{1,20}$"
        password = Prompt.ask(f"Password for {username}", password=True)
        if not re.match(password_pattern, password):
            console.log("Incorrect password specified. Please set correct one")
            password = None

    linux_part_size = args.part_size
    while linux_part_size is None:
        linux_part_size = Prompt.ask(
            "Size of linux partition (leave empty to skip if possible)",
            default="", show_default=False
        )
        if linux_part_size == "":
            linux_part_size = None
            break
        elif re.match(r"^\d+%$", linux_part_size) and 20 <= int(linux_part_size[:-1]) <= 90:
            break
        else:
            console.log("Incorrect linux partition size. It can be [20; 90]%")
            linux_part_size = None

    fb_list = list_fb_devices()
    adb_list = list(map(lambda x: x.serial, adb.list()))
    if args.device_serial:
        if args.device_serial in fb_list or args.device_serial in adb_list:
            serial = args.device_serial
        else:
            console.log(f"Device with serial {args.device_serial} not found")
            return 1
    elif len(fb_list) == 1 and len(adb_list) == 0:
        serial = fb_list[0]
    elif len(adb_list) == 1 and len(fb_list) == 0:
        serial = adb_list[0]
    elif len(adb_list + fb_list) == 0:
        console.log("No devices available. Please check your device connection")
        return 1
    else:
        console.log("More then one device detected. Use -d flag to set device")
        return 1

    for msg in [
        f"Username: {username}",
        f"Password: {password}",
        f"Partition size: {linux_part_size if linux_part_size else 'Not changed'}",
        f"Device: {serial}"
    ]:
        console.log(msg)

    if Prompt.ask("Is it ok?", default="n", choices=["y", "n"]) == "n":
        return 1

    if serial not in fb_list:
        console.log("ADB Device detected. Rebooting it to bootloader")
        adb.device(serial).shell("reboot bootloader")
        with console.status("[cyan]Waiting for fastboot device", spinner="line", spinner_style="white"):
            wait_for_bootloader(serial)
        console.log("Device connected")
    else:
        console.log("Device connected")

    if not check_device(serial):
        console.log("Is it nabu?")
        reboot_fb_device(serial)
        return 2

    parts_status = check_parts(serial)
    if linux_part_size:
        if Prompt.ask(
                f"Repartition {'requested' if parts_status else 'needed'}. All data will be ERASED",
                default="n", choices=["y", "n"]) == "y":
            console.log("Restoring stock partition table")
            fastboot.restore_parts(serial)
            console.log("Booting OrangeFox recovery")
            fastboot.boot_ofox(serial)
            with console.status("[cyan]Waiting for device", spinner="line", spinner_style="white"):
                try:
                    adb.wait_for(serial, state="recovery")
                except adbutils.errors.AdbTimeout():
                    console.log("Could not detect recovery device")
                    return 1
            repartition(serial, int(linux_part_size.replace("%", "")), percents=True)
            console.log("Repartition complete")
            adbutils.device(serial).shell("reboot bootloader")
            console.log("Rebooting into bootloader")
            wait_for_bootloader(serial)
            console.log("Booting OrangeFox recovery")
            boot_ofox(serial)
            with console.status("[cyan]Waiting for device", spinner="line", spinner_style="white"):
                try:
                    fastboot.wait_for_bootloader(serial)
        else:
            console.log("Repartition canceled. Exiting")
            return 1

    if not parts_status and not linux_part_size:
        console.log("Incompatible partition table detected. Repartition needed. Exiting")
        return 1

    console.log("Cleaning linux and esp")
    clean_device(serial)

    console.log("Booting OrangeFox recovery")

    boot_ofox(serial)

    with console.status("[cyan]Waiting for device", spinner="line", spinner_style="white"):
        try:
            adb.wait_for(serial, state="recovery")
        except adbutils.errors.AdbTimeout():
            console.log("Could not detect recovery device")
            return 1

    adbd = adb.device(serial)

    with console.status("[cyan]Formating EFI partition", spinner="line", spinner_style="white"):
        adbd.shell("mkfs.fat -F32 -s1 /dev/block/platform/soc/1d84000.ufshc/by-name/esp -n ESPNABU")
    console.log("EFI partition formated")
    server_port = get_port()
    nc_thread = threading.Thread(
        target=adbd.shell,
        args=(f"busybox nc -l 127.0.0.1:{server_port} > /dev/block/platform/soc/1d84000.ufshc/by-name/linux",),
        daemon=True
    )
    nc_thread.start()
    sleep(3)
    console.log("Flashing RootFS")
    with adbd.create_connection("tcp", server_port) as conn:
        with get_progress() as pbar:
            task = pbar.add_task("[cyan]Uploading RootFS", total=op.getsize(rootfs))
            with open(rootfs, "rb") as rootfs:
                while True:
                    data = rootfs.read(10240)
                    conn.send(data)
                    pbar.update(task, advance=len(data))
                    if len(data) < 10240:
                        break
        conn.close()

    nc_thread.join()

    with console.status("[cyan]Setting up user and creating boot files", spinner="line", spinner_style="white"):
        if adbd.shell2(f"postinstall {username} {password}").returncode == 0:
            console.log("User created")
            console.log("Boot files created")
        else:
            console.log("Postinstall failed. Rebooting to system")
            adbd.reboot()
            return 4

    console.log("Installing UEFI")
    bootshim = files.BootShim.get()
    payload = files.UEFI_Payload.get()
    adbd.shell("mkdir /tmp/uefi-install")
    with get_progress() as pbar:
        task = pbar.add_task("[cyan]Pushing uefi files", total=2)
        adbd.sync.push(bootshim, f"/tmp/uefi-install/{files.BootShim.name}")
        pbar.update(task, advance=1)
        adbd.sync.push(payload, f"/tmp/uefi-install/{files.UEFI_Payload.name}")
        pbar.update(task, advance=1)
    console.log("Patching boot image")
    match adbd.shell2("uefi-patch").returncode:
        case 1:
            console.log("Failed to patch boot")
            return 1
        case 2:
            console.log("Boot image already patched. Skipping")
            adbd.reboot()
        case 0:
            patched_size = int(adbd.shell("stat -c%s /tmp/uefi-install/new-boot.img"))
            with get_progress() as pbar:
                task = pbar.add_task("[cyan]Saving patched boot to disk", total=patched_size)
                boot_uefi_path = op.join(pwd(), "new_boot.img")
                if op.exists(boot_uefi_path):
                    remove(boot_uefi_path)
                with open(boot_uefi_path, "ab") as file:
                    for chunk in adbd.sync.iter_content("/tmp/uefi-install/new-boot.img"):
                        file.write(chunk)
                        pbar.update(task, advance=len(chunk))
            console.log(f"Pathed boot loaded to {boot_uefi_path}")

            backup_size = int(adbd.shell("stat -c%s /tmp/uefi-install/boot.img"))
            with get_progress() as pbar:
                task = pbar.add_task("[cyan]Saving boot backup to disk", total=backup_size)
                boot_backup_path = op.join(pwd(), "boot_backup.img")
                if op.exists(boot_backup_path):
                    remove(boot_backup_path)
                with open(boot_backup_path, "ab") as file:
                    for chunk in adbd.sync.iter_content("/tmp/uefi-install/new-boot.img"):
                        file.write(chunk)
                        pbar.update(task, advance=len(chunk))
            console.log(f"Boot backup saved to {boot_backup_path}")

            console.log("Rebooting to bootloader")
            adbd.shell("reboot bootloader")
            fastboot.wait_for_bootloader(serial)
            console.log("Flashing patched boot")
            with open(boot_uefi_path, "rb") as file:
                fastboot.flash(serial, "boot", file.read())
            fastboot.reboot(serial)

    console.log("Done!")
    return 0


def run() -> None:
    global adb
    status = main()
    if adb is not None:
        with console.status("[cyan]Stopping adb server", spinner="line", spinner_style="white"):
            adb.server_kill()
    exit(status)


if "__main__" == __name__:
    run()
