import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

LINK_TO_POST = "https://imgur.com/personal-income-spending-flowchart-united-states-lSoUQr2"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    await bot.tree.sync()

@bot.tree.command(name="flowchart", description="Posts a predefined useful link.")
async def link_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"Follow the flowchart: {LINK_TO_POST}", ephemeral=False)

BOT_TOKEN = os.getenv('FLOWCHART_BOT_TOKEN')

if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("Error: FLOWCHART_BOT_TOKEN environment variable not set.")

