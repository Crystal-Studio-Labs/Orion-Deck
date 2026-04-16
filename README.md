# ✦ Orion-Deck

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Client](https://img.shields.io/badge/Client-TUI-cyan)
![Encryption](https://img.shields.io/badge/Encryption-RSA%20%2B%20Fernet-purple)
![Status](https://img.shields.io/badge/Status-Active-success)
![Architecture](https://img.shields.io/badge/Architecture-Decentralized-orange)

---

**Orion-Deck** is a **terminal-based (TUI) client** for the Orion decentralized chat system.  
It connects to Orion-Core hubs and Orion-Net rooms to provide a **secure, encrypted, and ephemeral chat experience**.

> ✦ Orion — decentralized · encrypted · ephemeral

---

## 🏢 Organization

Developed under:  
👉 https://github.com/Crystal-Studio-Labs

---

## ✨ Features

- 🔐 **End-to-End Encryption**
  - RSA handshake for secure key exchange
  - Fernet encryption for all messages

- 💬 **Real-Time Chat**
  - Encrypted messaging
  - Structured events (join, leave, system, MOTD)

- 🖥️ **Rich Terminal UI**
  - Built using `rich`
  - Panels, tables, and styled output
  - Live chat formatting with timestamps

- 🧠 **Room Interaction**
  - Join via Room ID
  - View room info and metadata
  - Supports public and private rooms

- 🕓 **Ephemeral Messaging**
  - Messages are not stored permanently
  - History only exists while the room is active

- 📡 **Hub Integration**
  - Fetch live room list
  - Receive admin broadcasts
  - Real-time updates

---

## 🚀 Usage (Local Only)

Orion-Deck is a **client application** — no hosting required.

### Run the client

```bash
python orion-deck.py
```

---

## 📦 Installation

```bash
git clone https://github.com/Crystal-Studio-Labs/orion-deck
cd orion-deck
pip install websockets cryptography rich
python orion-deck.py
```

---

## ⚙️ Configuration

Set hub endpoint using environment variable:

```bash
export HUB_URL=wss://orion-core.onrender.com
```

Default:
```
wss://orion-core.onrender.com
```

---

## ⌨️ Commands

### Hub Commands

| Command        | Description                     |
|----------------|---------------------------------|
| `/join [id]`   | Join a room by Room ID          |
| `/info [id]`   | Show room details               |
| `/list`        | Refresh room list               |
| `/ping`        | Test hub connection             |
| `/quit`        | Exit Orion-Deck                 |

---

### Room Commands

| Command     | Description                |
|------------|----------------------------|
| `/leave`   | Exit the room              |
| `/help`    | Show commands              |
| `/who`     | List users                 |
| `/time`    | Server time                |
| `/uptime`  | Room uptime                |
| `/motd`    | Message of the day         |
| `/nick`    | Change nickname            |

---

## 🔐 Security Model

### 1. Handshake
- Client generates RSA keypair
- Server returns encrypted session key

### 2. Session Encryption
- All communication uses Fernet encryption

### 3. Authentication
- Passwords encrypted before sending
- Never transmitted in plaintext

---

## 🧩 Message Schema

### Inbound
```json
{"type":"session_key","key":"<b64>"}
{"type":"room_meta","locked":bool,"motd":"<str>","room_name":"<str>","history":[...]}
{"type":"auth_ok"}
{"type":"event","event":"join|leave|rename|system|motd","text":"<str>"}
{"type":"chat","from":"<n>","ciphertext":"<b64>"}
```

### Outbound
```json
{"type":"handshake","pubkey":"<pem>"}
{"type":"auth","ciphertext":"<b64>"}
{"type":"name","ciphertext":"<b64>"}
{"type":"chat","ciphertext":"<b64>"}
```

---

## 🧱 Architecture

```
        ┌───────────────┐
        │ Orion-Core    │
        │   (Hub)       │
        └──────┬────────┘
               │
        WebSocket (/ws)
               │
     ┌─────────▼─────────┐
     │   Orion-Deck      │
     │   (TUI Client)    │
     └─────────┬─────────┘
               │
        WebSocket (Room)
               │
     ┌─────────▼─────────┐
     │   Orion-Net       │
     │  (Room Server)    │
     └───────────────────┘
```

---

## ⚠️ Important Notes

- Messages are **ephemeral**
- No permanent storage
- If a room goes offline → history is lost
- This is **intentional design**

---

## 🛠️ Tech Stack

- Python
- websockets
- cryptography
- rich

---

## 👨‍💻 Author

**Shuvranshu Sahoo**  
🌐 https://sahooshuvranshu.me

---

## 📄 License

MIT License