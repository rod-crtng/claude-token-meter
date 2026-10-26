"""Instancia unica, solta quando o processo morre (crash nao deixa trava presa).

Windows: named mutex do kernel. macOS/Linux: flock num arquivo da pasta de
dados — o kernel solta o flock quando o descritor fecha, inclusive na morte do
processo. Sem PySide6 de proposito: roda ANTES de subir o Qt.
"""

import sys
from pathlib import Path

_HELD = []  # segura o handle/descritor vivo pela vida do processo


def acquire_windows(name: str) -> bool:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    ERROR_ALREADY_EXISTS = 183
    if not handle or kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    _HELD.append(handle)
    return True


def acquire_posix(lock_path: Path):
    """Descritor com o flock exclusivo, ou None se outra instancia segura."""
    import fcntl
    import os
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def release_posix(fd) -> None:
    import os
    os.close(fd)


def acquire(name: str, lock_path: Path) -> bool:
    if sys.platform == "win32":
        return acquire_windows(name)
    fd = acquire_posix(lock_path)
    if fd is None:
        return False
    _HELD.append(fd)
    return True
