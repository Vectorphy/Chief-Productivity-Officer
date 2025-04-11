import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import time
import logging
from typing import List

logger = logging.getLogger(__name__)


async def check_manager(ctx_or_interaction):
    if isinstance(ctx_or_interaction, discord.Interaction):
        bot = ctx_or_interaction.client
        guild = ctx_or_interaction.guild
        user = ctx_or_interaction.user
    elif isinstance(ctx_or_interaction, commands.Context):
        bot = ctx_or_interaction.bot
        guild = ctx_or_interaction.guild
        user = ctx_or_interaction.author
    else:
        logger.error(f"Unexpected context type in check_manager: {type(ctx_or_interaction)}")
        return False

    guild_id = guild.id
    if not hasattr(bot, 'manager_roles'):
        logger.debug("Initializing bot.manager_roles")
        bot.manager_roles = {}
    if not hasattr(bot, 'manager_members'):
        logger.debug("Initializing bot.manager_members")
        bot.manager_members = {}

    if guild_id not in bot.manager_roles:
        bot.manager_roles[guild_id] = []
    if guild_id not in bot.manager_members:
        bot.manager_members[guild_id] = []
    
    user_roles = user.roles
    is_manager = (user.guild_permissions.administrator or 
                  any(role.id in bot.manager_roles[guild_id] for role in user_roles) or 
                  user.id in bot.manager_members[guild_id])
    logger.info(f"User {user.name} is {'a' if is_manager else 'not a'} manager")
    return is_manager

def is_manager():
    async def predicate(ctx):
        return await check_manager(ctx)
    return commands.check(predicate)

def app_is_manager():
    async def predicate(interaction):
        return await check_manager(interaction)
    return app_commands.check(predicate)

def is_group_creator():
    async def predicate(interaction):
        logger.debug(f"Checking if user is group creator: {interaction.user}")
        group = await interaction.client.db.get_study_group(interaction.guild_id)
        is_creator = group and group[2] == interaction.user.id  # Assuming creator_id is at index 2
        logger.info(f"User {interaction.user.name} is {'the' if is_creator else 'not the'} group creator")
        return is_creator
    return app_commands.check(predicate)
