"""Orion-Deck: TUI client for the Orion decentralized chat network.

MESSAGE SCHEMA (matches orion-network.py):
  Inbound from room:
    {"type":"session_key","key":"<b64>"}
    {"type":"room_meta","locked":bool,"motd":"<str>","room_name":"<str>","history":[...]}
    {"type":"auth_ok"} / {"type":"auth_fail","message":"<str>"}
    {"type":"event","event":"join|leave|rename|system|motd","text":"<str>"}
    {"type":"chat","from":"<n>","ciphertext":"<b64>"}
    {"type":"error","message":"<str>"}
  Outbound to room:
    {"type":"handshake","pubkey":"<pem>"}
    {"type":"auth","ciphertext":"<b64>"}
    {"type":"name","ciphertext":"<b64>"}
    {"type":"chat","ciphertext":"<b64>"}
"""

import asyncio
import json
import os
import re
import base64
import getpass
from datetime import datetime
from websockets import connect
from websockets.exceptions import ConnectionClosed

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.fernet import Fernet

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

HUB_URL = os.environ.get("HUB_URL", "wss://orion-core.onrender.com")
HUB_WS  = HUB_URL.rstrip("/") + "/ws"

console = Console()

# ─────────────────────────────────────────────
#  TUI helpers
# ─────────────────────────────────────────────

def clear():
    console.clear()

def banner():
    title = Text(justify="center")
    title.append("\n")
    title.append("  ✦ ", style="bold yellow")
    title.append("ORION", style="bold white")
    title.append("-", style="dim cyan")
    title.append("DECK", style="bold cyan")
    title.append(" ✦\n", style="bold yellow")
    title.append("decentralized  ·  encrypted  ·  ephemeral\n", style="dim")
    console.print(Panel(title, border_style="cyan", box=box.DOUBLE_EDGE, padding=(0, 6)))

def status_line(icon: str, msg: str, style: str = "dim"):
    console.print(f" {icon}  [{style}]{msg}[/{style}]")

def section(title: str):
    console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))

def print_help():
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), expand=False)
    t.add_column("cmd",  style="bold cyan", no_wrap=True, width=18)
    t.add_column("desc", style="dim white")
    t.add_row("/join [id]",  "Join a room by its Room ID")
    t.add_row("/info [id]",  "Show room details")
    t.add_row("/list",       "Refresh room list")
    t.add_row("/ping",       "Test hub connection")
    t.add_row("/quit",       "Exit Orion-Deck")
    console.print(Panel(t, title="[bold yellow]⌘  Commands[/bold yellow]",
                        border_style="yellow", box=box.ROUNDED, padding=(0,1)))

def print_rooms(rooms: dict):
    if not rooms:
        console.print(Panel("[dim]No rooms are currently online.[/dim]",
                            border_style="dim", box=box.ROUNDED))
        return
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
              padding=(0, 2), expand=True)
    t.add_column("Room ID", style="bold yellow", width=10, justify="center", no_wrap=True)
    t.add_column("Name",    style="bold white")
    t.add_column("Online",  style="green",  width=8,  justify="center")
    t.add_column("Access",  style="dim",    width=14, justify="center")
    for name, info in rooms.items():
        rid    = info.get("id", "?")
        online = str(info.get("online", 0))
        locked = info.get("locked", False)
        public = info.get("public", True)
        access = "🔒 Private" if locked else ("🔐 Unlisted" if not public else "🔓 Open")
        t.add_row(rid, name, online, access)
    console.print(Panel(t,
        title=f"[bold cyan]Available Rooms[/bold cyan]  [dim]({len(rooms)} online)[/dim]",
        border_style="cyan", box=box.ROUNDED, padding=(0,1)))
    console.print(
        " [dim]Use [bold cyan]/join [Room ID][/bold cyan] to connect"
        "  ·  [bold cyan]/help[/bold cyan] for all commands[/dim]\n")

def print_room_info(room_name: str, info: dict):
    locked = info.get("locked", False)
    public = info.get("public", True)
    access = "🔒 Password required" if locked else ("🔐 Unlisted" if not public else "🔓 Open")
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("key", style="bold cyan", width=10)
    t.add_column("val", style="white")
    t.add_row("Room ID", str(info.get("id", "?")))
    t.add_row("Name",    room_name)
    t.add_row("Online",  str(info.get("online", 0)))
    t.add_row("Access",  access)
    console.print(Panel(t, title="[bold yellow]Room Info[/bold yellow]",
                        border_style="yellow", box=box.ROUNDED, padding=(0,1)))

