import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import DBHandler as Database
import logging

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
        await self.tree.sync()
        logger.info("CPO setup completed.")

    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info(f"Users: {len(set(self.get_all_members()))}")

        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
        for command in synced:
            logger.info(f"  - {command.name}")

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
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
    else:
        logger.exception(f"An error occurred in app command: {error}")
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in .env file")
    elif not BOT_DEVELOPER_ID:
        logger.warning("BOT_DEVELOPER_ID not found in .env file. Some features may be limited.")
        cpo.run(TOKEN)
    else:
        logger.info("Starting the bot...")
        cpo.run(TOKEN)