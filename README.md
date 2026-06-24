# LuuPass

LuuPass là ứng dụng quản lý mật khẩu cá nhân theo hướng **offline-first**. Dữ liệu được lưu trong một file vault mã hóa local, không cần cloud server và không đồng bộ tự động qua Internet.

LuuPass được thiết kế để bảo vệ file vault khi đang khóa. Nếu máy đang nhiễm infostealer/keylogger/screen capture/clipboard monitor, không nên unlock vault thật trên máy đó.

## Tính năng chính

- **Argon2id + AES-256-GCM:** Save mới dùng format `A2G1` với Argon2id (`time_cost=3`, `memory_cost=65536 KiB`, `parallelism=1`) và AES-GCM authenticated encryption. Header payload mới được authenticate bằng AAD.
- **Backward Compatibility:** Vẫn đọc được vault legacy `GCM1` dùng PBKDF2-SHA256 480,000 iterations và payload Fernet cũ.
- **Safe Save:** Ghi vào `.tmp` trước, sau đó atomic replace file vault chính.
- **Backup Rotation + Healing:** Save thông thường giữ tối đa 3 backup `.bak1`, `.bak2`, `.bak3`; app có thể khôi phục từ backup nếu vault chính bị hỏng hoặc bị xóa.
- **Safe Import:** Import phải nhập password của file import; app decrypt và validate thành công mới overwrite vault hiện tại. Vault import sẽ được save lại bằng `A2G1`.
- **Local Web Security:** Chế độ `--web` bind vào `127.0.0.1` và dùng route token ngẫu nhiên.
- **Clipboard Auto-clear:** Copy username/password sẽ tự clear clipboard sau 15 giây; copy mới sẽ reset timer cũ.
- **Offline Favicons:** Không gọi Google Favicon/API bên ngoài; icon được sinh offline từ title.
- **Instant Search:** Tìm theo platform, URL, hoặc username.

## Cài đặt và chạy

### Windows portable

1. Mở thư mục `dist/`.
2. Chạy `LuuPass.exe`.
3. Ứng dụng mở như cửa sổ desktop riêng.

Build lại bản Windows:

```powershell
.\build.ps1 -Windows
```

### Chạy từ source

```powershell
pip install -r requirements.txt
python main.py
```

Dependencies chính:

- `flet`
- `cryptography`
- `pydantic`
- `argon2-cffi`
- `pytest`

### Android qua Termux

```bash
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/thinh1234-cyber/luu_pass.git
cd luu_pass
pip install -r requirements.txt
python main.py --web
```

Khi chạy `--web`, terminal sẽ in ra link local dạng:

```text
http://127.0.0.1:8550/<token>
```

Nên mở link này trong Incognito/private tab nếu dùng trình duyệt mobile.

## Quản lý dữ liệu

- File vault mặc định: `vault.luupass`.
- Backup local: `vault.luupass.bak1`, `.bak2`, `.bak3`.
- Export sẽ copy đúng file vault hiện tại ra vị trí bạn chọn, kể cả khi app được cấu hình dùng path khác `vault.luupass`.
- Import sẽ hỏi password của file import, validate trước, sau đó mới thay vault hiện tại.
- Sau import hoặc change master password, backup cũ bị xóa để tránh việc password cũ vẫn mở được dữ liệu từ `.bak`.

## Git hygiene

Vault và backup không nên commit lên Git. `.gitignore` đã chặn:

```gitignore
*.luupass
*.luupass.bak*
*.luupass.tmp
```

Nếu `vault.luupass` từng bị commit/push lên remote, hãy coi ciphertext đã lộ và nên đổi master password hoặc purge Git history.

## Verification

Chạy test:

```powershell
python -m pytest -q
```

Trạng thái hiện tại có test cho:

- Encrypt/decrypt `A2G1`.
- Reject wrong password và tampered ciphertext.
- Legacy `GCM1` và Fernet fallback.
- Safe import đúng/sai password.
- Import legacy vault và re-encrypt thành `A2G1`.

## Giới hạn bảo mật

LuuPass bảo vệ tốt hơn khi file vault đang khóa. Khi vault đã unlock, plaintext password tồn tại trong RAM/UI để phục vụ việc xem, sửa, copy và save. Vì vậy, trên máy nghi còn infostealer, cách dùng an toàn hơn là làm sạch OS hoặc dùng thiết bị sạch trước khi unlock vault và rotate password quan trọng.
