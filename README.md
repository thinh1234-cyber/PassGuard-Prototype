<div align="center">

# PassGuard Prototype

> Password manager offline-first cho vault cá nhân được mã hóa cục bộ.

Phiên bản 3.0.0 | Python 3.10+ | Flet UI | Local encrypted storage

[Tính năng](#tính-năng) | [Cài đặt](#cài-đặt) | [Build Android](#build-android-apk) | [Build Windows](#build-windows-exe) | [Bảo mật](#bảo-mật) | [Kiến trúc](#kiến-trúc)

</div>

---

## Tổng quan

PassGuard Prototype là ứng dụng quản lý mật khẩu nhẹ, ưu tiên sử dụng cục bộ. Dữ liệu được lưu trong một file vault đã mã hóa trên thiết bị, không cần cloud server và không tự động đồng bộ qua Internet.

Ứng dụng hỗ trợ chế độ desktop và local web, phù hợp để chạy trên Windows hoặc Android Termux trong khi vault vẫn nằm dưới quyền kiểm soát của người dùng.

---

## Tính năng

### Core

| Tính năng | Mô tả |
|-----------|-------|
| Encrypted vault | Lưu dữ liệu trong file `.passguard` được mã hóa cục bộ. |
| Multi-account entries | Lưu nhiều username/password trong cùng một platform hoặc service. |
| Password generator | Tạo mật khẩu mạnh offline, không cần dịch vụ bên ngoài. |
| Search | Tìm nhanh theo platform, URL hoặc username. |
| Light/Dark mode | Đổi giao diện sáng/tối trong Settings. |

### Security & Recovery

| Tính năng | Mô tả |
|-----------|-------|
| Modern encryption | Vault mới dùng `Argon2id` để derive key và `AES-256-GCM` để mã hóa. |
| Legacy vault support | Vẫn đọc được vault cũ định dạng `GCM1` và Fernet để hỗ trợ migration. |
| Atomic save | Ghi vault qua file tạm trước khi thay thế file chính. |
| Backup rotation | Giữ tối đa 3 file backup cục bộ để phục hồi. |
| Healing mode | Tự thử phục hồi từ backup hợp lệ nếu vault chính bị mất hoặc hỏng. |
| Clipboard auto-clear | Tự xóa dữ liệu đã copy sau một khoảng thời gian ngắn khi nền tảng hỗ trợ. |
| Idle auto-lock | Tự khóa vault sau thời gian không hoạt động. |

### Import, Export & Updates

| Tính năng | Mô tả |
|-----------|-------|
| Export vault | Xuất bản backup đã mã hóa dạng `vault_backup.passguard`. |
| Import vault | Validate vault import thành công rồi mới thay thế vault hiện tại. |
| Change master password | Re-encrypt vault bằng master password mới. |
| Backup diagnostics | Kiểm tra các backup slot còn đọc được hay không. |
| Opt-in update check | Chỉ kiểm tra GitHub release/tag hoặc remote HEAD khi người dùng yêu cầu. |

---

## Cài đặt

### Yêu cầu

- Python 3.10 trở lên
- Git, khuyến nghị dùng để clone project và check update

### Setup

```bash
git clone https://github.com/thinh1234-cyber/PassGuard-Prototype.git
cd PassGuard-Prototype
pip install -r requirements-dev.txt
python main.py
```

---

## Sử dụng

### Desktop Mode

```bash
python main.py
```

1. Nhập master password để mở vault hiện có hoặc tạo vault mới.
2. Tạo platform entry, sau đó thêm một hoặc nhiều account.
3. Save changes để ghi dữ liệu vào file vault đã mã hóa.
4. Vào Settings để export/import vault, đổi master password, verify backups hoặc check updates.
5. Dùng Lock Vault khi rời thiết bị, hoặc Shutdown để đóng app/server.

### Local Web Mode

```bash
python main.py --web
```

Ứng dụng bind vào `127.0.0.1` và in ra local URL có token, ví dụ:

```text
http://127.0.0.1:8550/<token>
```

Hãy mở đúng URL được in trong terminal. Import/export trên browser phụ thuộc vào khả năng file picker của trình duyệt và nền tảng đang dùng.

### Android Termux

```bash
pkg update && pkg upgrade
pkg install python git rust clang make binutils pkg-config openssl libffi
git clone https://github.com/thinh1234-cyber/PassGuard-Prototype.git
cd PassGuard-Prototype
export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)
pip install pydantic-core
pip install -r requirements-dev.txt
python main.py --web
```

## Build Android APK

APK là hướng chạy ưu tiên trên Android. Vault của APK được lưu trong app-private storage (`FLET_APP_STORAGE_DATA`), không nằm trong thư mục shared storage. Import và export dùng Android system document picker nên không cần quyền đọc/ghi storage diện rộng.

### Build trên GitHub

1. Push source lên nhánh `main`.
2. Mở repository trên GitHub, vào **Actions** và chọn **Build Android APK**.
3. Chọn `arm64-v8a` cho hầu hết điện thoại Android rồi bấm **Run workflow**.
4. Khi job xanh, tải APK trong phần **Artifacts**. Artifact được giữ 14 ngày.

Workflow chạy test trước khi build và chỉ đóng gói runtime dependencies. Không có vault, backup hoặc keystore trong workflow.

### Build local trên Windows

```powershell
python -m pip install -r requirements-dev.txt
.\build.ps1 -Target Apk -Arch arm64-v8a -Clean
```

APK nằm trong `release\android\`. Bản test tự ký để sideload; khi cần phát hành/update chính thức, dùng Android keystore riêng ngoài repository.

## Build Windows EXE

Từ thư mục project trên Windows, chạy:

```powershell
python -m pip install -r requirements-dev.txt
.\build.ps1
```

Kết quả là một file duy nhất tại:

```text
release\PassGuardPrototype.exe
```

File `.exe` có thể chép sang máy Windows khác và chạy trực tiếp, không cần cài Python. Lần chạy đầu tiên có thể chậm hơn một chút vì dạng single-file sẽ tự giải nén runtime tạm thời. Vault được tạo ở thư mục hiện hành, vì vậy nên đặt `.exe` trong một thư mục riêng trước khi bắt đầu dùng.

Khi cần xem lỗi runtime trong console trong lúc phát triển:

```powershell
.\build.ps1 -Clean -DebugConsole
```

Thư mục `release/` chỉ chứa artefact build và đã được Git ignore.

---

## Bảo mật

PassGuard Prototype bảo vệ dữ liệu mạnh nhất khi vault đang khóa. Nếu file `vault.passguard` bị sao chép, attacker vẫn cần master password để giải mã dữ liệu.

Khi vault đã unlock, plaintext credentials có thể tồn tại trong RAM, UI state và clipboard state để app có thể hiển thị, chỉnh sửa và copy. Không nên unlock vault thật trên thiết bị nghi nhiễm keylogger, clipboard monitor, screen capture malware hoặc malware có khả năng đọc memory.

Vault và backup không nên commit lên Git:

```gitignore
*.passguard
*.passguard.bak*
*.passguard.tmp
```

File vault mặc định:

```text
vault.passguard
vault.passguard.bak1
vault.passguard.bak2
vault.passguard.bak3
```

---

## Kiến trúc

### Cấu trúc project

```text
.
|-- main.py
|-- requirements.txt
|-- requirements-dev.txt
|-- pyproject.toml
|-- build.ps1
|-- .github/workflows/build-android.yml
|-- src/
|   |-- crypto.py
|   |-- models.py
|   |-- passwords.py
|   |-- storage.py
|   |-- update_checker.py
|   |-- version.py
|   `-- ui/
|       `-- dashboard.py
`-- tests/
    |-- test_advanced_crypto.py
    |-- test_crypto.py
    |-- test_models.py
    |-- test_passwords.py
    |-- test_storage.py
    `-- test_update_checker.py
```

### Công nghệ

| Layer | Technology |
|-------|------------|
| UI | Flet |
| Runtime | Python |
| Models | Pydantic |
| Key derivation | Argon2id |
| Encryption | AES-256-GCM |
| Storage | Local encrypted vault file |
| Tests | Pytest |


---
<div align="center">
<p>Made with ❤️ by <b>Nguyễn Thịnh - Kyle</b></p>
</div>
