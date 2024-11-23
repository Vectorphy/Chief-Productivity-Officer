import discord
from discord import app_commands
from discord.ext import commands
import logging
from enum import Enum
from functools import wraps
from typing import List


# Set up logging
logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    BOT_DEVELOPER = 4
    GUILD_MANAGER = 3
    GROUP_OWNER = 2
    GROUP_MEMBER = 1
    REGULAR_USER = 0


class Manager(commands.Cog):
    max_sessions = 5
    max_groups = 6
    max_overall = 10


    def __init__(self, bot):
        self.bot = bot
        logger.info("Manager cog initialized")

        




    ### --- DECORATOR FUNCTIONS --- ###

    # Decorator to check if user is a member
    def is_member(func):
        @wraps(func)
        async def wrapper(instance, interaction: discord.Interaction, *args, **kwargs):
            user_id = interaction.user.id
            member_list : List[int]= []
            class_name : str = ""
            session_name : str = ""
            logger.info(f"Checking if user {interaction.user.display_name} is a member...")

            # Check for CheckinSession
            if instance.__class__.__name__ == "CheckinSession":
                member_list = instance.member_ids
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info(f"Instance is of type CheckinSession")

            # Check for StudyGroup
            if instance.__class__.__name__ == "StudyGroup":
                member_list = instance.member_ids
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info(f"Instance is of type StudyGroup")
            
            if user_id in member_list:
                logger.info(f"User {interaction.user.display_name} is a member of {class_name} with name: {session_name}")
                return await func(instance, interaction, *args, **kwargs)
            else:
                logger.warning(f"User {interaction.user.display_name} is not a member of {class_name} with name: {session_name}")
                await interaction.response.send_message(f"You are not a member of this {class_name} with name: {session_name}.", ephemeral=True)
        return wrapper
    

    # Decorator to check if user is the owner
    def is_owner(func):
        @wraps(func)
        async def wrapper(instance, interaction: discord.Interaction, *args, **kwargs):
            user_id = interaction.user.id
            owner_id : int = 0
            class_name : str = ""
            session_name : str = ""
            logger.info(f"Checking if user {interaction.user.display_name} is a member...")

            # Check for CheckinSession
            if instance.__class__.__name__ == "CheckinSession":
                owner_id = instance.owner_id
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info(f"Instance is of type CheckinSession")

            # Check for StudyGroup
            if instance.__class__.__name__ == "StudyGroup":
                owner_id = instance.owner_id
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info(f"Instance is of type StudyGroup")
            
            if user_id == owner_id:
                logger.info(f"User {interaction.user.display_name} is a the owner of {class_name} with name: {session_name}")
                return await func(instance, interaction, *args, **kwargs)
            else:
                logger.warning(f"User {interaction.user.display_name} is not the owner of {class_name} with name: {session_name}")
                await interaction.response.send_message(f"You are not the owner of this {class_name} with name: {session_name}.", ephemeral=True)
        return wrapper


    ## Check the max sessions / groups of a user
    ## Expand as neeeded for other group / modules
    def check_user_groups(func):
        @wraps(func)
        async def wrapper(cog_instance, interaction: discord.Interaction, *args, **kwargs):
            logger.info(f"Checking if user {interaction.user.display_name} can join more modules...")
            user_id = interaction.user.id
            class_name = ""
            checkin_count = 0
            study_group_count = 0
            overall_count = 0

            # Check user participation in 'CheckinSession's
            if cog_instance.__class__.__name__ == "CheckinCog":
                class_name = type(cog_instance).__name__
                logger.info(f"Instance is of type CheckinCog")
                checkin_count = sum(user_id in session.member_ids for session in cog_instance.active_sessions.values())
                overall_count += checkin_count
                logger.info(f"User {interaction.user.display_name} has {checkin_count} checkin sessions")
                if checkin_count >= Manager.max_sessions:
                    logger.info(f"User {interaction.user.display_name} has joined {checkin_count} checkin sessions, more than the limit of {Manager.max_sessions}")
                    await interaction.response.send_message(f"You are already in {checkin_count} check-in sessions. You can't join more.", ephemeral=True)
                    return

            # Check user participation in StudyGroups
            if cog_instance.__class__.__name__ == "StudyGroupCog":
                class_name = type(cog_instance).__name__
                logger.info(f"Instance is of type StudyGroupCog")
                checkin_count = sum(user_id in study_group.member_ids for study_group in cog_instance.active_study_groups.values())
                overall_count += study_group_count
                logger.info(f"User {interaction.user.display_name} has {study_group_count} study groups")
                if study_group_count >= Manager.max_groups:
                    logger.info(f"User {interaction.user.display_name} has joined {study_group_count} study groups, more than the limit of {Manager.max_groups}")
                    await interaction.response.send_message(f"You are already in {study_group_count} study groups. You can't join more.", ephemeral=True)
                    return

            # Check overall participation limit
            if overall_count >= Manager.max_overall:
                logger.info(f"User {interaction.user.display_name} has joined {overall_count} total modules, more than the limit of {Manager.max_overall}")
                await interaction.response.send_message(f"You are already in {overall_count} total groups/sessions. You can't join more.", ephemeral=True)
                return

            # If checks pass, proceed to the function
            logger.info(f"User {interaction.user.display_name} can this module of {class_name}")
            return await func(cog_instance, interaction, *args, **kwargs)
        return wrapper
  


    async def get_permission_level(self, guild_id, user_id):
        if user_id == self.bot.bot_developer_id:
            logger.debug(f"User {user_id} identified as bot developer")
            return PermissionLevel.BOT_DEVELOPER

        manager = await self.bot.db.get_manager(user_id, guild_id)
        if manager:
            permission_level = manager['permission_level']
            logger.debug(f"User {user_id} has permission level {permission_level}")
            return permission_level
        logger.debug(f"User {user_id} has regular user permissions")
        return PermissionLevel.REGULAR_USER

    @app_commands.command(name="add_bot_developer", description="Add a bot developer (Bot Developer only)")
    @app_commands.describe(user="The user to add as a bot developer")
    async def add_bot_developer(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to add bot developer: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to add bot developer without permission")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.add_manager(user.id, None, PermissionLevel.BOT_DEVELOPER)
        logger.info(f"Added {user.id} as bot developer")
        await interaction.response.send_message(f"{user.name} has been added as a bot developer.", ephemeral=True)

    @app_commands.command(name="add_guild_manager", description="Add a guild manager (Bot Developer only)")
    @app_commands.describe(user="The user to add as a guild manager")
    async def add_guild_manager(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to add guild manager: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to add guild manager without permission")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.add_manager(user.id, interaction.guild_id, PermissionLevel.GUILD_MANAGER)
        logger.info(f"Added {user.id} as guild manager for guild {interaction.guild_id}")
        await interaction.response.send_message(f"{user.name} has been added as a guild manager for this server.", ephemeral=True)

    @app_commands.command(name="remove_guild_manager", description="Remove a guild manager (Bot Developer only)")
    @app_commands.describe(user="The user to remove as a guild manager")
    async def remove_guild_manager(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to remove guild manager: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to remove guild manager without permission")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.remove_manager(user.id, interaction.guild_id)
        logger.info(f"Removed {user.id} as guild manager for guild {interaction.guild_id}")
        await interaction.response.send_message(f"{user.name} has been removed as a guild manager for this server.", ephemeral=True)

    @app_commands.command(name="list_managers", description="List all managers for this server")
    async def list_managers(self, interaction: discord.Interaction):
        logger.info(f"Listing managers for guild {interaction.guild_id}")
        managers = await self.bot.db.get_all_managers(interaction.guild_id)
        

        embed = discord.Embed(title="Managers", color=discord.Color.blue())
        for manager in managers:
            user = await self.bot.fetch_user(manager['user_id'])
            level = "Bot Developer" if manager['guild_id'] is None else "Guild Manager"
            embed.add_field(name=f"{user.name}#{user.discriminator}", value=level, inline=False)

        logger.debug(f"Found {len(managers)} managers for guild {interaction.guild_id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_permission_level", description="Set the permission level for a user (Bot Developer only)")
    @app_commands.describe(
        user="The user to set permissions for",
        level="The permission level to set (0: Regular User, 1: Group Creator, 2: Guild Manager, 3: Bot Developer)"
    )
    async def set_permission_level(self, interaction: discord.Interaction, user: discord.User, level: int):
        logger.info(f"Attempt to set permission level for user {user.id} to level {level} by user {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to set permission level without being a Bot Developer")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if level not in [0, 1, 2, 3]:
            logger.warning(f"Invalid permission level {level} specified")
            await interaction.response.send_message("Invalid permission level. Please use 0, 1, 2, or 3.", ephemeral=True)
            return

        if level == 0:
            await self.bot.db.remove_manager(user.id, interaction.guild_id)
            logger.info(f"Removed all permissions for user {user.id}")
        else:
            guild_id = None if level == PermissionLevel.BOT_DEVELOPER else interaction.guild_id
            await self.bot.db.add_manager(user.id, guild_id, level)
            logger.info(f"Set permission level {level} for user {user.id} in guild {guild_id}")

        permission_names = ["Regular User", "Group Creator", "Guild Manager", "Bot Developer"]
        await interaction.response.send_message(f"Set {user.name}'s permission level to {permission_names[level]}.", ephemeral=True)

async def setup(bot):

    await bot.add_cog(Manager(bot))
    logger.info("Manager cog loaded")

    
