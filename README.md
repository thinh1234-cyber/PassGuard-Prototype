<div align="center">

<img src="assets/icon.png" alt="Logo" width="120">

# LuuPass Vault

> Ứng dụng quản lý mật khẩu cá nhân Offline-first • An toàn • Không Cloud

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()
[![Flet](https://img.shields.io/badge/UI-Flet-green.svg)]()

[Features](#-tính-năng) • [Install](#-cài-đặt) • [Usage](#-hướng-dẫn-sử-dụng) • [Architecture](#-kiến-trúc) • [Security](#-giới-hạn-bảo-mật)

</div>

---

## 🎯 Tổng quan

LuuPass là ứng dụng quản lý mật khẩu cá nhân theo hướng **offline-first**. Dữ liệu được lưu trong một file vault mã hóa cục bộ, hoàn toàn không cần cloud server và không đồng bộ tự động qua Internet.

Dự án được thiết kế với mục tiêu bảo vệ dữ liệu *at-rest* bằng các tiêu chuẩn mã hóa mạnh nhất hiện nay, đảm bảo an toàn tối đa cho file vault của bạn khi đang ở trạng thái khóa.

---

## ✨ Tính năng

### 🔐 Cryptography & Security
| Tính năng | Mô tả |
|-----------|-------|
| 🛡️ **A2G1 Format** | Mã hóa chuẩn `Argon2id` (KDF) + `AES-256-GCM` (AEAD). Payload header được authenticate bằng AAD. |
| 🔄 **Backward Compat**| Vẫn hỗ trợ đọc vault legacy `GCM1` (PBKDF2-SHA256) và payload Fernet cũ. |
| 🌐 **Local Web Security**| Chế độ `--web` bind riêng `127.0.0.1` với route token ngẫu nhiên (chống unauthorized access). |
| 📋 **Auto-clear** | Copy username/password tự động xóa clipboard sau 15 giây; lock vault sẽ clear clipboard ngay. |
| ⏱️ **Idle Auto-lock** | Tự lock vault sau thời gian không hoạt động, giảm rủi ro để quên session đang mở. |

### 💾 Storage & Data Management
| Tính năng | Mô tả |
|-----------|-------|
| ⚡ **Safe Save** | Ghi dữ liệu ra `.tmp` trước khi atomic replace file vault chính, chống hỏng file khi mất điện. |
| 🏥 **Healing Mode** | Auto rotate tối đa 3 bản backup (`.bak`). Tự động khôi phục từ backup nếu vault chính bị hỏng/xóa. |
| 📥 **Safe Import** | Yêu cầu password của file import để validate trước khi ghi đè vault hiện tại. Tự động re-encrypt. |
| 🩺 **Backup Diagnostics** | Settings có kiểm tra backup valid/corrupt/missing bằng password session hiện tại. |

### 🎨 Core UI (Flet)
| Tính năng | Mô tả |
|-----------|-------|
| 🔍 **Instant Search** | Tìm kiếm realtime theo platform, URL hoặc username. |
| 🧬 **Password Generator** | Sinh password offline cho từng account, tránh phụ thuộc dịch vụ bên ngoài. |
| 🖼️ **Offline Favicon** | Tự động sinh icon dựa trên tên nền tảng, không gọi API ngoài (chống tracking). |
| 📱 **Cross-platform** | Chạy mượt mà trên Windows (.exe), Web Local, và Android (Termux). |

---

## 📦 Cài đặt

### Windows Portable
1. Mở thư mục `dist/`.
2. Chạy `LuuPass.exe` (Mở như một cửa sổ desktop độc lập).
> **Build lại bản Windows:** Chạy lệnh `.\build.ps1 -Windows` trong PowerShell.

### Chạy từ Source (Windows/Linux/macOS)
```bash
pip install -r requirements.txt
python main.py
```

### Android (thông qua Termux)
```bash
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/thinh1234-cyber/luu_pass.git
cd luu_pass
pip install -r requirements.txt
python main.py --web
```
*Khi chạy `--web`, terminal sẽ in ra link local dạng `http://127.0.0.1:8550/<token>`. Nên mở link này trong tab Ẩn danh (Incognito) của trình duyệt mobile.*

---

## 📖 Hướng dẫn sử dụng

### Quản lý Dữ liệu
- **File vault mặc định:** `vault.luupass`.
- **Backup local:** `vault.luupass.bak1`, `.bak2`, `.bak3`.
- **Export:** Copy chính xác file vault hiện tại ra vị trí bạn chọn (hỗ trợ Folder Picker trên desktop).
- **Import:** Nhập file vault `.luupass` khác. Hệ thống sẽ hỏi password của file import, validate trước, rotate backup vault hiện tại rồi lưu vault import bằng master password đang unlock.
- **Change master password:** Yêu cầu current password, new password và confirm password. App verify payload mới trước khi xóa backup cũ.

### Git Hygiene
Vault và backup không bao giờ nên commit lên Git. `.gitignore` đã cấu hình chặn:
```gitignore
*.luupass
*.luupass.bak*
*.luupass.tmp
```
> ⚠️ **Cảnh báo:** Nếu `vault.luupass` từng bị commit/push lên remote, hãy coi ciphertext đã bị lộ và nên đổi master password ngay lập tức, hoặc purge Git history.

### Update Check & Release Integrity
Update check phải là thao tác **opt-in** của user. Module `src/update_checker.py` mặc định đọc tag version bằng `git ls-remote --tags --refs https://github.com/thinh1234-cyber/luu_pass.git`, parse version tag, và so sánh với `APP_VERSION`. Nếu repo chưa có tag version, app fallback sang so sánh `remote HEAD` với `local HEAD`. App không tự `git pull`, tự cài, hoặc chạy code từ Internet.

Khi tải release thủ công, dùng file `SHA256SUMS` đi kèm release để kiểm tra artifact local trước khi chạy:
```python
from src.update_checker import parse_sha256sums, sha256_file

checksums = parse_sha256sums(sha256sums_text)
assert sha256_file("LuuPass.exe") == checksums["LuuPass.exe"]
```

---

## 🏗 Kiến trúc

### Cấu trúc thư mục
```
├── src/
│   ├── models.py         # Pydantic data models (Vault, Entry, Account)
│   ├── crypto.py         # KDF (Argon2id) & Encryption (AES-GCM) engine
│   ├── storage.py        # File I/O, Atomic Save & Healing Mode
│   └── ui/
│       └── dashboard.py  # Flet UI Components & State management
├── tests/
│   └── test_storage.py   # Pytest suite cho Storage & Crypto
├── main.py               # Entry point & Local Web Server binding
├── build.ps1             # Script build file executable (Windows)
├── architecture.md       # Tài liệu thiết kế hệ thống chi tiết
└── requirements.txt      # Dependencies
```

---

## 🔧 Công nghệ

| Layer | Technology |
|-------|------------|
| **UI Framework** | Flet `0.85.3` (Flutter-based Python UI) |
| **Data Validation**| Pydantic v2 |
| **Cryptography** | `cryptography` (AES-GCM), `argon2-cffi` (Argon2id) |
| **Testing** | Pytest |

---

## 🛡️ Giới hạn bảo mật

LuuPass bảo vệ cực tốt khi file vault đang **khóa**. 
Khi vault đã được **unlock**, plaintext password sẽ tồn tại trong RAM/UI để phục vụ việc xem, sửa và copy. 

Vì vậy, nếu máy tính bị nghi nhiễm malware (infostealer, keylogger, screen capture, clipboard monitor), cách an toàn nhất là làm sạch HĐH hoặc sử dụng thiết bị khác an toàn hơn trước khi unlock vault.

---

## ✅ Verification
Chạy Unit Test để verify toàn bộ module mã hóa và lưu trữ:
```bash
python -m pytest -q
```

---

<div align="center">
<p>Made with ❤️ by <b>Kyle (Nguyễn Thịnh)</b></p>
</div>
