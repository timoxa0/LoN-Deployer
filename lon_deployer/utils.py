import logging
import pathlib
import platform
import re
import socket
import subprocess
from random import randint
from time import sleep

import adbutils
from magic import Magic
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from . import exceptions

console = Console(log_path=False)


class TimeRemainingColumnCustom(TimeRemainingColumn):
    max_refresh = 1


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

logger = logging.getLogger("Deployer")


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


def repartition(serial: str, size: int, percents=False) -> None:
    device = adbutils.adb.device(serial)
    block_size = device.shell("blockdev --getsize64 /dev/block/sda")
    if re.match(r"^125[0-9]{9}$", block_size):
        maxsize = 126
    elif re.match(r"^253[0-9]{9}$", block_size):
        maxsize = 254
    else:
        logger.error("Weird block size. Is it nabu?")
        raise exceptions.RepartitonError()
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
    sleep(1)


def check_rootfs(filepath: pathlib.Path) -> bool:
    osname = platform.system()
    if osname == "Linux":
        magic_file = subprocess.check_output(["file", "--version"]) \
            .decode().splitlines()[1].split()[-1].split(":")[-1] + ".mgc"
        logger.debug(f"Magic file: {magic_file}")
        magic = Magic(mime=True, magic_file=magic_file)
    elif osname == "Windows":
        magic = Magic(mime=True)
    else:
        raise exceptions.UnsupportedPlatform(osname)
    filetype = magic.from_file(str(filepath.absolute()))
    logger.debug(f"RootFS MIME type: {filetype}")
    return filetype in ["application/octet-stream", "inode/blockdevice"]
