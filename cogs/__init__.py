import os
import logging
from discord.ext import commands

logger = logging.getLogger(__name__)

async def setup_cogs(bot: commands.Bot, db) -> None:
    """Loads all cogs in the cogs directory.

    Args:
        bot (commands.Bot): The bot instance.
        db (DBHandler): The database handler instance.
    """
    cogs_dir = os.path.dirname(__file__)
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                cog_name = filename[:-3]
                await bot.load_extension(f"cogs.{cog_name}", db = db)
                logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}")
