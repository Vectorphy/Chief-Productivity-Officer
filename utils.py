import logging
import random
import re
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

### Parsing Time Functions

def parse_seconds_to_hms(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: List[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or len(parts) == 0:  # Always show seconds if it's the only component
        parts.append(f"{seconds}s")
    result = " ".join(parts)
    logger.debug(f"Parsed {seconds} seconds to {result}")
    return result

def parse_duration(duration_str: str) -> Optional[int]:
    logger.debug(f"Attempting to parse duration: {duration_str}")
    match = re.match(r'(\d+)\s*(s|secs?|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?)', duration_str, re.IGNORECASE)
    if not match:
        logger.warning(f"Failed to parse duration: {duration_str}")
        return None
    value_str, unit = match.groups()
    value = int(value_str)
    unit = unit.lower()
    if 's' in unit:
        result: Optional[int] = value
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
def parse_mentions(interaction: discord.Interaction, mentions: str) -> List[int]:
    logger.info(f"Parsing mentions: {mentions}")
    logger.info(f"Interaction User: {interaction.user} and Interaction Guild: {interaction.guild}")
    if not interaction.guild:
        return [interaction.user.id]

    member_ids: set[int] = set()

    # Extract all role mentions <@&ROLE_ID>
    role_ids = re.findall(r'<@&(\d+)>', mentions)
    for r_id_str in role_ids:
        role_id = int(r_id_str)
        role = interaction.guild.get_role(role_id)
        if role:
            for member in role.members:
                member_ids.add(member.id)

    # Extract all user mentions <@USER_ID> or <@!USER_ID>
    user_ids = re.findall(r'<@!?(\d+)>', mentions)
    for u_id_str in user_ids:
        member_ids.add(int(u_id_str))

    # Also extract any standalone numeric IDs
    for word in mentions.split():
        clean_word = word.strip(',;()[]')
        if clean_word.isdigit() and len(clean_word) >= 17:
            member_ids.add(int(clean_word))

    # Always include interaction author
    if interaction.user:
        member_ids.add(interaction.user.id)

    result = list(member_ids)
    logger.info(f"Parsed mention user IDs: {result}")
    return result



### Validation Functions
async def validate_parameters(
    interaction: discord.Interaction,
    name: Optional[str] = None,
    member_ids: Optional[List[int]] = None,
    category: Optional[discord.CategoryChannel] = None,
    duration: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_members: Optional[int] = None,
) -> Optional[bool]:
    """
    A unified parameter validation function for all modules (Checkin, Study Group).
    Parameters are optional, and validation will only be performed for those passed.
    Parameters:
    - name: Name - Study Group
    - member_ids: List of Member IDs - Checkin, Study Group
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
        if max_members is not None and max_members < 0:
            await interaction.followup.send("The maximum number of members must be non-negative.", ephemeral=True)
            logger.warning(f"Invalid max_members provided: {max_members} by user {interaction.user}")
            return False

        # 3. Validate member_ids if provided (fetching Members by IDs)
        if member_ids is not None:
            guild = interaction.guild
            if not guild:
                return False
            members = []
            for member_id in member_ids:
                member = guild.get_member(member_id)
                if member is None:
                    try:
                        member = await guild.fetch_member(member_id)
                    except (discord.NotFound, discord.HTTPException):
                        member = None
                members.append(member)

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
            if not interaction.guild or category.id not in [c.id for c in interaction.guild.categories]:
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

    if not guild:
        logger.error("Guild is None in check_manager")
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

    # 1. Bot Developer Superuser
    if getattr(bot, 'bot_developer_id', None) == user.id:
        logger.info(f"User {user.name} is bot developer (manager access granted)")
        return True

    # 2. Server Owner
    if getattr(guild, 'owner_id', None) == user.id:
        logger.info(f"User {user.name} is server owner (manager access granted)")
        return True

    user_roles = getattr(user, 'roles', [])
    guild_perms = getattr(user, 'guild_permissions', None)

    # 3. Server Administrator or Moderator Level Permissions
    is_admin = getattr(guild_perms, 'administrator', False) if guild_perms else False
    is_mod = bool(
        is_admin or
        (guild_perms and (
            guild_perms.manage_guild or
            guild_perms.manage_channels or
            guild_perms.manage_roles or
            guild_perms.moderate_members or
            guild_perms.kick_members or
            guild_perms.ban_members
        ))
    )
    if is_mod:
        logger.info(f"User {user.name} has moderator/admin guild permissions (manager access granted)")
        return True

    # 4. Moderator / Admin / Staff Role Names
    mod_role_keywords = {'admin', 'administrator', 'mod', 'moderator', 'manager', 'lead', 'owner', 'staff'}
    has_mod_role = any(
        any(kw in role.name.lower() for kw in mod_role_keywords)
        for role in user_roles
    )
    if has_mod_role:
        logger.info(f"User {user.name} has a moderator/admin role by name (manager access granted)")
        return True

    # 5. Database Manager Lookup
    if hasattr(bot, 'db') and hasattr(bot.db, 'get_manager'):
        try:
            db_manager = await bot.db.get_manager(user.id, guild_id)
            if db_manager and (db_manager['permission_level'] >= 2 or db_manager['guild_id'] is None):
                logger.info(f"User {user.name} is a registered manager in the database")
                return True
        except Exception as e:
            logger.debug(f"Error querying db for manager status: {e}")

    # 6. In-memory manager arrays
    is_manager = (
        any(role.id in bot.manager_roles[guild_id] for role in user_roles) or
        user.id in bot.manager_members[guild_id]
    )
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
        logger.debug(f"Checking if user is group creator or manager: {interaction.user}")
        if getattr(interaction.client, 'bot_developer_id', None) == interaction.user.id:
            return True
        if await check_manager(interaction):
            return True
        group = await interaction.client.db.get_study_group(interaction.guild_id)
        if not group:
            return False
        creator_id = group['creator_id'] if 'creator_id' in group.keys() else group[4]
        owner_id = group['owner_id'] if 'owner_id' in group.keys() else group[5]
        is_creator_or_owner = bool(interaction.user.id in (creator_id, owner_id))
        logger.info(f"User {interaction.user.name} is {'authorized' if is_creator_or_owner else 'not authorized'} as group creator/owner")
        return is_creator_or_owner
    return app_commands.check(predicate)


class ProductivityService:
    def __init__(self, db_handler):
        self.db = db_handler

    async def get_productivity_metrics(self, user_id):
        tasks_completed = await self.get_tasks_completed(user_id)
        time_spent = self.get_mock_time_spent()
        efficiency_score = self.calculate_efficiency(tasks_completed, time_spent)

        return {
            "tasks_completed": tasks_completed,
            "time_spent": time_spent,
            "efficiency_score": efficiency_score,
        }

    async def get_tasks_completed(self, user_id):
        tasks = await self.db.get_user_tasks(user_id)
        completed_tasks = [task for task in tasks if task['completed']]
        return len(completed_tasks)

    def get_mock_time_spent(self):
        # Generate a random number of hours between 1 and 40
        return random.randint(1, 40)

    def calculate_efficiency(self, tasks, time):
        if time == 0:
            return 0.0
        return round(tasks / time, 2)
