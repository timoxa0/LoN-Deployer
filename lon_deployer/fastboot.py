import os
import subprocess

from . import files, exceptions
from .utils import logger, console


def _fastboot_run(command: [str], serial: str = None) -> str:
    try:
        cmd = ["fastboot"]
        if not serial:
            cmd += command
        else:
            cmd += ["-s", serial] + command
        logger.debug(f"fb-cmd: {cmd}")
        fb_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=60)
        logger.debug(f"fb-out: {fb_out}")
    except FileNotFoundError:
        console.log("Fastboot binary not found")
        console.log("Exiting")
        exit(1)
    except subprocess.CalledProcessError:
        raise exceptions.DeviceNotFound("Timed out")
    else:
        return fb_out.decode()


def list_devices() -> [str]:
    return list(
        filter(
            lambda x: x != "",
            [x.split("\t ")[0] for x in _fastboot_run(["devices"]).split("\n")]
        )
    )


def check_device(serial: str) -> bool:
    return "nabu" in _fastboot_run(["getvar", "product"], serial=serial)


def check_parts(serial: str) -> bool:
    linux_response = _fastboot_run(["getvar", "partition-type:linux"], serial=serial)
    esp_response = _fastboot_run(["getvar", "partition-type:esp"], serial=serial)
    logger.debug({
        "esp": 'FAILED' not in esp_response,
        "linux": 'FAILED' not in linux_response
    })
    return not ("FAILED" in linux_response or "FAILED" in esp_response)


def reboot(serial: str) -> None:
    _fastboot_run(["reboot"], serial=serial)


def boot_ofox(serial: str) -> None:
    files.OrangeFox.get()
    ofox = files.OrangeFox.filepath
    with console.status("[cyan]Booting", spinner="line", spinner_style="white"):
        out = _fastboot_run(["boot", ofox], serial)
        if "Failed to load/authenticate boot image: Device Error" in out:
            raise exceptions.UnauthorizedBootImage("Failed to load/authenticate boot image: Device Error", out)


def flash(serial: str, part: str, data: bytes) -> None:
    with open("image.img", "wb") as file:
        file.write(data)

    with console.status(f"[cyan]Flashing {part}", spinner="line", spinner_style="white"):
        _fastboot_run(["flash", part, "image.img"], serial=serial)

    os.remove("image.img")


def restore_parts(serial: str) -> None:
    gpt_both = files.GPT_Both0.get()
    userdata = files.UserData_Empty.get()
    flash(serial, "partition:0", gpt_both)
    flash(serial, "userdata", userdata)


def clean_device(serial: str) -> None:
    _fastboot_run(["erase", "linux"], serial=serial)
    _fastboot_run(["erase", "esp"], serial=serial)


def wait_for_bootloader(serial: str) -> None:
    _fastboot_run(["getvar", "product"], serial=serial)
