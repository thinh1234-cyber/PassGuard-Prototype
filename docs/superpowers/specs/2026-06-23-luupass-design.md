# LuuPass Design Specification

## 1. Overview
LuuPass is a lightweight, simple, and self-contained password manager designed to run natively on Android and Windows 10. It focuses on local encryption without cloud syncing, relying instead on manual import/export of a single encrypted file for data portability. The UI is inspired by 1Password, featuring a modern, dark-themed, responsive design.

## 2. Architecture & Data Flow
- **Data Structure**: A single JSON object containing a list of credential entries.
  - `Entry Model`: ID (UUID), Title, Username, Password, URL, Notes, CreatedAt, UpdatedAt.
- **Storage**: A single encrypted file named `vault.luupass`.
- **Encryption Algorithm**: AES-256 (via `Fernet` from the `cryptography` Python package).
- **Key Derivation**: PBKDF2HMAC is used to derive the encryption key from the user's Master Password, combined with a randomly generated Salt. The Salt is stored unencrypted at the beginning of the `vault.luupass` file so it can be read before deriving the key for decryption.
- **Data Portability**: Users export and import the vault by copying the `vault.luupass` file between devices.

## 3. Technology Stack
- **Language**: Python 3.
- **UI Framework**: Flet (provides a modern Flutter-based UI, builds to Windows executable and Android APK).
- **Cryptography**: `cryptography` library (for AES encryption and key derivation).
- **Data Validation**: `pydantic` (for managing the JSON schema and data structures).

## 4. UI/UX Design (Flet)
- **Theme**: Default Dark Mode, modern typography (similar to 1Password).
- **Unlock Screen**: A simple, centered input field for the Master Password with an "Unlock" button.
- **Main View (Desktop - Responsive 3-Column Layout)**:
  - **Sidebar (Left)**: Navigation options (All Items, Favorites, Settings, Lock Vault).
  - **List View (Center)**: Scrollable list of accounts showing Title and Username, with a Search bar at the top.
  - **Detail View (Right)**: Shows details of the selected account. Includes obscured password field, "Reveal" toggle, and "Copy to Clipboard" buttons for Username and Password.
- **Main View (Mobile)**:
  - The layout collapses. The list view acts as the home screen, and tapping an item navigates to the Detail View. The sidebar is accessible via a Hamburger menu.
- **Settings Screen**:
  - Options to Change Master Password.
  - Display the absolute path of `vault.luupass` for manual backup/export.

## 5. Security Constraints
- The Master Password is never saved to disk. It is held in volatile memory only while the vault is unlocked.
- The vault file is locked and encrypted.

## 6. Implementation Scope
- **Phase 1**: Setup project, define data models and encryption utility.
- **Phase 2**: Create basic Flet UI components (Unlock, Main layout).
- **Phase 3**: Integrate UI with the core logic, handle state management (CRUD operations on passwords).
- **Phase 4**: Setup build processes for Windows (`.exe`) and Android (`.apk`).
