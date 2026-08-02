import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import string
import time
import asyncio
from aiohttp import web
import os

# ---- READ TOKEN FROM ENVIRONMENT ----
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# ---- CONFIG ----
ALLOWED_USERS = [1532081645774045257, 798192702804983849]  # Your user IDs
GUILD_ID = 1533237721685032990  # Your server ID
PORT = 8080

# ---- DATABASE ----
conn = sqlite3.connect('keys.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keys (
    key TEXT PRIMARY KEY,
    expires INTEGER,
    used INTEGER DEFAULT 0
)''')
conn.commit()

# ---- BOT SETUP ----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# ---- HTTP SERVER FOR KEY VALIDATION ----
async def handle_validate(request):
    data = await request.json()
    key = data.get('key')
    if not key:
        return web.json_response({'valid': False}, status=400)
    c.execute('SELECT expires, used FROM keys WHERE key = ?', (key,))
    row = c.fetchone()
    if row and not row[1] and row[0] > int(time.time()):
        # Uncomment for single-use keys
        # c.execute('UPDATE keys SET used = 1 WHERE key = ?', (key,))
        # conn.commit()
        return web.json_response({'valid': True})
    return web.json_response({'valid': False})

app = web.Application()
app.router.add_post('/validate', handle_validate)

# ---- SLASH COMMAND: /genkey ----
@bot.tree.command(name='genkey', description='Generate a license key with expiration')
@app_commands.describe(duration='Duration: 1d, 3d, 7d, 30d, 1y, perm')
async def genkey(interaction: discord.Interaction, duration: str = '7d'):
    # Check guild
    if interaction.guild.id != GUILD_ID:
        await interaction.response.send_message("This command is not allowed in this server.", ephemeral=True)
        return
    # Check user permission
    if interaction.user.id not in ALLOWED_USERS:
        await interaction.response.send_message("You are not authorized to generate keys.", ephemeral=True)
        return

    # Parse duration
    duration = duration.lower()
    seconds = 0
    if duration.endswith('d'):
        days = int(duration[:-1])
        seconds = days * 86400
    elif duration.endswith('y'):
        years = int(duration[:-1])
        seconds = years * 365 * 86400
    elif duration == 'perm':
        seconds = 0
    else:
        await interaction.response.send_message("❌ Invalid duration. Use: 1d, 3d, 7d, 30d, 1y, perm", ephemeral=True)
        return

    # Generate key
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    expires = 9999999999 if seconds == 0 else int(time.time()) + seconds
    c.execute('INSERT INTO keys (key, expires) VALUES (?, ?)', (key, expires))
    conn.commit()

    dur_str = "permanent" if seconds == 0 else duration
    await interaction.response.send_message(f"✅ Key generated: `{key}` – expires in {dur_str}")

# ---- SYNC COMMANDS ON STARTUP ----
@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        # Sync commands to your guild (instant)
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print(f"✅ Slash commands synced to guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ---- RUN BOT AND HTTP SERVER ----
async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 HTTP validation server running on port {PORT}")
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