def print_motd(motd: str, room_name: str = ""):
    """Display MOTD prominently — always visible, never hidden."""
    title = f"[bold yellow]✦  {room_name}[/bold yellow]" if room_name else "[bold yellow]✦  MOTD[/bold yellow]"
    console.print(Panel(
        f"[yellow]{motd}[/yellow]",
        title=title,
        border_style="yellow",
        box=box.HEAVY_HEAD,
        padding=(0, 2),
    ))

def print_chat_header(name: str, room_name: str, locked: bool):
    lock_str = "🔒 Private" if locked else "🔓 Open"
    content  = (
        f"[bold white]{name}[/bold white]  [dim]in[/dim]  "
        f"[bold yellow]{room_name}[/bold yellow]  [dim cyan]({lock_str})[/dim cyan]\n"
        f"[dim]⚠ Messages are ephemeral — lost when the room goes offline[/dim]\n"
        f"[dim]Room commands: /help  /who  /time  /uptime  /motd  /nick  ·  "
        f"type [bold]/leave[/bold] to exit[/dim]"
    )
    console.print(Panel(content, border_style="green", box=box.ROUNDED, padding=(0, 2)))

def ts() -> str:
    return datetime.now().strftime("%H:%M")

def print_event(event: str, text: str):
    """Render a structured event packet — no string parsing needed."""
    t = ts()
    if event == "motd":
        print_motd(text)
    elif event == "join":
        console.print(f" [dim]{t}[/dim]  [green]→[/green]  [green]{text}[/green]")
    elif event == "leave":
        console.print(f" [dim]{t}[/dim]  [yellow]←[/yellow]  [yellow]{text}[/yellow]")
    elif event == "rename":
        console.print(f" [dim]{t}[/dim]  [cyan]◈[/cyan]  [cyan]{text}[/cyan]")
    elif event == "system":
        # Multi-line system messages (e.g. /help output)
        lines = text.split("\n")
        if len(lines) > 1:
            console.print(Panel("\n".join(f"[dim white]{l}[/dim white]" for l in lines),
                                border_style="dim", box=box.SIMPLE, padding=(0,2)))
        else:
            console.print(f" [dim]{t}[/dim]  [bold cyan]⬡[/bold cyan]  [cyan]{text}[/cyan]")
    else:
        console.print(f" [dim]{t}[/dim]  [dim]◦[/dim]  [dim]{text}[/dim]")

def print_chat(sender: str, plaintext: str):
    """Render a decrypted chat message."""
    t = ts()
    console.print(f" [dim]{t}[/dim]  [bold cyan]◆[/bold cyan]  [bold]{sender}[/bold]  [white]{plaintext}[/white]")

def print_history(history: list, cipher: Fernet):
    """Replay the ephemeral message history on room join."""
    if not history:
        return
    console.print(Rule("[dim]— recent history (ephemeral) —[/dim]", style="dim"))
    for entry in history:
        try:
            etype = entry.get("type")
            hts   = entry.get("ts", "--:--")
            if etype == "event":
                evt  = entry.get("event", "system")
                text = entry.get("text", "")
                if evt == "motd":
                    pass  # MOTD shown separately
                elif evt in ("join", "leave", "rename"):
                    color = "green" if evt == "join" else ("yellow" if evt == "leave" else "cyan")
                    console.print(f" [dim]{hts}[/dim]  [{color}]{text}[/{color}]")
                else:
                    console.print(f" [dim]{hts}[/dim]  [dim cyan]{text}[/dim cyan]")
            elif etype == "chat":
                sender = entry.get("from", "?")
                ct     = entry.get("ciphertext", "")
                try:
                    plain = cipher.decrypt(base64.b64decode(ct)).decode()
                    console.print(f" [dim]{hts}[/dim]  [bold]{sender}[/bold]  [dim white]{plain}[/dim white]")
                except Exception:
                    console.print(f" [dim]{hts}[/dim]  [bold]{sender}[/bold]  [dim red](encrypted)[/dim red]")
        except Exception:
            pass
    console.print(Rule("[dim]— live —[/dim]", style="dim"))

def print_error(msg: str):
    console.print(f"\n [bold red]✖[/bold red]  [red]{msg}[/red]")

def print_ok(msg: str):
    console.print(f" [bold green]✔[/bold green]  [green]{msg}[/green]")

# ─────────────────────────────────────────────
#  Input helpers
# ─────────────────────────────────────────────

async def read_input(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))

async def read_password(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: getpass.getpass(prompt))

# ─────────────────────────────────────────────
#  Crypto
# ─────────────────────────────────────────────

def _generate_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub  = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv, pub

