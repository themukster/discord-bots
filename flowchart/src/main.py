import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    await bot.tree.sync()

@bot.tree.command(name="flowchart", description="Posts a useful flowchart image.")
async def flowchart_command(interaction: discord.Interaction):
    flowchart_path = os.path.join(os.path.dirname(__file__), "pf_flowchart.jpeg")
    
    if os.path.exists(flowchart_path):
        with open(flowchart_path, 'rb') as f:
            file = discord.File(f, filename="flowchart.jpeg")
            await interaction.response.send_message("Dude, just follow the flowchart:", file=file, ephemeral=False)
    else:
        await interaction.response.send_message("Sorry, the flowchart image could not be found.", ephemeral=True)

BOT_TOKEN = os.getenv('FLOWCHART_BOT_TOKEN')

if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("Error: FLOWCHART_BOT_TOKEN environment variable not set.")

