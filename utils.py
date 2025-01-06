import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import time
import logging
import sys
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

### Parsing Time Functions

def parse_seconds_to_hms(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts : List[int] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or len(parts) == 0:  # Always show seconds if it's the only component
        parts.append(f"{seconds}s")
    result = " ".join(parts)
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


### Mentions Function
def parse_mentions(interaction: discord.Interaction, mentions : str) -> List[int]:
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

    member_ids = [member.id for member in members]
    return list(set(member_ids))  # Remove duplicates



### Validation Functions
async def validate_parameters(
    interaction: discord.Interaction,
    name: Optional[str] = None,
    member_ids: Optional[str] = None,
    category: Optional[discord.CategoryChannel] = None,
    duration: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_members: Optional[int] = None
) -> Optional[bool]:
    """
    A unified parameter validation function for all modules (Checkin, Study Group).
    Parameters are optional, and validation will only be performed for those passed.
    Parameters:
    - name: Name - Study Group
    - mentions: List of Member IDs - Checkin, Study Group
    - category: Category of Study Group
    Minimums and Maximum Values:
    - min_duration: The minimum duration of Checkin reminder
    - max_members: The maximum number of members - Checkin, Study Group
    """
    try:
        # 1. Validate the group name if provided
        if name is not None:
            if not name or len(name) > 100:
                await interaction.followup.send("Invalid group name. The name must be non-empty and less than 100 characters.", ephemeral=True)
                logger.warning(f"Invalid group name provided: {name} by user {interaction.user}")
                return False

        # 2. Check if the max_members given is a positive number
        if max_members < 0:
            await interaction.followup.send("The maximum number of members must be non-negative.", ephemeral=True)
            logger.warning(f"Invalid max_members provided: {max_members} by user {interaction.user}")
            return False
        
        # 3. Validate member_ids if provided (fetching Members by IDs)
        if member_ids is not None:
            guild = interaction.guild
            members = [guild.get_member(member_id) for member_id in member_ids]  # Fetch Members by IDs

            if not all(members):
                await interaction.followup.send("One or more members couldn't be found. Please mention valid users.", ephemeral=True)
                logger.warning(f"Some members in the mentions couldn't be found. User {interaction.user} provided mentions: {member_ids}")
                return False

            if max_members is not None and len(members) > max_members:
                await interaction.followup.send(f"Too many members specified. Max allowed: {max_members}.", ephemeral=True)
                logger.warning(f"Too many members ({len(members)}) compared to max_members: {max_members}. User {interaction.user}")
                return False

        # 4. Validate category if provided
        if category is not None:
            if category not in interaction.guild.categories:
                await interaction.followup.send("No valid category specified. Please provide a valid category.", ephemeral=True)
                logger.warning(f"Invalid category provided: {category}. User {interaction.user}")
                return False

        # 5. Validate duration if provided (for check-in)
        if duration is not None:
            duration_seconds = parse_duration(duration)
            if duration_seconds is None:
                await interaction.followup.send("Wrong duration format used. Please provide a valid duration like '2d 14h 25m 30s'.", ephemeral=True)
                logger.warning(f"Wrong duration format entered by user {interaction.user}: {duration}")
                return False
            if min_duration is not None and duration_seconds < min_duration:
                await interaction.followup.send(f"Duration must be at least {parse_seconds_to_hms(min_duration)}.", ephemeral=True)
                logger.warning(f"Attempted to start a session with insufficient duration by user {interaction.user}. Entered duration: {duration_seconds} (minimum: {min_duration} seconds).")
                return False

        return True

    except discord.Forbidden as forbidden_e:
        logger.error(f"Permission error during validation by user {interaction.user}: {forbidden_e}")
        await interaction.followup.send(f"Permission error occurred during validation: {forbidden_e}", ephemeral=True)
        return False

    except discord.HTTPException as http_e:
        logger.error(f"HTTP error during validation by user {interaction.user}: {http_e}")
        await interaction.followup.send(f"HTTP error occurred during validation: {http_e}", ephemeral=True)
        return False

    except Exception as e:
        logger.critical(f"Unexpected error during validation by user {interaction.user}: {e}")
        await interaction.followup.send(f"An unexpected error occurred during validation: {e}", ephemeral=True)
        return False




### Membership and Manager Functions



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