def normalize_rooms(raw_rooms) -> dict:
    out: dict = {}
    if isinstance(raw_rooms, dict):
        for name, val in raw_rooms.items():
            if isinstance(val, dict):
                out[str(name)] = {"id": val.get("id","?"), "online": val.get("online",0),
                                  "locked": val.get("locked",False), "public": val.get("public",True)}
            else:
                out[str(name)] = {"id":"?","online":0,"locked":False,"public":True}
    elif isinstance(raw_rooms, list):
        for item in raw_rooms:
            if isinstance(item, dict):
                name = item.get("name") or "Unknown"
                out[str(name)] = {"id": item.get("id","?"), "online": item.get("online",0),
                                  "locked": item.get("locked",False), "public": item.get("public",True)}
    return out

# ─────────────────────────────────────────────
#  Hub client
# ─────────────────────────────────────────────

async def hub_client():
    clear()
    banner()
    status_line("[dim]◌[/dim]", f"Connecting to hub  {HUB_URL}", "dim")
    console.print()

    try:
        async with connect(HUB_WS) as ws:
            await ws.send(json.dumps({"type": "get_list", "client_type": "deck"}))
            rooms: dict = {}
            status_line("[bold green]●[/bold green]", "Connected to Orion-Core hub", "green")
            console.print()

            async for raw in ws:
                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                if data.get("type") == "room_list":
                    rooms = normalize_rooms(data.get("rooms", {}))
                    print_rooms(rooms)

                    while True:
                        try:
                            raw_cmd = await read_input("  [hub] ◆ ")
                        except (EOFError, KeyboardInterrupt):
                            console.print("\n [bold yellow]👋  Goodbye![/bold yellow]")
                            return

                        cmd = raw_cmd.strip()
                        if not cmd:
                            continue

                        if cmd == "/help":
                            print_help()

                        elif cmd in ("/list", "/refresh"):
                            status_line("[dim]◌[/dim]", "Refreshing room list…")
                            await ws.send(json.dumps({"type": "get_list", "client_type": "deck"}))
                            break

                        elif cmd == "/ping":
                            await ws.send(json.dumps({"type": "get_list", "client_type": "deck"}))
                            status_line("[bold green]🏓[/bold green]", "Hub is responsive", "green")

                        elif cmd.startswith("/info"):
                            arg   = cmd[5:].strip()
                            match = next(((n,i) for n,i in rooms.items() if i.get("id")==arg), None)
                            if match:
                                print_room_info(match[0], match[1])
                            else:
                                print_error(f"No room with ID [bold]{arg}[/bold]  —  use /list to refresh")

                        elif cmd.startswith("/join"):
                            arg   = cmd[5:].strip()
                            match = next(((n,i) for n,i in rooms.items() if i.get("id")==arg), None)
                            if not match:
                                print_error(f"No room with ID [bold]{arg}[/bold]  —  use /list to refresh")
                                continue

                            rname, rinfo = match
                            await ws.send(json.dumps({"type": "join_by_id", "id": arg}))
                            join_raw  = await ws.recv()
                            join_data = json.loads(join_raw)

                            if join_data.get("type") != "join_info":
                                print_error(f"Hub error: {join_data.get('message','unknown')}")
                                continue

                            addr = join_data.get("address")
                            section(f"Joining  {rname}")
                            await room_chat(addr, rname, rinfo)
                            section("Back at hub")
                            await ws.send(json.dumps({"type": "get_list", "client_type": "deck"}))
                            break

                        elif cmd == "/quit":
                            console.print("\n [bold yellow]👋  Goodbye![/bold yellow]")
                            return

                        else:
                            print_error(f"Unknown command: [bold]{cmd}[/bold]  —  type /help")

                elif data.get("type") == "broadcast":
                    console.print(Panel(
                        f"[bold white]{data.get('message','')}[/bold white]",
                        title="[bold red]📢  Admin Broadcast[/bold red]",
                        border_style="red", box=box.ROUNDED,
                    ))

    except Exception as e:
        print_error(f"Could not connect to hub: {e}")

# ─────────────────────────────────────────────
#  Room chat
# ─────────────────────────────────────────────

