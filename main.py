import asyncio
import logging
import os
import signal
import discord
from discord.ext import commands

from dotenv import load_dotenv
from bot import CPO, DBHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
BOT_DEVELOPER_ID = os.getenv('BOT_DEVELOPER_ID')


async def on_shutdown(db_handler: DBHandler):
    """Closes the database connection when the bot is shutting down."""
    logger.info("Closing database connection...")
    await db_handler.close()

async def setup_database():
    db_handler = DBHandler("bot_database.sqlite")
    await db_handler.connect()
    return db_handler

async def main():
    """
    Main function to start the bot.
    Handles loading environment variables, setting up signal handlers, and starting the bot.
    """
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in .env file")
        return

    if not BOT_DEVELOPER_ID:
        logger.warning("BOT_DEVELOPER_ID not found in .env file. Some features may be limited.")

    db_handler = await setup_database()

    # Bot instance
    cpo = CPO(db_handler)
    async with cpo:
        loop = asyncio.get_running_loop()

        async def handle_signal(signum):
            """Handles received signals (SIGINT, SIGTERM) for graceful shutdown."""
            logger.info(f"Received signal {signum}, shutting down...")
            loop.create_task(cpo.close())
            loop.stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal, sig)
        try:
            logger.info("Starting the bot...")
            await cpo.start(TOKEN)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected, shutting down...")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        finally:
            await cpo.close()
            await on_shutdown(db_handler)


if __name__ == "__main__":
    asyncio.run(main())


@cpo.event
async def on_command_error(ctx, error):
    """Handles errors that occur during command processing."""
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f"Command not found: {ctx.message.content}")
        await ctx.reply("I don't know that command. Please use `/help` for a list of available commands.")
    elif isinstance(error, commands.MissingPermissions):
        logger.warning(f"Missing permissions for command: {ctx.message.content}")
        await ctx.reply("You don't have the required permissions to use this command.")
    elif isinstance(error, commands.CheckFailure):
        logger.warning(f"Check failed for command: {ctx.message.content}")
        await ctx.reply("You are not allowed to use this command.")
    else:
        logger.error(f"An error occurred: {error}")
        await ctx.reply("An unexpected error occurred. Please try again later.")

