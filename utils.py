import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import time
import logging
import sys

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

def parse_mentions(interaction: discord.Interaction, mentions : str):
    logger.info(f"Parsing mentions: {mentions}")
    logger.info(f"Interaction User: {interaction.user} and Interaction Guild: {interaction.guild}")
    members = []
    mention_list = mentions.split()

    for mention in mention_list:
        mention = mention.strip()
        if mention.startswith('<@&'):  # Role mention
            role_id = int(mention.strip('<@&>'))
            role = interaction.guild.get_role(role_id)
            if role:
                members.extend(role.members)
        elif mention.startswith('<@!') or mention.startswith('<@'):  # User mention
            user_id = int(mention.strip('<@!>').strip('<@>'))
            member = interaction.guild.get_member(user_id)
            if member:
                members.append(member)
                logger.info(f"Added member with username: {member.name}")
        
        members.append(interaction.user)
    
    return list(set(members))  # Remove duplicates


def generate_custom_id(action : str, session_id: str, namespace: str) -> str:
    """
    Generate a custom ID with the module namespace, action, and session ID.
    
    :param action: The action to be included in the custom ID.
    :param session_id: The session ID to be included in the custom ID.
    :return: A custom ID string in the format "namespace~action~session_id".
    """
    return f"{namespace}~{action}~{session_id}"


def parse_custom_id(interaction: discord.Interaction) -> tuple:
    """
    Parse a custom ID from a discord.Interaction into its namespace, action, and session ID components.
    
    :param interaction: The discord.Interaction object.
    :return: A tuple of (namespace, action, session_id) if valid, otherwise raises an error.
    :raises ValueError: If the custom ID format is invalid or not present.
    """
    # Log the entire interaction data for debugging
    logger.debug(f"Parse_Custom_ID: Interaction Data: {interaction}")
    

    if interaction.data and "custom_id" in interaction.data:
        custom_id = interaction.data["custom_id"]
        
        try:
            namespace, action, session_id = custom_id.split('~')
            
            # Log the details of the parsed components
            logger.info(f"Received custom_id: {custom_id}")
            logger.info(f"Namespace: {namespace}, Action: {action}, Session ID: {session_id}")
            
            return namespace, action, session_id
        
        except ValueError as ve:
            logger.error(f"Failed to parse custom_id: {custom_id} - Error: {ve}")
            raise ValueError(f"Invalid custom_id format: {custom_id} - {ve}")
    else:
        logger.error("No custom_id found in interaction data.")
        raise ValueError("No custom_id found in interaction data.")




### Assign Roles

async def assign_role_to_user(member: discord.Member, role: discord.Role):
    """
    Assigns a specified role to a member.

    :param member: The discord.Member object representing the user.
    :param role: The discord.Role object representing the role to be assigned.
    """
    try:
        await member.add_roles(role)
        return f"Role {role.name} has been assigned to {member.display_name}."
    except discord.Forbidden:
        return "I do not have permission to assign this role."
    except discord.HTTPException as e:
        return f"Failed to assign role: {str(e)}"
    except Exception as e:
        return f"An error occurred: {str(e)}"





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
