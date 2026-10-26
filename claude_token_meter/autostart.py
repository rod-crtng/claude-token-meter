import os
import plistlib
import subprocess
import sys
from pathlib import Path

SHORTCUT_NAME = "claude-token-meter.lnk"
LAUNCH_AGENT_LABEL = "com.crtng.claude-token-meter"


def _plat(platform: str | None) -> str:
    return platform or sys.platform


def menu_label(platform: str | None = None) -> str:
    return "Iniciar com o Mac" if _plat(platform) == "darwin" else "Iniciar com o Windows"


def startup_dir(platform: str | None = None) -> Path:
    if _plat(platform) == "darwin":
        return Path.home() / "Library" / "LaunchAgents"
    appdata = os.environ.get("APPDATA") or str(Path.home())
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path(directory: Path | None = None, platform: str | None = None) -> Path:
    name = LAUNCH_AGENT_LABEL + ".plist" if _plat(platform) == "darwin" else SHORTCUT_NAME
    return (Path(directory) if directory else startup_dir(platform)) / name


def is_enabled(directory: Path | None = None, platform: str | None = None) -> bool:
    return shortcut_path(directory, platform).exists()


def disable(directory: Path | None = None, platform: str | None = None) -> None:
    p = shortcut_path(directory, platform)
    if p.exists():
        p.unlink()


def enable(directory: Path | None = None, platform: str | None = None) -> None:
    if _plat(platform) == "darwin":
        _enable_launch_agent(shortcut_path(directory, platform))
    else:
        _enable_lnk(shortcut_path(directory, platform))


def _enable_launch_agent(plist: Path) -> None:
    """LaunchAgent do usuario: o launchd abre o medidor no proximo login. Usa o
    python do venv (sys.executable) — no macOS nao existe pythonw."""
    workdir = str(Path(__file__).resolve().parent.parent)
    data = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [sys.executable, "-m", "claude_token_meter.main"],
        "WorkingDirectory": workdir,
        "RunAtLoad": True,
    }
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(plistlib.dumps(data))


def _enable_lnk(lnk_path: Path) -> None:
    """Create a .lnk that launches the meter with pythonw (no console flash)."""
    target = str(Path(sys.executable).with_name("pythonw.exe"))
    workdir = str(Path(__file__).resolve().parent.parent)
    args = "-m claude_token_meter.main"
    lnk = str(lnk_path)
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='%s';"
        "$s.WorkingDirectory='%s';$s.Save()" % (lnk, target, args, workdir)
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
