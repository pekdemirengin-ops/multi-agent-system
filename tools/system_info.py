"""Sistem bilgisi araci (CPU, RAM, disk)."""
from __future__ import annotations

from typing import Any

import psutil


def get_system_status() -> dict[str, Any]:
    """Anlik sistem durumunu dondurur.

    Returns:
        {
            "cpu_percent": float,
            "memory_percent": float,
            "memory_used_gb": float,
            "memory_total_gb": float,
            "disk_percent": float,
            "disk_used_gb": float,
            "disk_total_gb": float,
            "boot_time_hours": float,
        }
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = psutil.boot_time()
    import time

    uptime_hours = (time.time() - boot) / 3600

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "boot_time_hours": round(uptime_hours, 2),
    }


def format_status(status: dict[str, Any]) -> str:
    """Sistem durumunu okunabilir metne cevirir."""
    lines = [
        f"CPU: {status['cpu_percent']}%",
        f"RAM: {status['memory_percent']}% "
        f"({status['memory_used_gb']}/{status['memory_total_gb']} GB)",
        f"Disk: {status['disk_percent']}% "
        f"({status['disk_used_gb']}/{status['disk_total_gb']} GB)",
        f"Uptime: {status['boot_time_hours']} saat",
    ]
    return "\n".join(lines)


def check_thresholds(
    status: dict[str, Any],
    cpu_limit: float = 85.0,
    mem_limit: float = 90.0,
    disk_limit: float = 90.0,
) -> list[str]:
    """Esik degerleri asildiysa uyarilari dondurur."""
    alerts: list[str] = []
    if status["cpu_percent"] > cpu_limit:
        alerts.append(f"YUKSEK CPU: {status['cpu_percent']}% (limit: {cpu_limit}%)")
    if status["memory_percent"] > mem_limit:
        alerts.append(
            f"YUKSEK RAM: {status['memory_percent']}% (limit: {mem_limit}%)"
        )
    if status["disk_percent"] > disk_limit:
        alerts.append(
            f"YUKSEK DISK: {status['disk_percent']}% (limit: {disk_limit}%)"
        )
    return alerts


if __name__ == "__main__":
    status = get_system_status()
    print(format_status(status))
    print()
    alerts = check_thresholds(status)
    if alerts:
        print("UYARILAR:")
        for a in alerts:
            print(f"  - {a}")
    else:
        print("Tum degerler normal.")