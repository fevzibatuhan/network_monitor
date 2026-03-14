#!/usr/bin/env python3
"""
Ağ İzleme Uygulaması - Ana GUI Modülü
Cross-platform (Windows & Linux) ağ izleme masaüstü uygulaması.
CustomTkinter tabanlı modern arayüz.
"""

import os
import sys
import threading
import time
import platform
from datetime import datetime
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

from scanner import NetworkScanner, DeviceInfo
from exporter import export_to_csv, export_to_json


# --- Tema Ayarları ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Renkler
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_card_hover": "#1a2744",
    "accent": "#0f3460",
    "accent_light": "#533483",
    "online": "#00b894",
    "offline": "#d63031",
    "warning": "#fdcb6e",
    "text": "#dfe6e9",
    "text_dim": "#636e72",
    "border": "#2d3436",
    "header_bg": "#0a1628",
    "row_even": "#16213e",
    "row_odd": "#1a2744",
    "local_highlight": "#0a3d62",
    "button_primary": "#0984e3",
    "button_danger": "#d63031",
    "button_success": "#00b894",
    "progress_bg": "#2d3436",
}


class DeviceTableFrame(ctk.CTkScrollableFrame):
    """Cihaz listesini tablo formatında gösteren scroll edilebilir frame."""

    COLUMNS = [
        ("Durum", 70),
        ("IP Adresi", 130),
        ("Cihaz Adı", 160),
        ("MAC Adresi", 150),
        ("Üretici", 130),
        ("Cihaz Türü", 130),
        ("İlk Görülme", 150),
        ("Son Görülme", 150),
        ("Pil", 80),
    ]

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=COLORS["bg_dark"])
        self._rows = []
        self._create_header()

    def _create_header(self):
        """Tablo başlığını oluştur."""
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["header_bg"], corner_radius=0, height=36)
        header_frame.pack(fill="x", pady=(0, 2))
        header_frame.pack_propagate(False)

        for col_name, col_width in self.COLUMNS:
            lbl = ctk.CTkLabel(
                header_frame,
                text=col_name,
                width=col_width,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text"],
                anchor="w",
            )
            lbl.pack(side="left", padx=(6, 2))

    def clear(self):
        """Tüm satırları temizle."""
        for row_frame in self._rows:
            row_frame.destroy()
        self._rows = []

    def add_device(self, device: DeviceInfo, row_index: int):
        """Tabloya bir cihaz satırı ekle."""
        # Satır rengi
        if device.is_local:
            bg_color = COLORS["local_highlight"]
        elif row_index % 2 == 0:
            bg_color = COLORS["row_even"]
        else:
            bg_color = COLORS["row_odd"]

        row_frame = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=4, height=34)
        row_frame.pack(fill="x", pady=1, padx=2)
        row_frame.pack_propagate(False)

        # Durum
        status_color = COLORS["online"] if device.status == "Online" else COLORS["offline"]
        status_text = "● Online" if device.status == "Online" else "● Offline"
        status_lbl = ctk.CTkLabel(
            row_frame, text=status_text, width=self.COLUMNS[0][1],
            font=ctk.CTkFont(size=11, weight="bold"), text_color=status_color, anchor="w"
        )
        status_lbl.pack(side="left", padx=(6, 2))

        # IP (yerel ise vurgula)
        ip_text = device.ip
        if device.is_local:
            ip_text = f"{device.ip} ★"
        ip_lbl = ctk.CTkLabel(
            row_frame, text=ip_text, width=self.COLUMNS[1][1],
            font=ctk.CTkFont(size=11), text_color=COLORS["text"], anchor="w"
        )
        ip_lbl.pack(side="left", padx=(6, 2))

        # Hostname
        hostname_text = device.hostname[:22] + "..." if len(device.hostname) > 25 else device.hostname
        hostname_lbl = ctk.CTkLabel(
            row_frame, text=hostname_text, width=self.COLUMNS[2][1],
            font=ctk.CTkFont(size=11), text_color=COLORS["text"], anchor="w"
        )
        hostname_lbl.pack(side="left", padx=(6, 2))

        # MAC
        mac_lbl = ctk.CTkLabel(
            row_frame, text=device.mac, width=self.COLUMNS[3][1],
            font=ctk.CTkFont(size=10, family="Courier"), text_color=COLORS["text_dim"], anchor="w"
        )
        mac_lbl.pack(side="left", padx=(6, 2))

        # Üretici
        vendor_text = device.vendor[:18] + "..." if len(device.vendor) > 20 else device.vendor
        vendor_lbl = ctk.CTkLabel(
            row_frame, text=vendor_text, width=self.COLUMNS[4][1],
            font=ctk.CTkFont(size=11), text_color=COLORS["text"], anchor="w"
        )
        vendor_lbl.pack(side="left", padx=(6, 2))

        # Cihaz Türü
        type_lbl = ctk.CTkLabel(
            row_frame, text=device.device_type, width=self.COLUMNS[5][1],
            font=ctk.CTkFont(size=11), text_color=COLORS["warning"], anchor="w"
        )
        type_lbl.pack(side="left", padx=(6, 2))

        # İlk Görülme
        first_lbl = ctk.CTkLabel(
            row_frame, text=device.first_seen, width=self.COLUMNS[6][1],
            font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"], anchor="w"
        )
        first_lbl.pack(side="left", padx=(6, 2))

        # Son Görülme
        last_lbl = ctk.CTkLabel(
            row_frame, text=device.last_seen, width=self.COLUMNS[7][1],
            font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"], anchor="w"
        )
        last_lbl.pack(side="left", padx=(6, 2))

        # Pil
        battery_text = "N/A"
        battery_color = COLORS["text_dim"]
        if device.is_local and device.battery_percent is not None:
            battery_text = f"{device.battery_percent}%"
            if device.battery_plugged:
                battery_text += " ⚡"
            if device.battery_percent > 50:
                battery_color = COLORS["online"]
            elif device.battery_percent > 20:
                battery_color = COLORS["warning"]
            else:
                battery_color = COLORS["offline"]

        battery_lbl = ctk.CTkLabel(
            row_frame, text=battery_text, width=self.COLUMNS[8][1],
            font=ctk.CTkFont(size=11), text_color=battery_color, anchor="w"
        )
        battery_lbl.pack(side="left", padx=(6, 2))

        self._rows.append(row_frame)


