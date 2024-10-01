import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import motor.motor_asyncio
from database import DBHandler as Database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class CPO(commands.Bot):
    """
    Main bot class that inherits from discord.ext.commands.Bot.
    Handles bot initialization, setup, cog loading, and error handling.
    """
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database()

    async def setup_hook(self) -> None:
        """
        Asynchronous setup hook that is called after the bot is initialized.
        Handles database connection, cog loading, and command syncing.
        """
        try:
            await self.db.connect()
        except motor.motor_asyncio.ServerSelectionTimeoutError:
            logger.critical("Could not connect to MongoDB (timeout). Check your connection string and network settings.")
            # Consider raising the exception or exiting the bot here
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")

        await self.load_cogs()
        try:
            await self.tree.sync()
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        logger.info("CPO setup completed.")

    async def close(self) -> None: 
        """
        Closes the database connection and the bot connection.
        """
        await self.db.close()
        await super().close()
        logger.info("Bot has been closed.")

    async def load_cogs(self) -> None:
        """Loads all cogs (extensions) from the cogs directory."""
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except commands.ExtensionError as e:
                    logger.error(f"Failed to load extension {filename[:-3]}: {e}")

    async def on_ready(self):
        """Event handler for when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info(f"Users: {len(set(self.get_all_members()))}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Command error handler.
        Handles specific command errors and logs other errors.
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Invalid command. Use `!help` for a list of commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {str(error)}")
        else:
            logger.error(f"An error occurred: {error}")
            await ctx.send("An error occurred while processing the command.")

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """
        Application command error handler.
        Handles cooldown and permission errors and logs other errors.
        """
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        elif isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"An error occurred in app command: {error}")
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """
        Global error handler for uncaught exceptions.
        Logs exceptions and their context.
        """
        logger.exception(f"Unhandled exception in event '{event}':")
        # Consider sending a message to an error channel or logging to a file
