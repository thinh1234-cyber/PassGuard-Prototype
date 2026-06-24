# LuuPass

LuuPass la password manager offline-first cho vault ca nhan. App luu du lieu trong mot file vault ma hoa cuc bo, khong can cloud server va khong tu dong dong bo qua Internet.

Repository public nay chi giu nhung file can thiet de chay, build va test project. Tai lieu phat trien noi bo nhu `architecture.md`, `update.md`, `docs/`, `stitch_modern_password_vault/` duoc giu local va ignore khoi Git.

## Tinh nang chinh

- Ma hoa vault bang `Argon2id` + `AES-256-GCM` voi format moi `A2G1`.
- Van doc duoc vault legacy `GCM1` va Fernet cu de tranh mat du lieu khi migrate.
- Safe import: decrypt va parse file import thanh cong roi moi overwrite vault hien tai.
- Atomic save, backup rotation va healing mode khi vault chinh hong hoac bi xoa.
- Password generator offline, khong goi dich vu ngoai.
- Auto-clear clipboard sau khi copy, idle auto-lock, lock va shutdown tu UI.
- UI Flet cho desktop window va local web/mobile qua Termux.
- Update check opt-in tu GitHub repo `thinh1234-cyber/luu_pass`, khong tu `git pull` hay tu chay code moi.

## Cai dat

Yeu cau:

- Python 3.10 tro len
- Git neu muon dung update check bang remote HEAD/tag

```bash
pip install -r requirements.txt
python main.py
```

## Chay tren Android Termux

```bash
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/thinh1234-cyber/luu_pass.git
cd luu_pass
pip install -r requirements.txt
python main.py --web
```

Khi chay `--web`, app bind vao `127.0.0.1` va in ra URL co token, vi du:

```text
http://127.0.0.1:8550/<token>
```

Nen mo dung URL co token trong browser tren dien thoai. Import/export tren web mobile phu thuoc kha nang File Picker cua browser; neu folder picker khong kha dung, hay dung o `Export Folder Path` de nhap path tren filesystem Termux.

## Cach dung nhanh

1. Chay app va nhap master password de unlock hoac tao vault moi.
2. Tao entry, them account, username/password va notes neu can.
3. Bam save trong dashboard de ghi vault.
4. Dung Settings de export/import vault, doi master password, verify backups hoac check update.
5. Dung Lock Vault khi roi may; dung Shutdown neu muon dong app/server local.

File vault mac dinh:

```text
vault.luupass
```

Backup mac dinh:

```text
vault.luupass.bak1
vault.luupass.bak2
vault.luupass.bak3
```

## Bao mat

LuuPass bao ve manh nhat khi vault dang khoa. Neu file `vault.luupass` bi copy, attacker van phai vuot qua Argon2id va AES-GCM.

Khi vault da unlock, plaintext password ton tai trong RAM/UI de app co the hien thi, sua va copy. Neu may dang nghi nhiem infostealer, keylogger, clipboard monitor, screen capture hoac malware doc RAM, khong nen unlock vault that tren may do. Hay lam sach he dieu hanh hoac dung thiet bi tin cay hon truoc.

Vault va backup khong bao gio nen commit len Git. `.gitignore` da chan:

```gitignore
*.luupass
*.luupass.bak*
*.luupass.tmp
```

Neu vault tung bi commit/push len remote, hay coi ciphertext da lo va nen doi master password, tao vault moi, hoac purge Git history neu can.

## Update

Nut `Check Updates` trong Settings dung module `src/update_checker.py`.

- Uu tien doc version tag tu `https://github.com/thinh1234-cyber/luu_pass.git`.
- Neu repo chua co tag version, fallback sang so sanh remote HEAD voi local HEAD.
- Khong tu cai dat, khong tu pull code moi, khong chay file tai ve.
- Helper SHA256 co san de verify artifact release thu cong.

## Cau truc project public

```text
.
|-- main.py
|-- requirements.txt
|-- build.ps1
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

Local-only development notes are ignored by Git:

```text
architecture.md
update.md
docs/
stitch_modern_password_vault/
```

## Test

```bash
python -m pytest -q
```

## Build Windows

```powershell
.\build.ps1 -Windows
```

Build output se nam trong `dist/`.
