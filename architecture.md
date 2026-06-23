# LuuPass - Project Architecture

## 1. Tổng quan Kiến trúc (Overview)
LuuPass là một ứng dụng quản lý mật khẩu được thiết kế theo kiến trúc **Offline-first (100% Nội bộ)** và **Cross-platform (Đa nền tảng)**, đảm bảo bảo mật tuyệt đối cho dữ liệu cá nhân mà không phụ thuộc vào bất kỳ máy chủ đám mây (Cloud Server) nào.

Dự án được chia làm 3 tầng (Layers) chính để đảm bảo tính Module hóa, dễ bảo trì và mở rộng:

1. **Tầng Lưu trữ & Dữ liệu (Storage & Data Layer)**: Định nghĩa cấu trúc dữ liệu và xử lý File I/O.
2. **Tầng Mã hóa (Cryptography Layer)**: Trái tim bảo mật của hệ thống.
3. **Tầng Giao diện Người dùng (UI / Presentation Layer)**: Quản lý hiển thị và tương tác người dùng qua Flet.

---

## 2. Chi tiết các Tầng (Layers)

### 2.1. Tầng Dữ liệu (Data Models)
Sử dụng thư viện **Pydantic (v2)** để thiết lập cấu trúc chặt chẽ (Strict Typing) và tự động Validate (Kiểm tra hợp lệ) dữ liệu:
- `Account`: Chứa `username` và `password`.
- `Entry`: Tượng trưng cho 1 nền tảng (Platform), gồm `title`, `url`, `notes`, và một List các `Account`.
- `Vault`: Gốc của toàn bộ dữ liệu, chứa List các `Entry`.

=> Khi cần lưu, Pydantic dễ dàng Serialize toàn bộ cây `Vault` này thành 1 chuỗi JSON duy nhất (`model_dump_json`).

### 2.2. Tầng Mã hóa (Cryptography Layer - `src/crypto.py`)
Kiến trúc mã hóa tuân thủ nghiêm ngặt các tiêu chuẩn bảo mật hiện đại:
- **Thuật toán chính:** `AES-256-GCM` (Authenticated Encryption with Associated Data).
- **Key Derivation (Phái sinh khóa):** Sử dụng `PBKDF2HMAC` kết hợp với chuẩn Hash `SHA256` qua `480,000` vòng lặp (Iterations) để chống lại các cuộc tấn công Brute-force/Dictionary.
- **Bảo mật thành phần:** 
  - `Salt` (16 bytes): Sinh ngẫu nhiên (`os.urandom`) cho mỗi lần Save, làm Key derivation luôn thay đổi.
  - `Nonce` (12 bytes): Sinh ngẫu nhiên chống tấn công Replay Attack.
- **Cấu trúc File (Payload Formatter):** `4-byte Header ('GCM1')` + `16-byte Salt` + `12-byte Nonce` + `Ciphertext (kèm Auth Tag)`.

### 2.3. Tầng Lưu trữ (Storage Layer - `src/storage.py`)
- **Atomic Save (Safe Save):** Cơ chế ghi file theo nguyên tắc: "Ghi ra file `.tmp` trước, ghi xong mới thay thế file gốc `.luupass`". Tuyệt đối không bao giờ làm hỏng dữ liệu dù app crash giữa chừng hay cúp điện.
- **Healing Mode (Tự phục hồi):** Tự động duy trì 3 phiên bản Backup (File `.bak1`, `.bak2`, `.bak3`). Khi hàm Load phát hiện file gốc bị lỗi (Corrupted / InvalidTag) nhưng mật khẩu đúng, nó sẽ tự động vét các file Backup để khôi phục lại dữ liệu chính.

### 2.4. Tầng Giao diện (UI Layer - `src/ui/dashboard.py` & `main.py`)
Sử dụng Framework **Flet** (Dựa trên Flutter Engine), đáp ứng mượt mà cả Desktop (Windows Native) và Web (Mobile Browser via Termux).
- **Phân tách State (State Management):** Truyền các hàm Callback (`on_save`, `on_lock`, `on_change_password`) từ `main.py` vào `Dashboard` để giữ luồng dữ liệu một chiều (One-way Data Flow).
- **Responsive Layout:** Tự động lắng nghe sự kiện `page.on_resize`. Nếu kích thước chiều rộng màn hình `< 800px` (Màn hình điện thoại), nó sẽ tự động chuyển từ chế độ "2 cột (Master-Detail)" sang chế độ "Ngăn xếp (Stack)", ẩn danh sách trái khi xem chi tiết.
- **Local Security (Bảo mật cục bộ):**
  - Giới hạn Binding IP (`127.0.0.1`), khóa chặt Port mạng LAN.
  - Sử dụng Token sinh ngẫu nhiên `secrets.token_urlsafe(16)` trong Session để chặn các tiến trình Local truy cập trái phép.
  - Auto-Clear Clipboard: Luồng chạy ngầm đếm ngược 15 giây để xóa bộ nhớ đệm chống Keylogger / Clipboard Monitor.

---

## 3. Luồng hoạt động (Data Flow)

### 3.1. Kịch bản Unlock (Mở khóa)
1. User nhập Master Password vào `main.py`.
2. `storage.load()` được gọi -> Đọc Byte từ `vault.luupass`.
3. Kiểm tra Header (`GCM1`). Tách Salt, Nonce, Ciphertext.
4. Sinh Key bằng PBKDF2.
5. Giải mã (Decrypt). Nếu sai Pass, Auth Tag báo `InvalidTag` -> Báo lỗi.
6. Nếu đúng Pass, trả về chuỗi JSON -> Pydantic Parse thành Object `Vault`.
7. Vẽ `Dashboard` UI dựa trên cây Object `Vault`.

### 3.2. Kịch bản Đóng gói (Save/Export)
1. Khi có sự thay đổi trên UI (Thêm/Sửa/Xóa Account), UI sửa trực tiếp trên biến Object trong RAM.
2. Bấm Save -> Pydantic dump từ Object thành JSON String.
3. Đẩy JSON String qua `crypto.encrypt()` để bọc lại thành gói Ciphertext mới toanh (với Salt và Nonce mới).
4. `storage.save()` thực hiện xoay tua Backup (Healing Mode) rồi đè File `.tmp` lên File gốc.

---

*LuuPass Architecture v2.0 - Designed for Simplicity, Built for Security.*