class NetworkMonitorApp(ctk.CTk):
    """Ana Uygulama Penceresi."""

    def __init__(self):
        super().__init__()

        # Pencere ayarları
        self.title("🌐 Ağ İzleme Uygulaması - Network Monitor")
        self.geometry("1320x780")
        self.minsize(1100, 600)
        self.configure(fg_color=COLORS["bg_dark"])

        # Scanner
        self.scanner = NetworkScanner()

        # Durum değişkenleri
        self._auto_scan_active = False
        self._auto_scan_thread: Optional[threading.Thread] = None
        self._scan_thread: Optional[threading.Thread] = None

        # UI oluştur
        self._create_ui()

        # Admin uyarısı
        self.after(500, self._check_admin_warning)

    def _create_ui(self):
        """Tüm UI bileşenlerini oluştur."""
        # === ÜST PANEL: Başlık & Bilgi ===
        self._create_top_panel()

        # === ORTA PANEL: Tablo ===
        self._create_table_panel()

        # === ALT PANEL: Kontroller & Durum ===
        self._create_bottom_panel()

    def _create_top_panel(self):
        """Üst bilgi paneli."""
        top_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=110)
        top_frame.pack(fill="x", padx=12, pady=(12, 6))
        top_frame.pack_propagate(False)

        # Sol: Başlık
        left_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=16, pady=10)

        title_lbl = ctk.CTkLabel(
            left_frame, text="🌐 Ağ İzleme Uygulaması",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=COLORS["text"]
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            left_frame, text="Yerel ağınızdaki cihazları tespit edin ve izleyin",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"]
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        platform_text = f"Platform: {platform.system()} {platform.release()} | Python {platform.python_version()}"
        platform_lbl = ctk.CTkLabel(
            left_frame, text=platform_text,
            font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]
        )
        platform_lbl.pack(anchor="w", pady=(2, 0))

        # Sağ: İstatistikler
        right_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=16, pady=10)

        # İstatistik kartları
        stats_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        stats_frame.pack(anchor="e")

        self.stat_total = self._create_stat_card(stats_frame, "Toplam", "0", COLORS["text"])
        self.stat_total.pack(side="left", padx=6)

        self.stat_online = self._create_stat_card(stats_frame, "Online", "0", COLORS["online"])
        self.stat_online.pack(side="left", padx=6)

        self.stat_offline = self._create_stat_card(stats_frame, "Offline", "0", COLORS["offline"])
        self.stat_offline.pack(side="left", padx=6)

        # Yerel IP bilgisi
        self.local_info_lbl = ctk.CTkLabel(
            right_frame, text="Yerel IP: -  |  Ağ: -",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]
        )
        self.local_info_lbl.pack(anchor="e", pady=(6, 0))

    def _create_stat_card(self, parent, label: str, value: str, color: str) -> ctk.CTkFrame:
        """İstatistik kartı oluştur."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["accent"], corner_radius=8, width=90, height=60)
        card.pack_propagate(False)

        val_lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold"), text_color=color)
        val_lbl.pack(pady=(8, 0))
        card._value_label = val_lbl

        name_lbl = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"])
        name_lbl.pack()

        return card

    def _update_stat_card(self, card: ctk.CTkFrame, value: str):
        """İstatistik kartını güncelle."""
        card._value_label.configure(text=value)

    def _create_table_panel(self):
        """Tablo paneli."""
        table_outer = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10)
        table_outer.pack(fill="both", expand=True, padx=12, pady=6)

        self.device_table = DeviceTableFrame(
            table_outer,
            fg_color=COLORS["bg_dark"],
            corner_radius=6,
        )
        self.device_table.pack(fill="both", expand=True, padx=6, pady=6)

    def _create_bottom_panel(self):
        """Alt kontrol paneli."""
        bottom_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10, height=130)
        bottom_frame.pack(fill="x", padx=12, pady=(6, 12))
        bottom_frame.pack_propagate(False)

        # --- Üst satır: Butonlar ---
        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Manuel Tarama
        self.scan_btn = ctk.CTkButton(
            btn_frame, text="🔍 Taramayı Başlat", width=160, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["button_primary"], hover_color="#0878cc",
            command=self._on_scan_click
        )
        self.scan_btn.pack(side="left", padx=(0, 8))

        # Durdur
        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ Durdur", width=100, height=36,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["button_danger"], hover_color="#c0392b",
            command=self._on_stop_click, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        # Otomatik Tarama
        self.auto_scan_var = ctk.BooleanVar(value=False)
        self.auto_scan_check = ctk.CTkCheckBox(
            btn_frame, text="Otomatik Tarama",
            variable=self.auto_scan_var,
            font=ctk.CTkFont(size=12),
            command=self._on_auto_scan_toggle
        )
        self.auto_scan_check.pack(side="left", padx=(16, 8))

        # Aralık
        interval_lbl = ctk.CTkLabel(btn_frame, text="Aralık (sn):", font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"])
        interval_lbl.pack(side="left", padx=(8, 4))

        self.interval_var = ctk.StringVar(value="60")
        self.interval_entry = ctk.CTkEntry(
            btn_frame, width=60, height=30, textvariable=self.interval_var,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.interval_entry.pack(side="left", padx=(0, 16))

        # Separator
        sep = ctk.CTkFrame(btn_frame, width=2, height=30, fg_color=COLORS["border"])
        sep.pack(side="left", padx=8)

        # Dışa Aktarma
        self.export_csv_btn = ctk.CTkButton(
            btn_frame, text="📄 CSV", width=80, height=36,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["button_success"], hover_color="#00a384",
            command=lambda: self._on_export("csv")
        )
        self.export_csv_btn.pack(side="left", padx=(0, 6))

        self.export_json_btn = ctk.CTkButton(
            btn_frame, text="📋 JSON", width=80, height=36,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["button_success"], hover_color="#00a384",
            command=lambda: self._on_export("json")
        )
        self.export_json_btn.pack(side="left", padx=(0, 6))

        # Tema değiştir
        self.theme_btn = ctk.CTkButton(
            btn_frame, text="🌙", width=36, height=36,
            font=ctk.CTkFont(size=16),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_light"],
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right")

        # --- Alt satır: İlerleme & Durum ---
        status_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            status_frame, width=400, height=14,
            progress_color=COLORS["button_primary"],
            fg_color=COLORS["progress_bg"]
        )
        self.progress_bar.pack(side="left", padx=(0, 12))
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            status_frame, text="Tarama için butona basın veya otomatik taramayı etkinleştirin.",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"], anchor="w"
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)

        # Admin durumu
        admin_text = "🔓 Admin" if self.scanner.has_admin else "🔒 Normal Kullanıcı"
        admin_color = COLORS["online"] if self.scanner.has_admin else COLORS["warning"]
        self.admin_lbl = ctk.CTkLabel(
            status_frame, text=admin_text,
            font=ctk.CTkFont(size=11, weight="bold"), text_color=admin_color
        )
        self.admin_lbl.pack(side="right", padx=(12, 0))

    def _check_admin_warning(self):
        """Admin değilse uyarı göster."""
        if not self.scanner.has_admin:
            self.status_lbl.configure(
                text="⚠ Root/Admin yetkisi yok. Ping taramas\u0131 kullanılacak (daha yavaş). "
                     "ARP taraması için root/admin olarak çalıştırın.",
                text_color=COLORS["warning"]
            )

    def _on_scan_click(self):
        """Manuel tarama butonu tıklandığında."""
        if self.scanner.is_scanning:
            return
        self._start_scan()

    def _start_scan(self):
        """Taramayı başlat."""
        self.scan_btn.configure(state="disabled", text="⏳ Taranıyor...")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)

        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()

    def _scan_worker(self):
        """Tarama iş parçacığı."""
        def progress_cb(message: str, percent: int):
            self.after(0, lambda: self._update_progress(message, percent))

        self.scanner.scan(progress_callback=progress_cb)
        self.after(0, self._on_scan_complete)

    def _update_progress(self, message: str, percent: int):
        """İlerleme güncelle (GUI thread'inde)."""
        self.status_lbl.configure(text=message, text_color=COLORS["text"])
        if 0 <= percent <= 100:
            self.progress_bar.set(percent / 100.0)

    def _on_scan_complete(self):
        """Tarama tamamlandığında."""
        self.scan_btn.configure(state="normal", text="🔍 Taramayı Başlat")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(1.0)

        # Tabloyu güncelle
        self._refresh_table()

        # Yerel bilgi güncelle
        local_ip = self.scanner._local_ip
        network = self.scanner._network_cidr
        self.local_info_lbl.configure(text=f"Yerel IP: {local_ip}  |  Ağ: {network}")

    def _refresh_table(self):
        """Cihaz tablosunu güncelle."""
        self.device_table.clear()
        devices = self.scanner.get_devices_list()

        online_count = sum(1 for d in devices if d.status == "Online")
        offline_count = sum(1 for d in devices if d.status == "Offline")

        for idx, device in enumerate(devices):
            self.device_table.add_device(device, idx)

        # İstatistikleri güncelle
        self._update_stat_card(self.stat_total, str(len(devices)))
        self._update_stat_card(self.stat_online, str(online_count))
        self._update_stat_card(self.stat_offline, str(offline_count))

    def _on_stop_click(self):
        """Durdur butonu."""
        self.scanner.stop_scan()
        self.status_lbl.configure(text="Tarama durduruldu.", text_color=COLORS["warning"])
        self.scan_btn.configure(state="normal", text="🔍 Taramayı Başlat")
        self.stop_btn.configure(state="disabled")

    def _on_auto_scan_toggle(self):
        """Otomatik tarama toggle."""
        if self.auto_scan_var.get():
            self._auto_scan_active = True
            self._auto_scan_thread = threading.Thread(target=self._auto_scan_worker, daemon=True)
            self._auto_scan_thread.start()
            self.status_lbl.configure(text="Otomatik tarama etkinleştirildi.", text_color=COLORS["online"])
        else:
            self._auto_scan_active = False
            self.status_lbl.configure(text="Otomatik tarama devre dışı.", text_color=COLORS["text_dim"])

    def _auto_scan_worker(self):
        """Otomatik tarama iş parçacığı."""
        while self._auto_scan_active:
            if not self.scanner.is_scanning:
                self.after(0, self._start_scan)

            # Aralık bekle
            try:
                interval = int(self.interval_var.get())
                if interval < 10:
                    interval = 10
            except ValueError:
                interval = 60

            # Bekleme sırasında iptal kontrolü
            for _ in range(interval):
                if not self._auto_scan_active:
                    return
                time.sleep(1)

    def _on_export(self, fmt: str):
        """Dışa aktarma."""
        devices = self.scanner.get_devices_list()
        if not devices:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak cihaz bulunamadı.\nÖnce bir tarama yapın.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if fmt == "csv":
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Dosyası", "*.csv")],
                initialfile=f"network_scan_{timestamp}.csv"
            )
            if filepath:
                try:
                    export_to_csv(devices, filepath)
                    messagebox.showinfo("Başarılı", f"CSV dosyası kaydedildi:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Hata", f"CSV kaydetme hatası:\n{e}")
        elif fmt == "json":
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Dosyası", "*.json")],
                initialfile=f"network_scan_{timestamp}.json"
            )
            if filepath:
                try:
                    export_to_json(devices, filepath)
                    messagebox.showinfo("Başarılı", f"JSON dosyası kaydedildi:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Hata", f"JSON kaydetme hatası:\n{e}")

    def _toggle_theme(self):
        """Tema değiştir."""
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="☀️")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="🌙")


def main():
    """Uygulamayı başlat."""
    app = NetworkMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
