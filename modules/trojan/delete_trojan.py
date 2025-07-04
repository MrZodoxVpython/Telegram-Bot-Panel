from telegram_bot_panel import *
from telethon import events, Button
import os
import re
import subprocess

CONFIG_PATH = "/etc/xray/config.json"

def parse_accounts():
    if not os.path.exists(CONFIG_PATH):
        return []

    with open(CONFIG_PATH, "r") as f:
        content = f.read()

    # Ambil semua akun dari semua tag
    pattern = r"#\!\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})\n\},\{\s*\"password\":\s*\"([^\"]+)\",\s*\"email\":\s*\"([^\"]+)"
    matches = re.finditer(pattern, content)

    # Hindari duplikat username
    seen = {}
    for m in matches:
        username = m.group(1).strip().lower()
        expired = m.group(2)
        if username not in seen:
            seen[username] = (m.group(1), expired)  # Simpan username asli + expired

    return list(seen.values())

def delete_account_from_config(username):
    if not os.path.exists(CONFIG_PATH):
        return False

    with open(CONFIG_PATH, "r") as f:
        lines = f.readlines()

    new_lines = []
    skip_next = False
    deleted = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if skip_next:
            skip_next = False
            deleted = True
            continue

        if stripped.startswith(f"#! {username} "):
            skip_next = True
            deleted = True
            continue

        new_lines.append(line)

    if deleted:
        with open(CONFIG_PATH, "w") as f:
            f.writelines(new_lines)
        subprocess.call("systemctl restart xray", shell=True)

    return deleted

@bot.on(events.CallbackQuery(data=b"trojan/delete_trojan"))
async def delete_trojan(event):
    chat = event.chat_id
    sender = await event.get_sender()

    if valid(str(sender.id)) != "true":
        await event.answer("Akses ditolak!", alert=True)
        return

    accounts = parse_accounts()
    if not accounts:
        await event.respond("❌ Tidak ada akun Trojan ditemukan.")
        return

    msg = "🗑 Pilih akun yang ingin dihapus:\n\n"
    buttons = []
    for username, exp in accounts:
        buttons.append([Button.inline(f"{username} (exp: {exp})", f"hapus:{username}".encode())])

    await bot.send_message(chat, msg, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"hapus:(.+)"))
async def confirm_delete(event):
    username = event.pattern_match.group(1).decode()
    chat = event.chat_id

    async with bot.conversation(chat) as conv:
        await conv.send_message(f"⚠ Konfirmasi hapus akun `{username}`?\nKetik `YA` untuk konfirmasi.")
        msg = await conv.wait_event(events.NewMessage(from_users=chat))
        if msg.raw_text.strip().upper() == "YA":
            if delete_account_from_config(username):
                await conv.send_message(f"✅ Akun `{username}` berhasil dihapus dari semua tag.", parse_mode="markdown")
            else:
                await conv.send_message("❌ Gagal menghapus akun. Mungkin akun tidak ditemukan.")
        else:
            await conv.send_message("❎ Penghapusan dibatalkan.")

