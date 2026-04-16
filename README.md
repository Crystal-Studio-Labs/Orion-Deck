# ✦ Orion-Deck

**Orion-Deck** is a terminal-based (TUI) client for the **Orion decentralized chat network**.  
It provides a secure, encrypted, and ephemeral chat experience with a rich terminal UI.

---

## ✨ Features

- 🔐 **End-to-End Encryption**
  - RSA handshake for secure key exchange
  - Fernet symmetric encryption for messages

- 💬 **Real-Time Chat**
  - Encrypted messaging between users
  - Structured events (join, leave, rename, system, MOTD)

- 🖥️ **Rich Terminal UI**
  - Built with `rich`
  - Panels, tables, colored logs, and live updates

- 🧠 **Smart Room Handling**
  - Join rooms via Room ID
  - View room info and metadata
  - Supports public, unlisted, and private (locked) rooms

- 🕓 **Ephemeral Messaging**
  - Messages are not stored permanently
  - History only exists while the room is active

- 📡 **Hub Integration**
  - Fetch live room list
  - Receive admin broadcasts
  - Real-time updates

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/orion-deck.git
cd orion-deck
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install websockets cryptography rich
```

---

## 🚀 Usage

### Run the client
```bash
python orion-deck.py
```

---

## ⚙️ Configuration

You can set the hub endpoint using an environment variable:

```bash
export HUB_URL=wss://orion-core.onrender.com
```

Default:
```
wss://orion-core.onrender.com
```

---

## ⌨️ Commands

| Command        | Description                     |
|----------------|---------------------------------|
| `/join [id]`   | Join a room by Room ID          |
| `/info [id]`   | Show room details               |
| `/list`        | Refresh room list               |
| `/ping`        | Test hub connection             |
| `/quit`        | Exit Orion-Deck                 |

---

## 🏠 Room Commands

Inside a room:

| Command     | Description                |
|------------|----------------------------|
| `/leave`   | Exit the room              |
| `/help`    | Show available commands    |
| `/who`     | List users                 |
| `/time`    | Show server time           |
| `/uptime`  | Show room uptime           |
| `/motd`    | Show message of the day    |
| `/nick`    | Change your name           |

---

## 🔐 Security Model

1. **Handshake**
   - Client generates RSA keypair
   - Server sends encrypted session key

2. **Session Encryption**
   - Fernet key used for all communication

3. **Authentication**
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
        │  Orion Hub    │
        │ (Room Index)  │
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
     │   Chat Rooms      │
     │ (Encrypted P2P)   │
     └───────────────────┘
```

---

## ⚠️ Important Notes

- Messages are **ephemeral**
- No permanent storage
- If a room goes offline → **all history is lost**
- This is **by design**

---

## 🛠️ Tech Stack

- Python 3
- `websockets`
- `cryptography`
- `rich`

---

## 📄 License

MIT License

---

## 👨‍💻 Author

**Shuvranshu Sahoo**  
🌐 https://sahooshuvranshu.me

---

## 💡 Future Ideas

- File sharing
- Voice channels
- GUI client
- Persistent optional rooms

---

> ✦ Orion — decentralized · encrypted · ephemeral