import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import DBHandler as Database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# TOKEN = "MTI2OTIzMTA3NDgwMjY2NzUzMA.Gf-Klh.B6EKURONxp5Q9q6toOibfc-feeivjyiiufhAz8" # For testing purposes
BOT_DEVELOPER_ID = os.getenv('BOT_DEVELOPER_ID')

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class CPO(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database()
        self.bot_developer_id = int(BOT_DEVELOPER_ID) if BOT_DEVELOPER_ID else None

    async def setup_hook(self):
        await self.db.connect()
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename[:-3]}: {e}")
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} command(s) globally.")
        logger.info("CPO setup completed.")

    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info(f"Users: {len(set(self.get_all_members()))}")
        # Clear any guild-scoped command copies so Discord only displays the global commands once
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Cleaned guild commands for '{guild.name}' ({guild.id}) to eliminate duplicates.")
            except Exception as e:
                logger.warning(f"Failed to clear guild commands for '{guild.name}' ({guild.id}): {e}")

    async def close(self):
        await self.db.close()
        await super().close()
        logger.info("Bot has been closed.")

cpo = CPO()

@cpo.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Use `!help` for a list of commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Bad argument: {str(error)}")
    else:
        logger.error(f"An error occurred: {error}")
        await ctx.send("An error occurred while processing the command.")

@cpo.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    actual_error = getattr(error, 'original', error)
    message = "An error occurred while processing the command."
    if isinstance(actual_error, discord.app_commands.CommandOnCooldown):
        message = f"This command is on cooldown. Try again in {actual_error.retry_after:.2f} seconds."
    elif isinstance(actual_error, discord.app_commands.MissingPermissions):
        message = "You don't have the required permissions to use this command."
    elif isinstance(actual_error, discord.app_commands.CheckFailure):
        message = str(actual_error) if str(actual_error) else "You don't have permission to use this command."
    else:
        logger.exception(f"An error occurred in app command: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            try:
                await interaction.response.send_message(message, ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(message, ephemeral=True)
    except Exception as exc:
        logger.exception(f"Failed to send error response to interaction: {exc}")


if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in .env file")
    elif not BOT_DEVELOPER_ID:
        logger.warning("BOT_DEVELOPER_ID not found in .env file. Some features may be limited.")
        cpo.run(TOKEN)
    else:
        logger.info("Starting the bot...")
        cpo.run(TOKEN)
