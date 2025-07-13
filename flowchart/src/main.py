import os
import discord
from discord.ext import commands

# Initialize the bot with necessary intents
# discord.Intents.default() provides basic intents like guild_messages, guild_reactions, etc.
# discord.Intents.message_content is REQUIRED to read message content for prefix commands (not strictly for slash commands)
# discord.Intents.members is required if you need member-related events/data
# discord.Intents.presences is also a privileged intent that might be needed depending on functionality.
intents = discord.Intents.default()
intents.message_content = True # Enable if you plan to read message content
#intents.members = True # Enable if you need member-related events
intents.presences = True # Enable if you need presence-related events

# Create a bot instance
# `command_prefix` is used for traditional prefix commands (e.g., !hello).
# For slash commands, it's not strictly necessary, but good to have a placeholder.
bot = commands.Bot(command_prefix='!', intents=intents)

# Define the URL that the bot will post
LINK_TO_POST = "https://imgur.com/personal-income-spending-flowchart-united-states-lSoUQr2"

@bot.event
async def on_ready():
    """
    Event that fires when the bot has successfully connected to Discord.
    It prints a message to the console and syncs slash commands.
    """
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    # Sync slash commands globally or to specific guilds.
    # For testing, syncing to a specific guild (server) is faster.
    # Replace YOUR_GUILD_ID with the ID of your Discord server.
    # You can get your guild ID by enabling Developer Mode in Discord settings (User Settings -> Advanced -> Developer Mode)
    # Then right-click on your server's icon and choose "Copy ID".
    #
    # To sync globally (can take up to an hour to appear):
    # await bot.tree.sync()
    #
    # To sync to a specific guild (faster for development):
    # For example, if your guild ID is 123456789012345678:
    # guild_id = YOUR_GUILD_ID
    # if guild_id:
    #     guild = discord.Object(id=guild_id)
    #     bot.tree.copy_global_to(guild=guild)
    #     await bot.tree.sync(guild=guild)
    # else:
    #     print("No guild ID provided for quick sync. Commands will sync globally (may take longer).")
    await bot.tree.sync() # Syncs globally by default

@bot.tree.command(name="flowchart", description="Posts a predefined useful link.")
async def link_command(interaction: discord.Interaction):
    """
    A slash command that responds with a predefined link.
    When a user types /flowchar, the bot will send the LINK_TO_POST.
    """
    await interaction.response.send_message(f"Follow the flowchart: {LINK_TO_POST}", ephemeral=False)
    # `ephemeral=False` means the message is visible to everyone in the channel.
    # Set to `True` if you want only the user who typed the command to see the response.

# Get the bot token from environment variables for security.
# Replit's "Secrets" feature sets these environment variables.
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Check if the token is available before running the bot
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    print("Please set your bot token in .bashrc")

