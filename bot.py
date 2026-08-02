import discord
from discord.ext import commands
import sqlite3
import random
import string
import time
import asyncio
from aiohttp import web
import os

BOT_TOKEN = os.getenv(MTUzMzU3MzUxNDQzMzQwMDg4Mw.G6Fw9z.9JEFRNoHhUzkVxSLKxTR6L6kJnQNohhy83Tlbw)
ALLOWED_USERS = [1532081645774045257, 798192702804983849]  # Your user IDs
GUILD_ID = 1533237721685032990  # Your server ID
PORT = 8080

conn = sqlite3.connect('keys.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keys (
    key TEXT PRIMARY KEY,
    expires INTEGER,
    used INTEGER DEFAULT 0
)''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

async def handle_validate(request):
    data = await request.json()
    key = data.get('key')
    if not key:
        return web.json_response({'valid': False}, status=400)
    c.execute('SELECT expires, used FROM keys WHERE key = ?', (key,))
    row = c.fetchone()
    if row and not row[1] and row[0] > int(time.time()):
        return web.json_response({'valid': True})
    return web.json_response({'valid': False})

app = web.Application()
app.router.add_post('/validate', handle_validate)

@bot.command(name='genkey')
async def genkey(ctx, duration: str = '7d'):
    if ctx.guild.id != GUILD_ID:
        await ctx.send("This command is not allowed in this server.")
        return
    if ctx.author.id not in ALLOWED_USERS:
        await ctx.send("You are not authorized to generate keys.")
        return

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
        await ctx.send("Invalid duration. Use e.g., 1d, 3d, 7d, 30d, 1y, perm")
        return

    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    expires = 9999999999 if seconds == 0 else int(time.time()) + seconds
    c.execute('INSERT INTO keys (key, expires) VALUES (?, ?)', (key, expires))
    conn.commit()

    dur_str = "permanent" if seconds == 0 else duration
    await ctx.send(f"✅ Key generated: `{key}` – expires in {dur_str}")

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"HTTP server running on port {PORT}")
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
