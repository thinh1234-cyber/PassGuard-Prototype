# LuuPass - Project Architecture

## 1. Tổng quan kiến trúc

LuuPass là ứng dụng quản lý mật khẩu cá nhân theo hướng **offline-first**: vault được lưu trong máy, không cần cloud server và không đồng bộ tự động qua Internet.

Mục tiêu bảo mật chính của dự án là bảo vệ **dữ liệu at-rest**: nếu file vault bị copy đi, kẻ tấn công vẫn phải vượt qua lớp mã hóa. LuuPass không thể đảm bảo an toàn tuyệt đối nếu hệ điều hành đang bị compromise bởi infostealer, keylogger, screen capture, clipboard monitor hoặc malware đọc RAM.

Dự án được chia thành 3 tầng chính:

1. **Storage & Data Layer**: Định nghĩa model vault và xử lý File I/O.
2. **Cryptography Layer**: Phái sinh key và mã hóa/giải mã payload.
3. **UI / Presentation Layer**: Quản lý hiển thị và tương tác người dùng bằng Flet.

---

## 2. Chi tiết các tầng

### 2.1. Data Models - `src/models.py`

Sử dụng **Pydantic v2** để validate và serialize dữ liệu:

- `Account`: Chứa `username` và `password`.
- `Entry`: Đại diện cho một platform, gồm `title`, `url`, `notes`, và danh sách `accounts`.
- `Vault`: Gốc của toàn bộ dữ liệu, chứa danh sách `entries`.

Khi save, `Vault` được serialize thành JSON bằng `model_dump_json()`. Khi load/import, plaintext JSON sau giải mã phải parse thành công qua `Vault.model_validate_json()` mới được chấp nhận.

### 2.2. Cryptography Layer - `src/crypto.py`

Format mã hóa mặc định hiện tại là **`A2G1`**:

- **AEAD:** `AES-256-GCM`.
- **KDF:** `Argon2id`.
- **Argon2id profile:** `time_cost=3`, `memory_cost=65536 KiB`, `parallelism=1`, `hash_len=32`.
- **KDF param bounds:** `time_cost`, `memory_cost_kib`, và `parallelism` có upper-bound để tránh file độc hại gây Local DoS khi decrypt.
- **Salt:** 16 bytes ngẫu nhiên.
- **Nonce:** 12 bytes ngẫu nhiên.
- **File format:** `4-byte magic ('A2G1')` + `time_cost` + `memory_cost_kib` + `parallelism` + `salt` + `nonce` + `ciphertext`.
- Ba tham số Argon2id được lưu dạng unsigned 32-bit big-endian để mỗi file tự mô tả được profile KDF cần dùng khi decrypt.
- **AAD:** Header không mã hóa (`magic`, KDF params, salt, nonce) được đưa vào AES-GCM Associated Data cho payload mới. Decrypt vẫn fallback đọc được `A2G1` giai đoạn đầu chưa có AAD.

Backward compatibility:

- `GCM1`: Legacy AES-GCM với `PBKDF2HMAC-SHA256`, 480,000 iterations.
- Legacy Fernet payload cũ: vẫn có fallback decrypt để tránh khóa mất vault cũ.
- Mỗi lần save mới sẽ ghi lại bằng `A2G1`, kể cả khi dữ liệu ban đầu được import từ format legacy.

### 2.3. Storage Layer - `src/storage.py`

- **Atomic Save:** Dữ liệu được encrypt, ghi vào file `.tmp`, sau đó thay thế file vault bằng `os.replace()`.
- **Backup Rotation:** Save thông thường giữ tối đa 3 backup: `.bak1`, `.bak2`, `.bak3`.
- **Healing Mode:** Nếu vault chính bị hỏng hoặc bị xóa nhưng backup decrypt/parse thành công với password đang nhập, app có thể khôi phục từ backup.
- **Safe Import:** File import phải decrypt bằng password của file import và parse thành `Vault` thành công trước khi overwrite vault hiện tại.
- **Re-encrypt On Import:** Vault import hợp lệ sẽ được save lại bằng format `A2G1`.
- **Clear Backups On Root Secret Change:** Import vault và change master password xóa backup cũ trước khi ghi file mới, tránh trường hợp backup cũ vẫn mở được bằng password cũ.
- **Git Hygiene:** `.gitignore` chặn `*.luupass`, `*.luupass.bak*`, và `*.luupass.tmp`; file vault không nên nằm trong Git index.

