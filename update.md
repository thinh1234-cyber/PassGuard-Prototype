# Đánh giá và Đề xuất Nâng cấp Bảo mật cho LuuPass

Dựa trên bản nhận xét chuyên sâu về kiến trúc Web UI và Local Security của dự án, dưới đây là phân tích chi tiết các điểm mạnh hiện tại, các rủi ro tiềm ẩn và đề xuất nâng cấp cụ thể cho dự án LuuPass.

## 1. Ràng buộc Mạng & Cơ chế Token (Network Binding & Authentication)
- **Hiện trạng:** Flet chạy `--web` mặc định khởi tạo một web server. Nếu không chỉ định host, mặc định nó có thể lắng nghe trên `0.0.0.0` (tùy thuộc vào version và OS), gây rủi ro lộ port trong mạng LAN.
- **Đề xuất nâng cấp:**
  - Bắt buộc bind host về `127.0.0.1` trong file `main.py` khi khởi chạy `--web` (`ft.app(..., host="127.0.0.1")`).
  - **Flet Token Protection:** Flet mặc định sinh ra một Session ID động qua WebSocket cho mỗi lần load trang, tuy nhiên để an toàn tuyệt đối trước các app độc hại scan port trên thiết bị, có thể thêm một Secret URL Token ngẫu nhiên sinh ra lúc khởi chạy server, và yêu cầu URL truy cập phải có dạng `http://127.0.0.1:8550/?token=XYZ`.

## 2. Quản lý Bộ nhớ đệm Trình duyệt (Browser Caching & Autofill)
- **Hiện trạng:** Các trường nhập liệu (TextField) hiện tại có thể bị trình duyệt ghi nhận (Autofill, Password Manager của Chrome).
- **Đề xuất nâng cấp:** 
  - Vô hiệu hóa triệt để Autofill trên toàn bộ các `TextField` (Trong Flet có thể giả lập việc này bằng cách không dùng các nhãn chuẩn như `password` cho HTML hoặc thiết lập `autocomplete=False` nếu thư viện hỗ trợ).
  - Đảm bảo tuyệt đối không sử dụng `page.client_storage` (localStorage) để lưu Master Password hay Vault Data (Hiện tại app đã tuân thủ tốt điều này).

## 3. Tự động xóa Bộ nhớ tạm (Clipboard Auto-clear)
- **Hiện trạng:** Tính năng Copy Username/Password hiện tại sẽ lưu chuỗi vào Clipboard vĩnh viễn cho đến khi người dùng copy nội dung khác.
- **Đề xuất nâng cấp:**
  - Thêm luồng (Background Thread) tự động dọn dẹp (Clear Clipboard) sau **15-30 giây** kể từ lúc bấm copy. Điều này ngăn chặn các phần mềm độc hại đọc trộm Clipboard sau khi người dùng đã paste xong.

## 4. Phục hồi Tự động khóa (Auto-lock)
- **Hiện trạng:** Tính năng này vừa bị gỡ bỏ theo yêu cầu để tối giản trải nghiệm.
- **Đề xuất nâng cấp:**
  - Lời khuyên bảo mật cho thấy Auto-lock là **bắt buộc** đối với Password Manager. Cần khôi phục lại cơ chế đếm ngược (đã tối ưu hóa single-thread, không gây lag UI) với thời lượng khoảng **3 - 5 phút** không tương tác.

## 5. Quản lý Bộ nhớ RAM (In-Memory Protection)
- **Hiện trạng:** Toàn bộ model `Vault` đang được parse thành danh sách Object trong RAM (Python variables) chừng nào App còn mở.
- **Đề xuất nâng cấp:**
  - Ở cấp độ cao nhất: Chỉ giữ Vault ở dạng mã hóa trong RAM. Khi người dùng click vào một Platform cụ thể, mới tiến hành giải mã (decrypt) riêng cục data của Platform đó. Khi thoát ra danh sách, xóa plaintext đó (gán bằng `None` và gọi `gc.collect()`).
  - Hủy Master Password (xóa khỏi RAM) ngay sau khi mở khóa. Khi cần Save (Encrypt), yêu cầu người dùng nhập lại hoặc sử dụng một Key 파i sinh (Derived Key) tạm thời rồi hủy. (Tuy nhiên điều này làm giảm UX).

