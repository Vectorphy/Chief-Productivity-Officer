import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import time
import logging
import sys
from typing import List, Optional

logger = logging.getLogger(__name__)

### Parsing Time Functions

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



### Mentions Function
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


### Custom ID Functions

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



### Validation Functions

async def validate_parameters(
    interaction: discord.Interaction,
    name: Optional[str] = None,
    max_size: Optional[int] = None,
    mentions: Optional[str] = None,
    category: Optional[discord.CategoryChannel] = None,
    duration: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_members: Optional[int] = None
) -> Optional[bool]:
    """
    A unified parameter validation function for all modules (Checkin, Study Group)
    Parameters are optional, and validation will only be performed for those passed.
    Parameters:
    - name: Name - Study Group
    - max_size: The maximum no of members - Checkin, Study Group 
    - mentions: List of Member IDs - Checkin, Study Group
    - category: Category of Study Group
    Minimums and Maximum Values:
    - min_duration: The minimum duration of Checkin reminder
    - max_members: The maximum no of members - Checkin, Study Group

    """
    try:
        # 1. Validate the group name if provided
        if name is not None:
            if not name or len(name) > 100:
                await interaction.followup.send("Invalid group name. The name must be non-empty and less than 100 characters.", ephemeral=True)
                logger.warning(f"Invalid group name provided: {name} by user {interaction.user}")
                return False

        # 2. Validate max size if provided
        if max_size is not None:
            if max_size <= 0:
                await interaction.followup.send(f"Invalid max_size: {max_size}. It must be a positive number.", ephemeral=True)
                logger.warning(f"Invalid max_size ({max_size}) provided by user {interaction.user}")
                return False

        # 3. Validate mentions if provided (fetching Members by IDs)
        if mentions is not None:
            guild = interaction.guild
            members = [guild.get_member(member_id) for member_id in mentions]  # Fetch Members by IDs

            if not all(members):
                await interaction.followup.send("One or more members couldn't be found. Please mention valid users.", ephemeral=True)
                logger.warning(f"Some members in the mentions couldn't be found. User {interaction.user} provided mentions: {mentions}")
                return False

            if max_size is not None and len(members) > max_size:
                await interaction.followup.send(f"Too many members specified. Max allowed: {max_size}.", ephemeral=True)
                logger.warning(f"Too many members ({len(members)}) compared to max_size: {max_size}. User {interaction.user}")
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

        # 6. Validate max members if provided (for check-in)
        if max_members is not None and mentions is not None:
            if len(mentions) > max_members:
                await interaction.followup.send(f"Too many members for the session. Maximum allowed is {max_members}.", ephemeral=True)
                logger.warning(f"Too many members ({len(mentions)}) compared to max_members: {max_members}. User {interaction.user}")
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



### Members and Roles Functions

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
