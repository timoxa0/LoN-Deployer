import PyInstaller.__main__
from pathlib import Path

HERE = Path(__file__).parent.parent.absolute()
path_to_main = str(HERE / "run.py")


def install():
    PyInstaller.__main__.run([
        path_to_main,
        '--onefile',
        '--collect-submodules',
        '--name LoN Deployer',
        "-i",
        "NONE",
        # other pyinstaller options...
    ])