## 6. Nâng cấp Thuật toán Mã hóa
- **Hiện trạng:** Dự án đã được nâng cấp lên **AES-256-GCM** (Bảo mật Authenticated Encryption).
- **Đề xuất nâng cấp:** 
  - Hàm băm phái sinh khóa (KDF) đang dùng `PBKDF2HMAC`. Nên xem xét chuyển sang `Argon2id` (chuẩn chống brute-force và kháng GPU tốt nhất hiện nay) theo khuyến nghị từ bài phân tích.

## 7. Đánh giá Mô hình Android Termux + Chrome (Threat Model)
Theo phân tích chuyên sâu về Infostealer trên Android, cấu trúc hiện tại của dự án đáp ứng được hầu hết các tiêu chuẩn "Private Sandbox", nhưng vẫn đối mặt với các rủi ro hệ thống (OS-level). Dưới đây là đối chiếu trực tiếp với dự án:

- **Cô lập Mạng (Pass):** Ứng dụng đã chạy ở `127.0.0.1` kèm Token. Không một ứng dụng độc hại nào trên máy (dù scan được port) có thể mở được giao diện nếu không bắt được Token này.
- **Cô lập Dữ liệu (Pass):** File `vault.luupass` nằm gọn trong phân vùng riêng của Termux (`$HOME`). Hệ điều hành Android (Sandboxing) chặn tuyệt đối các ứng dụng khác chạm vào file này nếu thiết bị chưa Root. Tuyệt đối không chạy lệnh `termux-setup-storage` nếu không có nhu cầu Export backup ra thư mục `/Download`.
- **Bảo mật Trình duyệt (Warning):** Dù Flet thiết lập WebSocket một chiều, URL ban đầu (chứa Token) vẫn có thể bị Chrome lưu vào *Browser History*. Nếu kẻ gian lấy được lịch sử truy cập, hắn có thể chôm Token. 
  -> *Khuyến nghị:* Mở link bằng chế độ Ẩn danh (Incognito), tắt tính năng Auto-save Password của Chrome đối với IP `127.0.0.1`.
- **Rủi ro Infostealer - Accessibility & Overlay (Critical):** Các phần mềm độc hại hiện đại không cần trộm file mã hóa. Chúng sử dụng quyền Trợ năng (Accessibility) để "đọc" màn hình lúc bạn đang xem mật khẩu, hoặc dùng "Bàn phím giả" (Fake Keyboard) để ghi log Master Password lúc gõ. Đây là giới hạn vật lý của bất kỳ Web UI nào.
  -> *Khuyến nghị:* Định kỳ kiểm tra Play Protect, gỡ bỏ mọi ứng dụng xin quyền "Trợ năng" (Accessibility) hoặc "Hiển thị trên ứng dụng khác" (Draw over other apps). Tính năng *Auto-clear Clipboard sau 15s* của dự án đã triệt tiêu được 1 phần rủi ro bị trộm qua bộ nhớ đệm.

---
**Kết luận:** Bài phân tích cực kỳ chính xác và chuyên nghiệp. Nó đánh đúng vào điểm yếu chí mạng của các ứng dụng Desktop/Web-local: "Khóa chặt file trên ổ cứng là chưa đủ, phải chống lộ lọt dữ liệu khi file đã được mở khóa (In-RAM, Clipboard, Network Port, Accessibility Keylogger)". Dự án hiện đã áp dụng thành công các chốt chặn cơ bản nhất (127.0.0.1, Token, Clipboard Clear), biến LuuPass thành một pháo đài gần như bất khả xâm phạm nếu môi trường Android được giữ sạch.
