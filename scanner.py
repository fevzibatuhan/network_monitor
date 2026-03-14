"""
Ağ Tarama Motoru
ARP taraması ve ping yöntemleriyle ağdaki cihazları tespit eder.
Hem Windows hem Linux'ta çalışır.
"""

import os
import sys
import socket
import subprocess
import platform
import re
import time
import ipaddress
import threading
import struct
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None

from mac_vendor import MacVendorLookup


@dataclass
class DeviceInfo:
    """Ağdaki bir cihazın bilgilerini tutan veri sınıfı."""
    ip: str
    hostname: str = "Bilinmiyor"
    mac: str = "N/A"
    vendor: str = "Bilinmiyor"
    status: str = "Online"
    device_type: str = "Bilinmiyor"
    first_seen: str = ""
    last_seen: str = ""
    is_local: bool = False
    battery_percent: Optional[int] = None
    battery_plugged: Optional[bool] = None

    def to_dict(self) -> dict:
        """Sözlüğe dönüştür."""
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "mac": self.mac,
            "vendor": self.vendor,
            "status": self.status,
            "device_type": self.device_type,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "is_local": self.is_local,
            "battery_percent": self.battery_percent,
            "battery_plugged": self.battery_plugged,
        }


class NetworkScanner:
    """Ağ tarama sınıfı. Cross-platform çalışır."""

    def __init__(self):
        self.vendor_lookup = MacVendorLookup()
        self.devices: Dict[str, DeviceInfo] = {}
        self.is_scanning = False
        self._stop_event = threading.Event()
        self._platform = platform.system().lower()
        self._is_admin = self._check_admin()
        self._local_ip = ""
        self._local_mac = ""
        self._network_cidr = ""

    def _check_admin(self) -> bool:
        """Yönetici/root yetkisi kontrolü."""
        if self._platform == "windows":
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        else:
            return os.geteuid() == 0

    @property
    def has_admin(self) -> bool:
        return self._is_admin

    def get_local_info(self) -> Tuple[str, str, str]:
        """Yerel IP, MAC ve ağ CIDR bilgisini al."""
        local_ip = ""
        local_mac = ""
        network_cidr = ""

        # IP adresini bul
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        # psutil ile arayüz bilgilerini al
        if psutil:
            try:
                for iface, addrs in psutil.net_if_addrs().items():
                    ipv4_addr = None
                    mac_addr = None
                    netmask = None
                    for addr in addrs:
                        if addr.family == socket.AF_INET and addr.address == local_ip:
                            ipv4_addr = addr.address
                            netmask = addr.netmask
                        if addr.family == psutil.AF_LINK:
                            mac_addr = addr.address
                    if ipv4_addr and mac_addr:
                        local_mac = mac_addr.upper().replace('-', ':')
                        if netmask:
                            try:
                                net = ipaddress.IPv4Network(f"{local_ip}/{netmask}", strict=False)
                                network_cidr = str(net)
                            except Exception:
                                pass
                        break
            except Exception:
                pass

        # Fallback: ağ CIDR'ını tahmin et
        if not network_cidr and local_ip != "127.0.0.1":
            parts = local_ip.split('.')
            network_cidr = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

        # Fallback: MAC adresini al
        if not local_mac:
            local_mac = self._get_mac_fallback(local_ip)

        self._local_ip = local_ip
        self._local_mac = local_mac
        self._network_cidr = network_cidr

        return local_ip, local_mac, network_cidr

    def _get_mac_fallback(self, ip: str) -> str:
        """Alternatif MAC adresi alma yöntemi."""
        if self._platform == "windows":
            try:
                result = subprocess.run(
                    ["getmac", "/v", "/fo", "csv"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.splitlines():
                    if ip in line:
                        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line)
                        if mac_match:
                            return mac_match.group().upper().replace('-', ':')
            except Exception:
                pass
        else:
            try:
                result = subprocess.run(
                    ["ip", "link"],
                    capture_output=True, text=True, timeout=10
                )
                mac_match = re.search(r'link/ether\s+([0-9a-fA-F:]{17})', result.stdout)
                if mac_match:
                    return mac_match.group(1).upper()
            except Exception:
                pass
        return "N/A"

    def _resolve_hostname(self, ip: str) -> str:
        """IP adresinden hostname çöz."""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return "Bilinmiyor"

    def _get_mac_from_arp(self, ip: str) -> str:
        """ARP tablosundan MAC adresi al."""
        try:
            if self._platform == "windows":
                result = subprocess.run(
                    ["arp", "-a", ip],
                    capture_output=True, text=True, timeout=5
                )
            else:
                result = subprocess.run(
                    ["arp", "-n", ip],
                    capture_output=True, text=True, timeout=5
                )
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', result.stdout)
            if mac_match:
                mac = mac_match.group().upper().replace('-', ':')
                if mac != "FF:FF:FF:FF:FF:FF":
                    return mac
        except Exception:
            pass
        return "N/A"

    def _ping_host(self, ip: str) -> bool:
        """Bir IP adresine ping at."""
        try:
            if self._platform == "windows":
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=3
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    def _scan_with_scapy(self, network: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Scapy ile ARP taraması yap (root/admin gerektirir)."""
        results = []
        try:
            from scapy.all import ARP, Ether, srp, conf
            conf.verb = 0  # Scapy çıktısını sustur

            arp_request = ARP(pdst=network)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast / arp_request

            answered, _ = srp(arp_request_broadcast, timeout=3, retry=1, verbose=False)

            for i, (sent, received) in enumerate(answered):
                if self._stop_event.is_set():
                    break
                results.append({
                    "ip": received.psrc,
                    "mac": received.hwsrc.upper(),
                })
                if progress_callback:
                    progress_callback(f"ARP yanıtı: {received.psrc}", -1)

        except ImportError:
            pass
        except PermissionError:
            pass
        except Exception:
            pass

        return results

    def _scan_with_ping(self, network: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Ping taraması ile cihazları tespit et."""
        results = []
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            hosts = list(net.hosts())
            total = len(hosts)

            # Paralel ping için thread kullan
            found_ips = []
            lock = threading.Lock()

            def ping_worker(ip_str, idx):
                if self._stop_event.is_set():
                    return
                if progress_callback:
                    progress_callback(f"Taranıyor: {ip_str}", int((idx / total) * 100))
                if self._ping_host(ip_str):
                    with lock:
                        found_ips.append(ip_str)

            # Thread havuzu
            threads = []
            max_threads = 50
            for idx, host in enumerate(hosts):
                if self._stop_event.is_set():
                    break
                ip_str = str(host)
                t = threading.Thread(target=ping_worker, args=(ip_str, idx))
                threads.append(t)
                t.start()

                # Aktif thread sayısını sınırla
                while len([t for t in threads if t.is_alive()]) >= max_threads:
                    time.sleep(0.05)

            # Tüm thread'lerin bitmesini bekle
            for t in threads:
                t.join(timeout=5)

            # Bulunan IP'ler için MAC adreslerini al
            for ip_str in found_ips:
                if self._stop_event.is_set():
                    break
                mac = self._get_mac_from_arp(ip_str)
                results.append({"ip": ip_str, "mac": mac})

        except Exception:
            pass

        return results

    def _get_battery_info(self) -> Tuple[Optional[int], Optional[bool]]:
        """Yerel bilgisayarın pil bilgisini al."""
        if not psutil:
            return None, None
        try:
            battery = psutil.sensors_battery()
            if battery:
                return int(battery.percent), battery.power_plugged
        except Exception:
            pass
        return None, None

    def _determine_device_type(self, ip: str, mac: str, vendor: str, hostname: str) -> str:
        """Cihaz türünü tahmin et."""
        # Üretici bazlı tahmin
        device_type = self.vendor_lookup.get_device_type(vendor)
        if device_type != "Bilinmiyor":
            return device_type

        # Gateway/Router kontrolü
        if ip == self._get_gateway():
            return "Router/Gateway"

        # Hostname bazlı tahmin
        hostname_lower = hostname.lower() if hostname else ""
        if any(kw in hostname_lower for kw in ["iphone", "ipad", "android", "galaxy", "pixel", "phone"]):
            return "Telefon"
        if any(kw in hostname_lower for kw in ["macbook", "laptop", "desktop", "pc", "dell", "lenovo", "hp"]):
            return "Bilgisayar"
        if any(kw in hostname_lower for kw in ["printer", "epson", "canon", "brother"]):
            return "Yazıcı"
        if any(kw in hostname_lower for kw in ["tv", "smart-tv", "roku", "chromecast", "firestick"]):
            return "Akıllı TV"
        if any(kw in hostname_lower for kw in ["camera", "cam", "hikvision", "dahua"]):
            return "IP Kamera"
        if any(kw in hostname_lower for kw in ["echo", "alexa", "google-home", "homepod"]):
            return "Akıllı Hoparlör"
        if any(kw in hostname_lower for kw in ["switch", "ap", "access-point"]):
            return "Ağ Cihazı"
        if any(kw in hostname_lower for kw in ["xbox", "playstation", "ps4", "ps5", "nintendo"]):
            return "Oyun Konsolu"
        if any(kw in hostname_lower for kw in ["tablet", "ipad", "tab"]):
            return "Tablet"
        if any(kw in hostname_lower for kw in ["raspberry", "pi", "arduino", "esp"]):
            return "IoT/Geliştirme Kartı"

        return "Bilinmiyor"

    def _get_gateway(self) -> str:
        """Varsayılan ağ geçidini (gateway) bul."""
        try:
            if self._platform == "windows":
                result = subprocess.run(
                    ["ipconfig"],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.splitlines():
                    if "Default Gateway" in line or "Varsayılan Ağ Geçidi" in line:
                        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if ip_match:
                            return ip_match.group(1)
            else:
                result = subprocess.run(
                    ["ip", "route", "show", "default"],
                    capture_output=True, text=True, timeout=5
                )
                match = re.search(r'default via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # Fallback: .1 adresi genellikle gateway'dir
        if self._local_ip:
            parts = self._local_ip.split('.')
            return f"{parts[0]}.{parts[1]}.{parts[2]}.1"
        return ""

    def scan(self, progress_callback: Optional[Callable] = None) -> Dict[str, DeviceInfo]:
        """Ana tarama fonksiyonu."""
        self.is_scanning = True
        self._stop_event.clear()

        try:
            # Yerel bilgileri al
            local_ip, local_mac, network_cidr = self.get_local_info()

            if progress_callback:
                progress_callback(f"Yerel IP: {local_ip}, Ağ: {network_cidr}", 0)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Scapy ile ARP taraması dene
            raw_results = []
            if self._is_admin:
                if progress_callback:
                    progress_callback("ARP taraması yapılıyor...", 5)
                raw_results = self._scan_with_scapy(network_cidr, progress_callback)

            # ARP sonuç yoksa veya admin değilse, ping taraması yap
            if not raw_results:
                if progress_callback:
                    progress_callback("Ping taraması yapılıyor...", 10)
                raw_results = self._scan_with_ping(network_cidr, progress_callback)

            if self._stop_event.is_set():
                return self.devices

            if progress_callback:
                progress_callback("Cihaz bilgileri çözümleniyor...", 85)

            # Mevcut cihazları offline yap
            for dev in self.devices.values():
                dev.status = "Offline"

            # Bulunan cihazları işle
            total = len(raw_results)
            for idx, item in enumerate(raw_results):
                if self._stop_event.is_set():
                    break

                ip = item["ip"]
                mac = item.get("mac", "N/A")

                if progress_callback:
                    pct = 85 + int((idx / max(total, 1)) * 14)
                    progress_callback(f"İşleniyor: {ip}", pct)

                # Hostname çöz
                hostname = self._resolve_hostname(ip)

                # Üretici bul
                vendor = self.vendor_lookup.lookup(mac) if mac != "N/A" else "Bilinmiyor"

                # Cihaz türü tahmin et
                device_type = self._determine_device_type(ip, mac, vendor, hostname)

                # Gateway kontrolü
                gateway = self._get_gateway()
                if ip == gateway:
                    device_type = "Router/Gateway"

                # Yerel cihaz mı?
                is_local = (ip == local_ip)

                # Pil bilgisi (sadece yerel cihaz için)
                battery_pct = None
                battery_plugged = None
                if is_local:
                    battery_pct, battery_plugged = self._get_battery_info()
                    if local_mac and mac == "N/A":
                        mac = local_mac
                        vendor = self.vendor_lookup.lookup(mac)

                # Mevcut cihaz mı kontrol et
                if ip in self.devices:
                    dev = self.devices[ip]
                    dev.status = "Online"
                    dev.last_seen = now
                    dev.hostname = hostname if hostname != "Bilinmiyor" else dev.hostname
                    dev.mac = mac if mac != "N/A" else dev.mac
                    dev.vendor = vendor if vendor != "Bilinmiyor" else dev.vendor
                    dev.device_type = device_type if device_type != "Bilinmiyor" else dev.device_type
                    dev.is_local = is_local
                    dev.battery_percent = battery_pct
                    dev.battery_plugged = battery_plugged
                else:
                    self.devices[ip] = DeviceInfo(
                        ip=ip,
                        hostname=hostname,
                        mac=mac,
                        vendor=vendor,
                        status="Online",
                        device_type=device_type,
                        first_seen=now,
                        last_seen=now,
                        is_local=is_local,
                        battery_percent=battery_pct,
                        battery_plugged=battery_plugged,
                    )

            if progress_callback:
                progress_callback(f"Tarama tamamlandı. {len([d for d in self.devices.values() if d.status == 'Online'])} cihaz bulundu.", 100)

        except Exception as e:
            if progress_callback:
                progress_callback(f"Tarama hatası: {str(e)}", -1)
        finally:
            self.is_scanning = False

        return self.devices

    def stop_scan(self):
        """Devam eden taramayı durdur."""
        self._stop_event.set()

    def get_devices_list(self) -> List[DeviceInfo]:
        """Cihaz listesini döndür."""
        return sorted(self.devices.values(), key=lambda d: (
            0 if d.is_local else 1,
            0 if d.status == "Online" else 1,
            [int(p) for p in d.ip.split('.')]
        ))
