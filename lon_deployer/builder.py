import PyInstaller.__main__
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()


def get_git_revision(base_path):
    git_dir = Path(base_path) / '.git'
    with (git_dir / 'HEAD').open('r') as head:
        ref = head.readline().split(' ')[-1].strip()

    with (git_dir / ref).open('r') as git_hash:
        return git_hash.readline().strip()


def create_version():
    with open(Path(__file__).parent/"_version.py", "w") as vf:
        vf.write(f"VERSION=\"{get_git_revision(PROJECT_DIR)[:7]}\"")


def build():
    create_version()
    PyInstaller.__main__.run([
        str(PROJECT_DIR / "run.py"),
        '--onefile',
        '--collect-submodules',
        '--name',
        'LoN-Deployer',
        "-i",
        "NONE",
        # other pyinstaller options...
    ])
