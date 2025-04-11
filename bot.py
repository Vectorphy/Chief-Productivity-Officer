import logging
import os

import discord
from dotenv import load_dotenv


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

class CPO(discord.Bot):
    """
    Main bot class that inherits from discord.Bot.
    Handles bot initialization, setup, cog loading, and error handling.
    """
    def __init__(self, db_handler, bot_developer_id):
        super().__init__(command_prefix='!', intents=intents)
        self.db = db_handler
        self.bot_developer_id = bot_developer_id


        """
        Asynchronous setup hook that is called after the bot is initialized.
        Handles database connection, cog loading, and command syncing.
        """
        try:
            await self.db.connect()
        except motor.motor_asyncio.ServerSelectionTimeoutError:

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
        await super().close()
        logger.info("Bot has been closed.")

    async def load_cogs(self) -> None:
        """Loads all cogs (extensions) from the cogs directory."""
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_") and filename != "test_file.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}", db=self.db)
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except discord.errors.ExtensionError as e:
                    logger.error(f"Failed to load extension {filename[:-3]}: {e}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Command error handler.
        Handles specific command errors and logs other errors.
        """
        if isinstance(error, commands.CommandNotFound):\n        logger.warning(f"Command not found: {ctx.message.content}")\n        await ctx.reply("I don't know that command. Please use `/help` for a list of available commands.")\n    elif isinstance(error, commands.MissingPermissions):\n        logger.warning(f"Missing permissions for command: {ctx.message.content}")\n        await ctx.reply("You don't have the required permissions to use this command.")\n    elif isinstance(error, commands.CheckFailure):\n        logger.warning(f"Check failed for command: {ctx.message.content}")\n        await ctx.reply("You are not allowed to use this command.")\n    else:\n        logger.error(f"An error occurred: {error}")\n        await ctx.reply("An unexpected error occurred. Please try again later.")\n
    \n\n\n@cpo.event\nasync def on_error(event, *args, **kwargs):\n        """\n        Global error handler for uncaught exceptions.\n        Logs exceptions and their context.\n        """\n        logger.exception(f"Unhandled exception in event '{event}':")\n        # Consider sending a message to an error channel or logging to a file\n
        else:
            logger.error(f"An error occurred in app command: {error}")
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

    async def on_error(self, event, *args, **kwargs):
        """
        Global error handler for uncaught exceptions.
        Logs exceptions and their context.
        """
        logger.exception(f"Unhandled exception in event '{event}':")
        # Consider sending a message to an error channel or logging to a file
