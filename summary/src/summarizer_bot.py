import asyncio
import discord
import logging
import traceback

from discord.ui import View, Button
from discord import Interaction
from discord import app_commands
from discord.ext import commands
import os
import time
from mistralai import Mistral
from dotenv import load_dotenv

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ShareSummaryView(View):
    """View with Yes/No buttons asking to share summary in the channel."""
    def __init__(self, summary: str, channel, requesting_user, count: int, message=None):
        super().__init__(timeout=180)
        self.summary = summary
        self.channel = channel
        self.requesting_user = requesting_user
        self.count = count
        self.message = message
        
        # Log view creation
        logger.info(f"ShareSummaryView created - User: {requesting_user.id} ({requesting_user.name}), Channel: {channel.id} ({channel.name}), Count: {count}")

    async def on_timeout(self):
        """Called when the view times out"""
        logger.warning(f"ShareSummaryView timed out - User: {self.requesting_user.id}, Channel: {self.channel.id}")
        
        # If we have a reference to the message, delete it and send a timeout notification
        if self.message:
            try:
                # Delete the original message with the Yes/No buttons
                await self.message.delete()
                logger.info(f"Deleted original share prompt message after timeout for user {self.requesting_user.id}")
                
                # Send a new message explaining the timeout
                timeout_message = (
                    "⏰ **Time limit reached!**\n"
                    "The share option has expired after 3 minutes. If you'd like to share a summary with the channel, "
                    "please generate a new summary using `/summarize` again."
                )
                
                await self.message.channel.send(timeout_message)
                logger.info(f"Sent timeout notification to user {self.requesting_user.id}")
                
            except discord.NotFound:
                # Message was already deleted
                logger.info(f"Original message already deleted for user {self.requesting_user.id}")
            except discord.Forbidden:
                # Don't have permission to delete the message
                logger.error(f"No permission to delete message for user {self.requesting_user.id}")
                # Disable all buttons as fallback
                for item in self.children:
                    item.disabled = True
            except Exception as e:
                logger.error(f"Error handling timeout for user {self.requesting_user.id}: {e}")
                # Disable all buttons as fallback
                for item in self.children:
                    item.disabled = True
        else:
            # Fallback to original behavior if no message reference
            logger.warning(f"No message reference available for timeout handling - User: {self.requesting_user.id}")
            for item in self.children:
                item.disabled = True

    async def on_error(self, interaction: Interaction, error: Exception, item):
        """Called when an error occurs in the view"""
        logger.error(f"ShareSummaryView error - User: {interaction.user.id}, Channel: {self.channel.id}, Error: {error}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing your request.", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Failed to send error message to user: {followup_error}")

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: Interaction, button: Button):
        logger.info(f"Yes button clicked - User: {interaction.user.id} ({interaction.user.name}), Channel: {self.channel.id}")
        
        try:
            # Check if the user who clicked is the same as who requested
            if interaction.user.id != self.requesting_user.id:
                logger.warning(f"Unauthorized button click - Clicker: {interaction.user.id}, Requester: {self.requesting_user.id}")
                await interaction.response.send_message("❌ Only the person who requested the summary can share it.", ephemeral=True)
                return

            # Check bot permissions
            bot_member = self.channel.guild.get_member(interaction.client.user.id)
            if not bot_member:
                logger.error(f"Bot member not found in guild {self.channel.guild.id}")
                await interaction.response.send_message("❌ Bot permissions error. Please contact an admin.", ephemeral=True)
                return

            channel_permissions = self.channel.permissions_for(bot_member)
            if not channel_permissions.send_messages:
                logger.error(f"Bot lacks send_messages permission in channel {self.channel.id}")
                await interaction.response.send_message("❌ I don't have permission to send messages in this channel.", ephemeral=True)
                return

            if not channel_permissions.view_channel:
                logger.error(f"Bot lacks view_channel permission in channel {self.channel.id}")
                await interaction.response.send_message("❌ I don't have permission to view this channel.", ephemeral=True)
                return

            # Acknowledge the interaction first
            await interaction.response.send_message("✅ Sharing the summary with the channel...", ephemeral=True)
            
            # Send the summary to the channel
            summary_message = f"**Summary of the last {self.count} messages:** (requested by {self.requesting_user.mention})\n{self.summary}"
            
            # Check if summary is too long for Discord
            if len(summary_message) > 2000:
                logger.warning(f"Summary message too long ({len(summary_message)} chars), truncating")
                summary_message = summary_message[:1997] + "..."
            
            sent_message = await self.channel.send(summary_message)
            logger.info(f"Summary successfully shared - Message ID: {sent_message.id}, Channel: {self.channel.id}")
            
            # Update the ephemeral response
            await interaction.edit_original_response(content="✅ Successfully shared the summary with the channel!")
            
        except discord.Forbidden as e:
            logger.error(f"Forbidden error when sharing summary: {e}")
            await interaction.edit_original_response(content="❌ I don't have permission to send messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"HTTP error when sharing summary: {e}")
            await interaction.edit_original_response(content="❌ Failed to send the summary due to a Discord API error.")
        except Exception as e:
            logger.error(f"Unexpected error when sharing summary: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await interaction.edit_original_response(content="❌ An unexpected error occurred while sharing the summary.")
        finally:
            self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
    async def no_button(self, interaction: Interaction, button: Button):
        logger.info(f"No button clicked - User: {interaction.user.id} ({interaction.user.name}), Channel: {self.channel.id}")
        
        try:
            # Check if the user who clicked is the same as who requested
            if interaction.user.id != self.requesting_user.id:
                logger.warning(f"Unauthorized no button click - Clicker: {interaction.user.id}, Requester: {self.requesting_user.id}")
                await interaction.response.send_message("❌ Only the person who requested the summary can dismiss this.", ephemeral=True)
                return

            await interaction.response.send_message("✅ Okay, I won't share it.", ephemeral=True)
            logger.info(f"User chose not to share summary - User: {interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error in no_button: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            self.stop()


load_dotenv()

USER_COOLDOWNS = {}
COOLDOWN_SECONDS = 600
MAX_USES_PER_COOLDOWN = 3

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

async def summarize_with_mistral_async(messages: list[str]) -> str:
    return await asyncio.to_thread(summarize_with_mistral, messages)


def summarize_with_mistral(messages: list[str]) -> str:
    """Return a summary ≤ 1900 characters. Two‑pass self‑condense strategy."""
    logger.info(f"Starting summarization for {len(messages)} messages")
    
    chat_text = "\n".join(messages)
    logger.debug(f"Chat text length: {len(chat_text)} characters")

    system_base = (
        "You're a friendly and funny group member catching someone up on what they missed in the Discord chat. "
        "Summarize the conversation in a natural, human tone — like you're telling a friend what happened while highlighting the main things people said. "
        "Stick to what was actually said — don't make up names, jokes, or facts that weren't in the messages. Be accurate, helpful, and fun. "
        "Try to remember to keep the order of events and don't jumble them. "
        "Pay attention to reply chains - when someone replies to another message, understand the context and connection. "
        "Messages formatted as 'Name (replying to OtherName: \"quoted text\"): response' show reply relationships. "
        "Do not offer the user options for follow-up or additional questions. They cannot respond to you. Simply deliver the summary and stop. "
        f"***Your entire response MUST be no longer than 1900 characters, including line breaks.***"
    )

    try:
        # First attempt with tight token limit
        logger.info("Making first Mistral API call")
        first = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": system_base},
                {"role": "user", "content": f"Summarize the following conversation:\n\n{chat_text}"}
            ],
            temperature=0.2,
            max_tokens=450,
        ).choices[0].message.content.strip()

        logger.info(f"First summary length: {len(first)} characters")

        # If it's within limit, return
        if len(first) <= 1900:
            logger.info("First summary within character limit, returning")
            return first

        # Second pass: ask model to condense its own draft
        logger.info("First summary too long, making second API call to condense")
        refine_prompt = (
            f"This draft is {len(first)} characters long. "
            f"Please shorten it to ≤ 1900 characters WITHOUT losing key info.\n\n{first}"
        )

        second = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": system_base},
                {"role": "user", "content": refine_prompt}
            ],
            temperature=0.2,
            max_tokens=350,
        ).choices[0].message.content.strip()

        logger.info(f"Second summary length: {len(second)} characters")

        # Final safeguard
        final_summary = second if len(second) <= 1900 else second[:1900]
        logger.info(f"Final summary length: {len(final_summary)} characters")
        return final_summary

    except Exception as e:
        logger.error(f"Mistral API error: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return "⚠️ Failed to summarize messages."


TOKEN =os.environ["BOT_TOKEN"]
GUILD_ID = os.environ["GUILD_ID"]
MAX_MESSAGES = 200
MIN_MESSAGES = 5

intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        logger.info(f"Synced {len(synced)} command(s) to guild {GUILD_ID}")
    except Exception as e:
        logger.error(f"Command sync failed: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Bot error in event {event}: {args}, {kwargs}")
    logger.error(f"Full traceback: {traceback.format_exc()}")

@bot.tree.command(name="summarize", description="Summarize the last X messages", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(count=f"Number of messages to summarize (between {MIN_MESSAGES} and {MAX_MESSAGES})")
async def summarize(interaction: discord.Interaction, count: int):
    user_id = interaction.user.id
    now = time.time()
    
    logger.info(f"Summarize command called - User: {user_id} ({interaction.user.name}), Channel: {interaction.channel.id} ({interaction.channel.name}), Count: {count}")

    # Check if user has administrator permissions (unlimited usage)
    is_admin = interaction.user.guild_permissions.administrator
    
    if not is_admin:
        # Enforce cooldown for non-admin users
        user_usage = USER_COOLDOWNS.get(user_id, [])
        
        # Remove timestamps older than cooldown period
        user_usage = [timestamp for timestamp in user_usage if now - timestamp < COOLDOWN_SECONDS]
        
        if len(user_usage) >= MAX_USES_PER_COOLDOWN:
            # Find the oldest usage to calculate when they can use again
            oldest_usage = min(user_usage)
            remaining = int(COOLDOWN_SECONDS - (now - oldest_usage))
            logger.info(f"User {user_id} hit usage limit, {remaining} seconds remaining")
            await interaction.response.send_message(
                f"⏳ You've used your {MAX_USES_PER_COOLDOWN} uses for this 10-minute period. Please wait {remaining} more seconds.", ephemeral=True
            )
            return
        
        # Update user's usage history
        user_usage.append(now)
        USER_COOLDOWNS[user_id] = user_usage
    
    if count > MAX_MESSAGES:
        logger.info(f"User {user_id} requested too many messages: {count}")
        await interaction.response.send_message(
            f"Limit is {MAX_MESSAGES} messages at a time.", ephemeral=True
        )
        return
    if count < MIN_MESSAGES:
        logger.info(f"User {user_id} requested too few messages: {count}")
        await interaction.response.send_message(
            f"Minimum messages to summarize is {MIN_MESSAGES}.", ephemeral=True
        )
        return

    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
        logger.info(f"Deferred interaction for user {user_id}")

        # Fetch messages (most recent first)
        messages = []
        message_count = 0
        logger.info(f"Starting to fetch messages from channel {interaction.channel.id}")
        
        async for msg in interaction.channel.history(limit=count, oldest_first=False):
            message_count += 1
            if msg.author.bot:
                logger.debug(f"Skipping bot message from {msg.author.name}")
                continue
            if not msg.content.strip():
                logger.debug(f"Skipping empty message from {msg.author.name}")
                continue

            # Resolve a user-friendly name (nickname if available)
            if isinstance(msg.author, discord.Member):
                name = msg.author.display_name
            else:
                member = interaction.guild.get_member(msg.author.id)
                name = member.display_name if member else msg.author.name

            # Check if this message is a reply
            message_text = f"{name}: {msg.content.strip()}"
            if msg.reference and msg.reference.message_id:
                try:
                    # Try to get the referenced message
                    referenced_msg = await interaction.channel.fetch_message(msg.reference.message_id)
                    if referenced_msg and not referenced_msg.author.bot:
                        # Get the referenced message author's display name
                        if isinstance(referenced_msg.author, discord.Member):
                            ref_name = referenced_msg.author.display_name
                        else:
                            ref_member = interaction.guild.get_member(referenced_msg.author.id)
                            ref_name = ref_member.display_name if ref_member else referenced_msg.author.name
                        
                        # Format as reply with context
                        ref_content = referenced_msg.content.strip()[:100] + ("..." if len(referenced_msg.content.strip()) > 100 else "")
                        message_text = f"{name} (replying to {ref_name}: \"{ref_content}\"): {msg.content.strip()}"
                except:
                    # If we can't fetch the referenced message, just use the original format
                    pass

            messages.append(message_text)

        logger.info(f"Fetched {message_count} total messages, {len(messages)} valid messages for summarization")

        # Reverse so oldest messages come first
        messages.reverse()

        if not messages:
            logger.warning(f"No valid messages found for user {user_id} in channel {interaction.channel.id}")
            await interaction.followup.send("⚠️ No valid messages found to summarize.", ephemeral=True)
            return

        await interaction.followup.send(
            f"✅ Collected {len(messages)} messages.\n\n📝 Summarizing...", ephemeral=True
        )

        summary = await summarize_with_mistral_async(messages)
        logger.info(f"Summary generated for user {user_id}, length: {len(summary)}")
        
        # Send the summary
        await interaction.followup.send(
            f"📋**Summary**\n━━━━━━━━━━━━━━━━━━\n{summary}", ephemeral=True
        )

        # Prompt user to share the summary
        view = ShareSummaryView(summary=summary, channel=interaction.channel, requesting_user=interaction.user, count=len(messages))
        share_message = await interaction.followup.send(
            "Would you like me to share this summary with the rest of the channel?",
            view=view,
            ephemeral=True
        )
        # Store the message reference in the view for timeout handling
        view.message = share_message
        logger.info(f"Share prompt sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in summarize command for user {user_id}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing your request.", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Failed to send error message to user {user_id}: {followup_error}")


# Run the bot
if __name__ == "__main__":
    logger.info("Starting Discord bot...")
    bot.run(TOKEN)
