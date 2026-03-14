# 🌐 Ağ İzleme Uygulaması (Network Monitor)

Cross-platform (Windows & Linux) çalışan, yerel ağınızdaki cihazları tespit eden ve izleyen modern masaüstü uygulaması.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-orange)

---

## 📋 Özellikler

- **Ağ Tarama**: ARP (root/admin) veya Ping tabanlı cihaz keşfi
- **Cihaz Bilgileri**: IP adresi, hostname, MAC adresi, üretici firma, cihaz türü tahmini
- **Durum İzleme**: Online/Offline durumu, ilk ve son görülme zamanı
- **Otomatik Tarama**: Ayarlanabilir aralıklarla periyodik tarama
- **Pil Durumu**: Yerel bilgisayarın şarj bilgisi
- **Dışa Aktarma**: CSV ve JSON formatlarında rapor oluşturma
- **Modern Arayüz**: CustomTkinter ile karanlık/aydınlık tema desteği
- **Cross-Platform**: Windows ve Linux'ta sorunsuz çalışır

---

## 🛠 Kurulum

### Gereksinimler

- Python 3.8 veya üstü
- pip (Python paket yöneticisi)

### Linux Kurulumu

```bash
# 1. Projeyi klonlayın veya indirin
cd network_monitor

# 2. Sanal ortam oluşturun (önerilen)
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Uygulamayı çalıştırın
# Normal kullanıcı olarak (ping taraması):
python3 main.py

# Root olarak (ARP taraması - daha hızlı ve güvenilir):
sudo python3 main.py
# veya sanal ortam ile:
sudo venv/bin/python main.py
```

#### Linux için ek notlar:
- `tkinter` sisteminizde yoksa: `sudo apt install python3-tk` (Debian/Ubuntu) veya `sudo dnf install python3-tkinter` (Fedora)
- ARP taraması için root yetkisi gereklidir. Root olmadan uygulama ping taraması kullanır. Eğer ki customtkinter sistemde bulunamazsa `pip install customtkinter`(Debian/Ubuntu)

### Windows Kurulumu

```powershell
# 1. Projeyi klonlayın veya indirin
cd network_monitor

# 2. Sanal ortam oluşturun (önerilen)
python -m venv venv
venv\Scripts\activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Uygulamayı çalıştırın
# Normal kullanıcı:
python main.py

# Yönetici olarak (önerilen - ARP taraması için):
# Komut istemini "Yönetici olarak çalıştır" ile açıp tekrar çalıştırın
python main.py
```

#### Windows için ek notlar:
- Windows'ta Npcap veya WinPcap kurulu olmalıdır (Scapy ARP taraması için).
  İndirme: https://npcap.com/
- Npcap olmadan uygulama ping taraması kullanır (biraz daha yavaş ama çalışır).
- Windows Defender Güvenlik Duvarı uyarı verebilir - "Erişime izin ver" seçin.

---

## 🚀 Kullanım

### Manuel Tarama
1. Uygulamayı başlatın
2. **"🔍 Taramayı Başlat"** butonuna tıklayın
3. Tarama tamamlanınca cihaz listesi tabloda görünecektir

### Otomatik Tarama
1. **"Otomatik Tarama"** kutucuğunu işaretleyin
2. **"Aralık (sn)"** alanına tarama sıklığını saniye cinsinden girin (minimum 10 sn)
3. Uygulama belirtilen aralıklarla otomatik tarama yapacaktır

### Dışa Aktarma
- **CSV**: "📄 CSV" butonuyla Excel/tablolama uyumlu format
- **JSON**: "📋 JSON" butonuyla yapılandırılmış veri formatı

### Tema Değiştirme
- Sağ alttaki 🌙/☀️ butonuyla karanlık/aydınlık tema arasında geçiş yapın

---

## 📊 Gösterilen Bilgiler

| Bilgi | Açıklama |
|-------|----------|
| Durum | Online (●) / Offline (●) |
| IP Adresi | Cihazın yerel ağ IP'si (★ = yerel bilgisayar) |
| Cihaz Adı | DNS hostname |
| MAC Adresi | Fiziksel ağ adresi |
| Üretici | MAC adresinden tespit edilen firma |
| Cihaz Türü | Tahmin edilen cihaz kategorisi |
| İlk Görülme | Cihazın ilk tespit edildiği zaman |
| Son Görülme | Cihazın son kez online görüldüğü zaman |
| Pil | Yerel bilgisayarın pil durumu (varsa) |

---

## 📦 Executable Oluşturma (PyInstaller)

### Linux

```bash
pip install pyinstaller
pyinstaller --onefile --windowed \
  --name="NetworkMonitor" \
  --add-data="mac_vendor.py:." \
  --add-data="scanner.py:." \
  --add-data="exporter.py:." \
  --hidden-import=customtkinter \
  --hidden-import=psutil \
  --hidden-import=scapy \
  --hidden-import=mac_vendor_lookup \
  main.py
```

Oluşan executable: `dist/NetworkMonitor`

### Windows

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed ^
  --name="NetworkMonitor" ^
  --add-data="mac_vendor.py;." ^
  --add-data="scanner.py;." ^
  --add-data="exporter.py;." ^
  --hidden-import=customtkinter ^
  --hidden-import=psutil ^
  --hidden-import=scapy ^
  --hidden-import=mac_vendor_lookup ^
  --icon=NONE ^
  main.py
```

Oluşan executable: `dist\NetworkMonitor.exe`

> **Not**: PyInstaller ile oluşturulan executable'ı yönetici/root olarak çalıştırmanız ARP tarama özelliği için önerilir.

---

## 🏗 Proje Yapısı

```
network_monitor/
├── main.py              # Ana uygulama & GUI
├── scanner.py           # Ağ tarama motoru
├── mac_vendor.py        # MAC üretici veritabanı
├── exporter.py          # CSV/JSON dışa aktarma
├── requirements.txt     # Python bağımlılıkları
└── README.md            # Bu dosya
```

---

## ⚠️ Bilinen Sınırlamalar

1. **Pil Durumu**: Sadece uygulamanın çalıştığı yerel bilgisayar için gösterilebilir
2. **Cihaz Türü**: Tahmin bazlıdır; %100 doğruluk garanti edilmez
3. **MAC Adresi**: Farklı alt ağlardaki cihazların MAC adresi okunamayabilir
4. **ARP Taraması**: Root/Admin yetkisi gerektirir; aksi halde ping taraması kullanılır
5. **Güvenlik Duvarı**: Bazı cihazlar ping'e yanıt vermeyebilir

---

## 📄 Lisans

Bu proje eğitim ve kişisel kullanım amaçlıdır.
