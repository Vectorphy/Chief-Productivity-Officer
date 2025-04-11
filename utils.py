import discord
from discord import app_commands
import logging
from typing import Union

logger = logging.getLogger(__name__)


async def check_manager(ctx_or_interaction: Union[discord.Interaction, discord.ext.commands.Context], db_handler) -> bool:
    """
    Checks if the user has manager permissions within the given context.

    Args:
        ctx_or_interaction (Union[discord.Interaction, discord.ext.commands.Context]): The context of the command, which could be an interaction or a command context.

    Returns:
        bool: True if the user has manager permissions, False otherwise.
    """
    if isinstance(ctx_or_interaction, discord.Interaction):
        guild = ctx_or_interaction.guild
        user = ctx_or_interaction.user
    elif isinstance(ctx_or_interaction, discord.ext.commands.Context):
        guild = ctx_or_interaction.guild
        user = ctx_or_interaction.author
    else:
        logger.error(f"Unexpected context type in check_manager: {type(ctx_or_interaction)}")
        return False

    try:
        is_user_manager = await db_handler.is_manager(user.id, guild.id)
        logger.info(f"User {user.name} is {'a' if is_user_manager else 'not a'} manager in guild {guild.name}")
        return is_user_manager or user.guild_permissions.administrator
    except Exception as e:
        logger.error(f"Error checking manager status: {e}")
        return False


def is_manager(db_handler):
    """
    Decorator to check if the command invoker is a manager.

    Args:
        db_handler: The database handler instance.

    Returns:
        A decorator that can be used with application commands.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_manager(interaction, db_handler)

    return app_commands.check(predicate)


def is_group_creator(db):
    """
    Decorator to check if the command invoker is the creator of the study group.
    """

    async def predicate(interaction: discord.Interaction):
        logger.debug(f"Checking if user is group creator: {interaction.user} in channel {interaction.channel.id}")
        group = await db.fetch_study_group_by_id(str(interaction.channel.id))
        if not group:
            logger.info(f"No group found for channel {interaction.channel.id}")
            return False
        is_creator = group["creator_id"] == interaction.user.id
        logger.info(f"User {interaction.user.name} is {'the' if is_creator else 'not the'} group creator")
        return is_creator

    return app_commands.check(predicate)