### 2.4. UI Layer - `main.py` và `src/ui/dashboard.py`

UI dùng **Flet** cho desktop native và local web mode:

- **Local Web Binding:** Khi chạy `--web`, server bind vào `127.0.0.1`, không mở port LAN.
- **Session Route Token:** App sinh `secrets.token_urlsafe(16)` và yêu cầu URL dạng `http://127.0.0.1:8550/<token>`.
- **Clipboard Auto-clear:** Copy username/password sẽ tự clear clipboard sau 15 giây.
- **Safe Import Dialog:** Khi chọn file import, UI hỏi `Import Vault Password`, sau đó gọi storage validate/import. Nếu password sai hoặc file corrupt, vault hiện tại không bị thay đổi.
- **Dynamic Export Path:** Dashboard nhận `storage.filepath` từ `main.py`, nên export dùng đúng vault hiện tại thay vì hardcode `vault.luupass`.
- **Clipboard Timer Reset:** Mỗi lần copy sẽ hủy timer clear clipboard cũ rồi đặt timer 15 giây mới, tránh xóa clipboard sớm khi user copy liên tiếp.
- **State:** Khi unlock, master password và plaintext `Vault` tồn tại trong RAM để cho phép save/edit. Đây là tradeoff UX và là rủi ro nếu máy đang nhiễm malware.

---

## 3. Luồng hoạt động

### 3.1. Unlock

1. User nhập Master Password.
2. `storage.load()` đọc `vault.luupass`.
3. `crypto.decrypt()` nhận diện header: `A2G1`, `GCM1`, hoặc legacy Fernet.
4. Sinh key bằng Argon2id hoặc legacy PBKDF2 tùy theo format.
5. AES-GCM/Fernet decrypt và verify integrity.
6. Plaintext JSON được validate bằng Pydantic thành `Vault`.
7. Dashboard hiển thị dữ liệu plaintext trong RAM.

### 3.2. Save

1. UI cập nhật object `Vault` trong RAM.
2. Khi save, `Vault` serialize thành JSON.
3. `crypto.encrypt()` tạo payload `A2G1` mới với salt/nonce mới.
4. `storage.save()` rotate backup nếu là save thông thường, sau đó atomic replace vault chính.

### 3.3. Import

1. User chọn file `.luupass` cần import.
2. UI hỏi password của file import.
3. `storage.validate_import_file()` decrypt và parse file import.
4. Nếu validate fail, vault hiện tại giữ nguyên.
5. Nếu validate pass, app xóa backup cũ và save vault import bằng `A2G1`.
6. App lock lại để user unlock bằng password của vault import.

---

## 4. Threat Model thực tế

LuuPass phù hợp để giảm rủi ro khi:

- File vault bị copy, đồng bộ nhầm, hoặc bị lấy từ ổ đĩa.
- Cần một password manager offline, không phụ thuộc cloud.
- Muốn tự quản lý backup/import/export một file mã hóa duy nhất.

LuuPass không giải quyết được hoàn toàn khi:

- Máy đang có infostealer, keylogger, clipboard monitor, screen capture, hoặc malware đọc RAM.
- User unlock vault trên OS không sạch.
- Password bị lộ qua browser history, screen recording, fake keyboard, hoặc clipboard trước khi auto-clear.

Khuyến nghị vận hành: chỉ unlock vault thật trên máy đã được làm sạch hoặc OS/thiết bị đáng tin cậy. Nếu vault từng nằm trong Git remote, cần coi ciphertext đã lộ và nên đổi master password hoặc purge history.

---

*LuuPass Architecture v3.0 - Offline-first, Argon2id-hardened, safe-import aware.*
