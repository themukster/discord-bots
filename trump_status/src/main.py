import os
import logging

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

TARGET_CHANNEL_ID = 907266390103298080
API_URL = "https://istrumpdead.app/api/"
TRIGGER_PREFIXES = ("has it happened", "did it happen")
DISCORD_MESSAGE_LIMIT = 2000

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')


@bot.event
async def on_message(message: discord.Message):
    # Ignore ourselves and other bots.
    if message.author.bot:
        return

    # Only respond in the configured channel.
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    content = message.content.strip().lower()
    if not content.startswith(TRIGGER_PREFIXES):
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                text = (await resp.text()).strip()
    except Exception as exc:
        logger.error(f"Failed to fetch {API_URL}: {exc}")
        await message.reply("Couldn't reach istrumpdead.app right now.")
        return

    if not text:
        text = "istrumpdead.app returned an empty response."

    await message.reply(text[:DISCORD_MESSAGE_LIMIT])


BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
