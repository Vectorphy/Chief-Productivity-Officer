import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

def parse_seconds_to_hms(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    result = f"{hours}h {minutes}m {seconds}s"
    logger.debug(f"Parsed {seconds} seconds to {result}")
    return result

def parse_duration(duration_str):
    logger.debug(f"Attempting to parse duration: {duration_str}")
    match = re.match(r'(\d+)\s*(s|secs?|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?)', duration_str, re.IGNORECASE)
    if not match:
        logger.warning(f"Failed to parse duration: {duration_str}")
        return None
    value, unit = match.groups()
    value = int(value)
    unit = unit.lower()
    if 's' in unit:
        result = value
    elif 'm' in unit:
        result = value * 60
    elif 'h' in unit:
        result = value * 3600
    elif 'd' in unit:
        result = value * 86400
    else:
        result = None
    logger.debug(f"Parsed duration '{duration_str}' to {result} seconds")
    return result

def parse_mentions(interaction: discord.Interaction, mentions: str):
    logger.info(f"Parsing mentions: {mentions}")
    mention_list = mentions.split()
    members = []

    for mention in mention_list:
        mention = mention.strip()
        if mention.startswith('<@&'):  # Role mention
            role_id = int(mention.strip('<@&>'))
            role = interaction.guild.get_role(role_id)
            if role:
                members.extend(role.members)
                logger.debug(f"Added {len(role.members)} members from role {role.name}")
            else:
                logger.warning(f"Role not found for ID: {role_id}")
        elif mention.startswith('<@!') or mention.startswith('<@'):  # User mention
            user_id = int(mention.strip('<@!>').strip('<@>'))
            member = interaction.guild.get_member(user_id)
            if member:
                members.append(member)
                logger.debug(f"Added member {member.name}")
            else:
                logger.warning(f"Member not found for ID: {user_id}")

    # Remove duplicates and ensure unique members
    unique_members = list(set(members))
    logger.info(f"Parsed {len(mention_list)} mentions into {len(unique_members)} unique members")
    return unique_members


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
