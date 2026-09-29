"""
Real-time ADB device monitor.
Runs a background thread that polls `adb devices` and fires callbacks
when devices are attached or detached.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class AndroidDevice:
    serial: str
    state: str          # "device" | "offline" | "unauthorized" | "recovery"
    model: str = ""
    manufacturer: str = ""
    android_version: str = ""
    sdk_version: str = ""
    product: str = ""
    usb_debugging: bool = False

    @property
    def display_name(self) -> str:
        if self.model:
            return f"{self.manufacturer} {self.model} ({self.serial})"
        return self.serial

    @property
    def is_ready(self) -> bool:
        return self.state == "device"


def _run(cmd: list[str], timeout: int = 8) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as exc:
        return f"[error] {exc}"


def _getprop(serial: str, prop: str) -> str:
    return _run(["adb", "-s", serial, "shell", "getprop", prop])


def _enumerate_devices() -> list[AndroidDevice]:
    if not shutil.which("adb"):
        return []
    raw = _run(["adb", "devices", "-l"])
    devices: list[AndroidDevice] = []
    for line in raw.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        dev = AndroidDevice(serial=serial, state=state)
        if state == "device":
            dev.model = _getprop(serial, "ro.product.model")
            dev.manufacturer = _getprop(serial, "ro.product.manufacturer")
            dev.android_version = _getprop(serial, "ro.build.version.release")
            dev.sdk_version = _getprop(serial, "ro.build.version.sdk")
            dev.product = _getprop(serial, "ro.product.name")
            dev.usb_debugging = True
        devices.append(dev)
    return devices


class DeviceMonitor:
    """Background thread that polls ADB every `interval` seconds."""

    def __init__(self, interval: float = 3.0) -> None:
        self._interval = interval
        self._lock = threading.Lock()
        self._devices: dict[str, AndroidDevice] = {}
        self._callbacks_attach: list[Callable[[AndroidDevice], None]] = []
        self._callbacks_detach: list[Callable[[str], None]] = []
        self._callbacks_update: list[Callable[[list[AndroidDevice]], None]] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── public API ────────────────────────────────────────────────────────────

    def on_attach(self, cb: Callable[[AndroidDevice], None]) -> None:
        self._callbacks_attach.append(cb)

    def on_detach(self, cb: Callable[[str], None]) -> None:
        self._callbacks_detach.append(cb)

    def on_update(self, cb: Callable[[list[AndroidDevice]], None]) -> None:
        self._callbacks_update.append(cb)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def devices(self) -> list[AndroidDevice]:
        with self._lock:
            return list(self._devices.values())

    def refresh_once(self) -> list[AndroidDevice]:
        devs = _enumerate_devices()
        with self._lock:
            self._devices = {d.serial: d for d in devs}
        for cb in self._callbacks_update:
            cb(devs)
        return devs

    # ── background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            current = {d.serial: d for d in _enumerate_devices()}
            with self._lock:
                prev = self._devices
                attached = [d for s, d in current.items() if s not in prev]
                detached = [s for s in prev if s not in current]
                self._devices = current

            for dev in attached:
                for cb in self._callbacks_attach:
                    cb(dev)
            for serial in detached:
                for cb in self._callbacks_detach:
                    cb(serial)
            if attached or detached:
                for cb in self._callbacks_update:
                    cb(list(current.values()))

            self._stop_event.wait(self._interval)
