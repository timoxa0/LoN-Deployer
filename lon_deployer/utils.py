import logging
import os
import re
import socket
import subprocess
from random import randint
from time import sleep

import adbutils
from rich.logging import RichHandler
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from . import Files


console = Console(log_path=False)


class TimeRemainingColumnCustom(TimeRemainingColumn):
    max_refresh = 1


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

logger = logging.getLogger("Deployer")


class DeviceNotFound(Exception):
    pass


def get_progress() -> Progress:
    return Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumnCustom(),
    )


def fastboot_run(command: [str], serial: str = None) -> str:

    try:
        if not serial:
            cmd = f"fastboot {' '.join(command)}"
        else:
            cmd = f"fastboot -s {serial} {' '.join(command)}"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except FileNotFoundError:
        console.log("Fastboot binary not found")
        console.log("Exiting")
        exit(1)
    else:
        stdout, stderr = proc.communicate()
        proc.wait()
        logger.debug(f"fb-cmd: {cmd}")
        logger.debug(f"fb-out: {stdout}")
        logger.debug(f"fb-err: {stderr}")
        return (stdout if stdout else stderr).decode()


def list_fb_devices() -> [str]:
    return [x.split("\t ")[0] for x in fastboot_run(["devices"]).split("\n")[:-1]]


def check_device(serial: str) -> bool:
    return "nabu" in fastboot_run(["getvar", "product"], serial=serial)


def check_parts(serial: str) -> bool:
    linux_response = fastboot_run(["getvar", "partition-type:linux"], serial=serial)
    esp_response = fastboot_run(["getvar", "partition-type:esp"], serial=serial)
    logger.debug({
        "esp": 'FAILED' not in esp_response,
        "linux": 'FAILED' not in linux_response
    })
    return not ("FAILED" in linux_response or "FAILED" in esp_response)


def reboot_fb_device(serial: str) -> None:
    fastboot_run(["reboot"], serial=serial)


def check_port(tcp_port: int) -> bool:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", tcp_port))
    except OSError as e:
        if e.errno == 98:
            return False
    return True


def get_port() -> int:
    while True:
        tcp_port = randint(10000, 60000)
        if check_port(tcp_port):
            return tcp_port


def boot_ofox(serial: str) -> None:
    Files.OrangeFox.get()
    ofox = Files.OrangeFox.filepath
    with console.status("[cyan]Booting", spinner="line", spinner_style="white"):
        fastboot_run(["boot", ofox])


def flash_boot(serial: str, boot_data: bytes) -> None:
    proper_flash(serial, "boot", boot_data)


def proper_flash(serial: str, part: str, data: bytes) -> None:
    with open("image.img", "wb") as file:
        file.write(data)

    with console.status(f"[cyan]Flashing {part}", spinner="line", spinner_style="white"):
        fastboot_run(["flash", part, "image.img"], serial=serial)

    os.remove("image.img")


def restore_parts(serial: str) -> None:
    gpt_both = Files.GPT_Both0.get()
    userdata = Files.UserData_Empty.get()
    proper_flash(serial, "partition:0", gpt_both)
    proper_flash(serial, "userdata", userdata)


def clean_device(serial: str) -> None:
    fastboot_run(["erase", "linux"], serial=serial)
    fastboot_run(["erase", "esp"], serial=serial)


def repartition(serial: str, size: int, percents=False) -> None:
    device = adbutils.adb.device(serial)
    block_size = device.shell("blockdev --getsize64 /dev/block/sda")
    if re.match(r"^125[0-9]{9}$", block_size):
        maxsize = 126
    elif re.match(r"^253[0-9]{9}$", block_size):
        maxsize = 254
    else:
        logger.error("Weird block size. Is it nabu?")
        exit(4)
    linux_max = maxsize - 12
    if percents:
        size = round(linux_max / 100 * size, 2)

    if size > linux_max:
        raise ValueError("Too big partition")
    userdata_end = maxsize - 1 - size
    linux_end = userdata_end + size
    cmds = [
        "sgdisk --resize-table 64 /dev/block/sda",
        f"parted -s /dev/block/sda rm 31",
        f"parted -s /dev/block/sda mkpart userdata ext4 10.9GB {userdata_end}GB",
        f"parted -s /dev/block/sda mkpart linux ext4 {userdata_end}GB {linux_end}GB",
        f"parted -s /dev/block/sda mkpart esp fat32 {linux_end}GB {maxsize}GB",
        f"parted -s /dev/block/sda set 33 esp on"
    ]
    for cmd in cmds:
        device.shell(cmd)
    sleep(3)


def wait_for_bootloader(serial: str) -> None:
    fastboot_run(["getvar", "product"], serial=serial)
