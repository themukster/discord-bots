import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import os
from dotenv import load_dotenv
import httpx
import webcolors

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_NAME = os.getenv("ROLE_NAME", "Rainbow Role")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.members = True  # Needed to manage roles

bot = commands.Bot(command_prefix="!", intents=intents)

# Cooldown tracker
last_used = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync: {e}")

async def set_gradient_role_color(guild_id: int, role_id: int):
    url = f"https://discord.com/api/v10/guilds/{guild_id}/roles/{role_id}"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    # Generate two distinct random 24-bit color integers
    def generate_color():
        return random.randint(0x000000, 0xFFFFFF)

    primary_color = generate_color()
    secondary_color = generate_color()

    # Optionally: ensure colors are sufficiently different (for contrast)
    while abs(primary_color - secondary_color) < 0x202020:
        secondary_color = generate_color()

    primary_hex = f"#{primary_color:06X}"
    secondary_hex = f"#{secondary_color:06X}"

    payload = {
        "colors": {
            "primary_color": primary_color,
            "secondary_color": secondary_color
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        print(f"✅ Set gradient  #{primary_hex} → #{secondary_hex}")
        return primary_hex, secondary_hex
    else:
        print(f"❌ Failed to update role: {response.status_code} - {response.text}")


def get_color_name_from_hex(hex_color: str) -> str:
    """Try to name a color from a hex string, fallback to hex."""
    try:
        return webcolors.hex_to_name(hex_color, spec="css3")
    except ValueError:
        # Find the closest named CSS3 color by RGB distance
        r, g, b = webcolors.hex_to_rgb(hex_color)
        min_distance = float("inf")
        closest_name = hex_color
        for name in webcolors.names("css3"):
            cr, cg, cb = webcolors.name_to_rgb(name)
            distance = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if distance < min_distance:
                min_distance = distance
                closest_name = name
        return closest_name


@bot.tree.command(name="randomcolors", description="Assigns you a role and changes its color", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(remove="Set this to true to remove the role instead of assigning a color")
async def randomcolors(interaction: discord.Interaction, remove: bool = False):
    guild = interaction.guild
    member = interaction.user
    user_id = member.id

    now = time.time()

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    member_has_role = role in member.roles

    if remove:
        if member_has_role:
            await member.remove_roles(role, reason="User requested role removal")
            await interaction.response.send_message(f"The **{ROLE_NAME}** role has been removed from your account.", ephemeral=True)
        else:
            await interaction.response.send_message(f"You don't have the **{ROLE_NAME}** role.", ephemeral=True)
        return

    if user_id in last_used and now - last_used[user_id] < 30:
        await interaction.response.send_message("Please wait before using this command again!", ephemeral=True)
        return
    last_used[user_id] = now

    guild = interaction.guild
    member = interaction.user

    # Assign role if not already present
    if not member_has_role:
        await member.add_roles(role, reason="randomcolors command used")

    primary_hex, secondary_hex = await set_gradient_role_color(guild.id, role.id)
    if not primary_hex:
        await interaction.response.send_message("Something went wrong while setting the gradient colors.", ephemeral=True)
        return

    primary_name = get_color_name_from_hex(primary_hex)
    secondary_name = get_color_name_from_hex(secondary_hex)

    embed = discord.Embed(
        title="🎨Random Colors Role Gradient Updated",
        description=(
            f"{member.mention} updated the **{ROLE_NAME}** role to a gradient!\n"
            f"**{primary_name.title()} → {secondary_name.title()}**"
        ),
        color=int(primary_hex.strip("#"), 16)
    )

    # Send ephemeral confirmation to user
    await interaction.response.send_message(f"✅ Your gradent of **{primary_name.title()} → {secondary_name.title()}** was applied!", ephemeral=True)

    # Send public embed to log channel
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)
    else:
        print(f"⚠️ Log channel ID {LOG_CHANNEL_ID} not found.")


bot.run(TOKEN)
