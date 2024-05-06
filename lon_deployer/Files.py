import os
import json
import urllib.parse
import requests
import hashlib
from os import path as op
from os import getcwd as pwd
from sys import exit
from rich.console import Console

from .utils import get_progress

console = Console(log_path=False)


class File:
    def __init__(self, url: str):
        self.name = url.split("/")[-1]
        self.url = url
        self.filepath = op.join(pwd(), "files/", self.name)
        if not op.exists(op.join(pwd(), "files/")):
            os.mkdir(op.join(pwd(), "files/"))
        elif not op.isdir(op.join(pwd(), "files/")):
            os.remove(op.join(pwd(), "files/"))
            os.mkdir(op.join(pwd(), "files/"))

    def md5sum(self) -> str | None:
        try:
            return json.loads(requests.get(f"https://timoxa0.su/?info={urllib.parse.urlparse(self.url).path}")
                              .content.decode())["hashes"]["md5"]
        except requests.ConnectionError:
            pass

    def get(self):
        while True:
            md5sum = self.md5sum()
            if not md5sum:
                console.log(f"Unable to verify {self.name} checksum")

            if op.exists(self.filepath):
                with open(self.filepath, "rb") as file:
                    data = file.read()
                    if hashlib.md5(data).hexdigest() == md5sum or not md5sum:
                        return data

            download_image = b""
            r = requests.get(self.url, stream=True)
            if r.status_code != 200:
                console.log(f"{self.name} not found on server. Please contact developer")
            total_size = int(r.headers.get("content-length", 0))
            block_size = 204800
            with get_progress() as pbar:
                task = pbar.add_task(f"[green]Downloading {self.name}", total=total_size)
                for data in r.iter_content(block_size):
                    download_image += data
                    pbar.update(task, advance=len(data))
            with open(self.filepath, "wb") as file:
                file.write(download_image)

            if hashlib.md5(download_image).hexdigest() == md5sum or not md5sum:
                return download_image
            else:
                console.log("Downloaded file corrupted!")


OrangeFox = File(
    url="https://timoxa0.su/share/nabu/deployer/orangefox.img"
)

UEFI_Payload = File(
    url="https://timoxa0.su/share/nabu/deployer/uefi/nabu_UEFI.fd"
)

BootShim = File(
    url="https://timoxa0.su/share/nabu/deployer/uefi/BootShim.Dualboot.bin"
)

GPT_Both0 = File(
    url="https://timoxa0.su/share/nabu/deployer/gpt_both0.bin"
)

UserData_Empty = File(
    url="https://timoxa0.su/share/nabu/deployer/userdata.img"
)
