"""
Dışa Aktarma Modülü
Tarama sonuçlarını CSV ve JSON formatlarında dışa aktarır.
"""

import csv
import json
import os
from typing import List
from datetime import datetime

from scanner import DeviceInfo


def export_to_csv(devices: List[DeviceInfo], filepath: str) -> str:
    """Cihaz listesini CSV dosyasına aktar."""
    headers = [
        "IP Adresi", "Cihaz Adı", "MAC Adresi", "Üretici Firma",
        "Bağlantı Durumu", "Cihaz Türü", "İlk Görülme", "Son Görülme",
        "Yerel Cihaz", "Pil Durumu (%)", "Şarjda"
    ]

    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for dev in devices:
                writer.writerow([
                    dev.ip,
                    dev.hostname,
                    dev.mac,
                    dev.vendor,
                    dev.status,
                    dev.device_type,
                    dev.first_seen,
                    dev.last_seen,
                    "Evet" if dev.is_local else "Hayır",
                    dev.battery_percent if dev.battery_percent is not None else "N/A",
                    "Evet" if dev.battery_plugged else ("Hayır" if dev.battery_plugged is False else "N/A"),
                ])
        return filepath
    except Exception as e:
        raise RuntimeError(f"CSV dışa aktarma hatası: {e}")


def export_to_json(devices: List[DeviceInfo], filepath: str) -> str:
    """Cihaz listesini JSON dosyasına aktar."""
    try:
        data = {
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_devices": len(devices),
            "online_devices": sum(1 for d in devices if d.status == "Online"),
            "offline_devices": sum(1 for d in devices if d.status == "Offline"),
            "devices": [dev.to_dict() for dev in devices]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
    except Exception as e:
        raise RuntimeError(f"JSON dışa aktarma hatası: {e}")