async def room_chat(address: str, room_name: str, room_info: dict):
    """
    Connect to a room. Each call is a completely fresh session:
    - new RSA keypair
    - new Fernet cipher derived from the room's session key
    - clean recv_task lifecycle
    """
    try:
        async with connect(address) as ws:

            # ── 1. RSA handshake ──────────────────────────────────────
            status_line("[dim]◌[/dim]", "Performing encrypted handshake…")
            private_key, pub_pem = _generate_keypair()
            await ws.send(json.dumps({"type": "handshake", "pubkey": pub_pem}))

            sess_raw  = await ws.recv()
            sess_data = json.loads(sess_raw)
            if sess_data.get("type") != "session_key":
                print_error("Handshake failed — unexpected response")
                return

            session_key = private_key.decrypt(
                base64.b64decode(sess_data["key"]),
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                             algorithm=hashes.SHA256(), label=None),
            )
            cipher = Fernet(session_key)
            print_ok("Encrypted session established")

            # ── 2. room_meta: locked, MOTD, history ───────────────────
            meta_raw  = await ws.recv()
            meta_data = json.loads(meta_raw)
            if meta_data.get("type") == "error":
                print_error(meta_data.get("message", "Room error"))
                return
            room_locked = False
            room_motd   = ""
            history     = []
            if meta_data.get("type") == "room_meta":
                room_locked = meta_data.get("locked", False)
                room_motd   = meta_data.get("motd", "")
                history     = meta_data.get("history", [])
                # Update room name from server if available
                room_name = meta_data.get("room_name", room_name)

            # ── 3. Password (only if locked) ──────────────────────────
            if room_locked:
                password = await read_password("  🔑 Password: ")
                enc_pw   = cipher.encrypt(password.encode())
                await ws.send(json.dumps({
                    "type":       "auth",
                    "ciphertext": base64.b64encode(enc_pw).decode(),
                }))
                auth_resp = json.loads(await ws.recv())
                if auth_resp.get("type") != "auth_ok":
                    print_error(auth_resp.get("message", "Authentication failed"))
                    return
                print_ok("Authenticated")

            # ── 4. Send name (structured packet) ─────────────────────
            name = (await read_input("  👤 Your name: ")).strip() or "anon"
            enc_name = cipher.encrypt(name.encode())
            await ws.send(json.dumps({
                "type":       "name",
                "ciphertext": base64.b64encode(enc_name).decode(),
            }))

            # ── 5. Show MOTD prominently, then history, then header ───
            if room_motd:
                print_motd(room_motd, room_name)

            print_history(history, cipher)
            print_chat_header(name, room_name, room_locked)

            # ── 6. Message loop ───────────────────────────────────────
            # recv_task is tracked so we can cancel it cleanly on /leave
            recv_task: asyncio.Task | None = None
            disconnected = asyncio.Event()

            async def receiver():
                try:
                    async for raw_msg in ws:
                        try:
                            msg_data = json.loads(raw_msg)
                            mtype = msg_data.get("type")

                            if mtype == "event":
                                print_event(msg_data.get("event","system"),
                                            msg_data.get("text",""))

                            elif mtype == "chat":
                                sender = msg_data.get("from", "?")
                                try:
                                    plain = cipher.decrypt(
                                        base64.b64decode(msg_data["ciphertext"])
                                    ).decode()
                                    print_chat(sender, plain)
                                except Exception:
                                    console.print(f" [dim]{ts()}[/dim]  "
                                                  f"[bold]{sender}[/bold]  [dim red](decrypt error)[/dim red]")

                            elif mtype == "error":
                                print_error(msg_data.get("message", ""))

                        except Exception as e:
                            console.print(f" [dim red]recv parse error: {e}[/dim red]")
                except ConnectionClosed:
                    pass
                except Exception:
                    pass
                finally:
                    disconnected.set()

            recv_task = asyncio.create_task(receiver())

            try:
                while True:
                    try:
                        line = await read_input("  💬 ")
                    except (EOFError, KeyboardInterrupt):
                        break

                    stripped = line.strip()

                    if stripped == "/leave":
                        status_line("[yellow]←[/yellow]", "Leaving room…", "yellow")
                        break

                    if not stripped:
                        continue

                    # Check if receiver already stopped (room went offline)
                    if disconnected.is_set():
                        print_error("Room connection lost.")
                        break

                    try:
                        enc_msg = cipher.encrypt(line.encode())
                        await ws.send(json.dumps({
                            "type":       "chat",
                            "ciphertext": base64.b64encode(enc_msg).decode(),
                        }))
                    except Exception:
                        print_error("Connection lost")
                        break

            finally:
                # Always clean up recv_task — this is the rejoin fix:
                # Cancel, then await so the task is fully done before we return.
                # Without awaiting, stale tasks can interfere with the next session.
                if recv_task and not recv_task.done():
                    recv_task.cancel()
                    try:
                        await recv_task
                    except (asyncio.CancelledError, Exception):
                        pass

    except ConnectionClosed:
        print_error("Room closed the connection.")
    except Exception as e:
        print_error(f"Failed to join room: {e}")

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    try:
        asyncio.run(hub_client())
    except KeyboardInterrupt:
        console.print("\n [dim]Exiting…[/dim]")

if __name__ == "__main__":
    main()
