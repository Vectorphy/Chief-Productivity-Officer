import logging
from enum import IntEnum
from functools import wraps
from typing import Any, Callable, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

# Set up logging
logger = logging.getLogger(__name__)

class PermissionLevel(IntEnum):
    BOT_DEVELOPER = 4
    ADMIN = 3
    GUILD_MANAGER = 3  # Backward-compatible alias
    MODERATOR = 2
    GROUP_OWNER = 2    # Backward-compatible alias
    GROUP_MEMBER = 1
    REGULAR_USER = 0


class Manager(commands.Cog):
    max_sessions = 5
    max_groups = 6
    max_overall = 10

    @staticmethod
    def get_tier_name(level: int) -> str:
        """Maps permission level to high-level user tier: Admin, Mod, or User."""
        if level >= PermissionLevel.ADMIN:
            return "Admin"
        elif level >= PermissionLevel.MODERATOR:
            return "Mod"
        else:
            return "User"


    def __init__(self, bot):
        self.bot = bot
        logger.info("Manager cog initialized")






    ### --- DECORATOR FUNCTIONS --- ###

    # Decorator to check if user is a member
    @staticmethod
    def is_member(func: Callable[..., Any]) -> Callable[..., Any]:
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
                logger.info("Instance is of type CheckinSession")

            # Check for StudyGroup
            if instance.__class__.__name__ == "StudyGroup":
                member_list = instance.member_ids
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info("Instance is of type StudyGroup")

            if user_id in member_list:
                logger.info(f"User {interaction.user.display_name} is a member of {class_name} with name: {session_name}")
                return await func(instance, interaction, *args, **kwargs)
            else:
                logger.warning(f"User {interaction.user.display_name} is not a member of {class_name} with name: {session_name}")
                await interaction.response.send_message(f"You are not a member of this {class_name} with name: {session_name}.", ephemeral=True)
        return wrapper


    # Decorator to check if user is the owner
    @staticmethod
    def is_owner(func: Callable[..., Any]) -> Callable[..., Any]:
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
                logger.info("Instance is of type CheckinSession")

            # Check for StudyGroup
            if instance.__class__.__name__ == "StudyGroup":
                owner_id = instance.owner_id
                class_name = type(instance).__name__
                session_name = instance.name
                logger.info("Instance is of type StudyGroup")

            if user_id == owner_id:
                logger.info(f"User {interaction.user.display_name} is a the owner of {class_name} with name: {session_name}")
                return await func(instance, interaction, *args, **kwargs)
            else:
                logger.warning(f"User {interaction.user.display_name} is not the owner of {class_name} with name: {session_name}")
                await interaction.response.send_message(f"You are not the owner of this {class_name} with name: {session_name}.", ephemeral=True)
        return wrapper


    ## Check the max sessions / groups of a user
    ## Expand as neeeded for other group / modules
    @staticmethod
    def check_user_groups(func: Callable[..., Any]) -> Callable[..., Any]:
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
                logger.info("Instance is of type CheckinCog")
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
                logger.info("Instance is of type StudyGroupCog")
                study_group_count = sum(user_id in study_group.member_ids for study_group in cog_instance.active_study_groups.values())
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



    async def get_permission_level(self, guild_id: Optional[int], user_id: int, member: Optional[discord.Member] = None) -> PermissionLevel:
        if user_id == self.bot.bot_developer_id:
            logger.debug(f"User {user_id} identified as bot developer")
            return PermissionLevel.BOT_DEVELOPER

        guild = self.bot.get_guild(guild_id) if guild_id else None
        if not member and guild:
            member = guild.get_member(user_id)

        if member and member.guild and member.guild.owner_id == user_id:
            logger.debug(f"User {user_id} identified as server owner (Admin)")
            return PermissionLevel.ADMIN
        elif guild and guild.owner_id == user_id:
            logger.debug(f"User {user_id} identified as server owner (Admin)")
            return PermissionLevel.ADMIN

        if member:
            perms = member.guild_permissions
            if perms.administrator:
                logger.debug(f"User {user_id} identified as admin via administrator permission")
                return PermissionLevel.ADMIN
            if perms.manage_guild or perms.manage_channels or perms.manage_roles or perms.moderate_members or perms.kick_members or perms.ban_members:
                logger.debug(f"User {user_id} identified as moderator via permissions")
                return PermissionLevel.MODERATOR
            mod_keywords = {'admin', 'administrator', 'mod', 'moderator', 'manager', 'lead', 'staff'}
            if any(any(kw in r.name.lower() for kw in mod_keywords) for r in member.roles):
                logger.debug(f"User {user_id} identified as moderator via role name")
                return PermissionLevel.MODERATOR

        manager = await self.bot.db.get_manager(user_id, guild_id)
        if manager:
            permission_level = manager['permission_level']
            logger.debug(f"User {user_id} has permission level {permission_level}")
            try:
                return PermissionLevel(permission_level)
            except ValueError:
                return PermissionLevel.REGULAR_USER
        logger.debug(f"User {user_id} has regular user permissions")
        return PermissionLevel.REGULAR_USER

    async def sync_guild_managers(self, guild: discord.Guild) -> List[discord.Member]:
        """Auto-detect server owner, administrators, and moderators, registering them into the database."""
        synced_members: List[discord.Member] = []
        try:
            owner = guild.owner
            if not owner and guild.owner_id:
                try:
                    owner = await guild.fetch_member(guild.owner_id)
                except Exception:
                    owner = guild.get_member(guild.owner_id)

            if owner:
                await self.bot.db.add_manager(owner.id, guild.id, PermissionLevel.ADMIN)
                synced_members.append(owner)
                logger.info(f"Auto-synced server owner {owner.display_name} ({owner.id}) as ADMIN for guild {guild.id}")

            mod_keywords = {'admin', 'administrator', 'mod', 'moderator', 'manager', 'lead', 'staff'}
            for member in guild.members:
                if member.bot or (owner and member.id == owner.id):
                    continue
                perms = member.guild_permissions
                if perms.administrator:
                    await self.bot.db.add_manager(member.id, guild.id, PermissionLevel.ADMIN)
                    synced_members.append(member)
                    logger.info(f"Auto-synced administrator {member.display_name} ({member.id}) as ADMIN for guild {guild.id}")
                elif (
                    perms.manage_guild or
                    perms.manage_channels or
                    perms.manage_roles or
                    perms.moderate_members or
                    perms.kick_members or
                    perms.ban_members or
                    any(any(kw in r.name.lower() for kw in mod_keywords) for r in member.roles)
                ):
                    await self.bot.db.add_manager(member.id, guild.id, PermissionLevel.MODERATOR)
                    synced_members.append(member)
                    logger.info(f"Auto-synced moderator {member.display_name} ({member.id}) as MODERATOR for guild {guild.id}")

        except Exception as e:
            logger.error(f"Error in sync_guild_managers for guild {guild.id}: {e}")

        return synced_members

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                await self.sync_guild_managers(guild)
            except Exception as e:
                logger.warning(f"Could not sync managers for guild {guild.id}: {e}")

    @app_commands.command(name="sync_commands", description="Synchronize application slash commands with Discord (Admin only)")
    @app_commands.describe(guild_only="If true, syncs only to this server. If false, syncs globally.")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction, guild_only: bool = False):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild and guild_only:
            await interaction.followup.send("Guild-only sync can only be used inside a server.", ephemeral=True)
            return

        level = await self.get_permission_level(interaction.guild_id, interaction.user.id, member=interaction.user if isinstance(interaction.user, discord.Member) else None)
        if level < PermissionLevel.ADMIN:
            await interaction.followup.send("You must be an Administrator or Bot Developer to sync commands.", ephemeral=True)
            return

        try:
            if guild_only and interaction.guild:
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(f"Successfully synced **{len(synced)}** command(s) to server **{interaction.guild.name}**.", ephemeral=True)
            else:
                synced = await self.bot.tree.sync()
                await interaction.followup.send(f"Successfully synced **{len(synced)}** command(s) globally across all servers.", ephemeral=True)
            logger.info(f"Slash commands synced by {interaction.user.display_name} (guild_only={guild_only})")
        except Exception as e:
            logger.exception(f"Error syncing commands: {e}")
            await interaction.followup.send(f"Failed to sync commands: {e}", ephemeral=True)

    @app_commands.command(name="user_level", description="Check the authorization level (User, Mod, Admin) of a server member")
    @app_commands.describe(user="The member to inspect (defaults to yourself)")
    async def user_level(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target_member = user or (interaction.user if isinstance(interaction.user, discord.Member) else None)
        if not target_member:
            await interaction.response.send_message("Could not identify the target member.", ephemeral=True)
            return

        level = await self.get_permission_level(interaction.guild_id, target_member.id, member=target_member)
        tier = self.get_tier_name(level)

        level_labels = {
            PermissionLevel.BOT_DEVELOPER: "Bot Developer (Superuser)",
            PermissionLevel.ADMIN: "Administrator (Admin)",
            PermissionLevel.MODERATOR: "Moderator (Mod)",
            PermissionLevel.GROUP_MEMBER: "Group Member",
            PermissionLevel.REGULAR_USER: "Regular User",
        }

        color = discord.Color.gold() if tier == "Admin" else (discord.Color.blue() if tier == "Mod" else discord.Color.green())
        embed = discord.Embed(title=f"User Authorization Level: {target_member.display_name}", color=color)
        embed.add_field(name="User Level Tier", value=f"🛡️ **{tier}**", inline=True)
        embed.add_field(name="Permission Level", value=f"{level_labels.get(level, str(level))} (Level {int(level)})", inline=True)
        embed.set_footer(text=f"User ID: {target_member.id}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="sync_managers", description="Automatically detect server owner and moderators and grant manager roles (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def sync_managers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        level = await self.get_permission_level(interaction.guild_id, interaction.user.id, member=interaction.user if isinstance(interaction.user, discord.Member) else None)
        if level < PermissionLevel.ADMIN:
            await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
            return

        synced = await self.sync_guild_managers(interaction.guild)
        names = ", ".join(m.display_name for m in synced[:15])
        if len(synced) > 15:
            names += f" and {len(synced) - 15} others"

        await interaction.followup.send(
            f"Successfully synced **{len(synced)}** server owner & moderator members in the database:\n{names or 'None detected'}",
            ephemeral=True
        )

    @app_commands.command(name="add_bot_developer", description="Add a bot developer (Bot Developer only)")
    @app_commands.describe(user="The user to add as a bot developer")
    @app_commands.default_permissions(administrator=True)
    async def add_bot_developer(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to add bot developer: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to add bot developer without permission")
            if interaction.response.is_done():
                await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.add_manager(user.id, None, PermissionLevel.BOT_DEVELOPER)
        logger.info(f"Added {user.id} as bot developer")
        if interaction.response.is_done():
            await interaction.followup.send(f"{user.name} has been added as a bot developer.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.name} has been added as a bot developer.", ephemeral=True)

    @app_commands.command(name="add_guild_manager", description="Add a guild manager (Admin only)")
    @app_commands.describe(user="The user to add as a guild manager")
    @app_commands.default_permissions(administrator=True)
    async def add_guild_manager(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to add guild manager: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) < PermissionLevel.ADMIN:
            logger.warning(f"User {interaction.user.id} attempted to add guild manager without permission")
            if interaction.response.is_done():
                await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.add_manager(user.id, interaction.guild_id, PermissionLevel.ADMIN)
        logger.info(f"Added {user.id} as guild manager for guild {interaction.guild_id}")
        if interaction.response.is_done():
            await interaction.followup.send(f"{user.name} has been added as a guild manager for this server.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.name} has been added as a guild manager for this server.", ephemeral=True)

    @app_commands.command(name="remove_guild_manager", description="Remove a guild manager (Admin only)")
    @app_commands.describe(user="The user to remove as a guild manager")
    @app_commands.default_permissions(administrator=True)
    async def remove_guild_manager(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to remove guild manager: {user.id} by user: {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) < PermissionLevel.ADMIN:
            logger.warning(f"User {interaction.user.id} attempted to remove guild manager without permission")
            if interaction.response.is_done():
                await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await self.bot.db.remove_manager(user.id, interaction.guild_id)
        logger.info(f"Removed {user.id} as guild manager for guild {interaction.guild_id}")
        if interaction.response.is_done():
            await interaction.followup.send(f"{user.name} has been removed as a guild manager for this server.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.name} has been removed as a guild manager for this server.", ephemeral=True)

    @app_commands.command(name="list_managers", description="List all managers and staff for this server")
    @app_commands.default_permissions(manage_guild=True)
    async def list_managers(self, interaction: discord.Interaction):
        logger.info(f"Listing managers for guild {interaction.guild_id}")
        managers = await self.bot.db.get_all_managers(interaction.guild_id)

        embed = discord.Embed(title="Server Staff & Managers", color=discord.Color.blue())
        for manager in managers:
            uid = manager['user_id']
            user = self.bot.get_user(uid)
            if not user:
                try:
                    user = await self.bot.fetch_user(uid)
                except Exception:
                    user = None
            user_label = user.name if user else f"User {uid}"
            perm_lvl = manager['permission_level']
            if manager['guild_id'] is None or perm_lvl >= PermissionLevel.BOT_DEVELOPER:
                level_str = "Bot Developer (Superuser)"
            elif perm_lvl >= PermissionLevel.ADMIN:
                level_str = "Administrator (Admin)"
            elif perm_lvl >= PermissionLevel.MODERATOR:
                level_str = "Moderator (Mod)"
            else:
                level_str = f"Level {perm_lvl}"
            embed.add_field(name=user_label, value=level_str, inline=False)

        logger.debug(f"Found {len(managers)} managers for guild {interaction.guild_id}")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_permission_level", description="Set the permission level for a user (Bot Developer only)")
    @app_commands.describe(
        user="The user to set permissions for",
        level="The permission level to set (0: Regular User, 1: Member, 2: Moderator, 3: Admin, 4: Bot Developer)"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_permission_level(self, interaction: discord.Interaction, user: discord.User, level: int):
        logger.info(f"Attempt to set permission level for user {user.id} to level {level} by user {interaction.user.id}")
        if await self.get_permission_level(interaction.guild_id, interaction.user.id) != PermissionLevel.BOT_DEVELOPER:
            logger.warning(f"User {interaction.user.id} attempted to set permission level without being a Bot Developer")
            if interaction.response.is_done():
                await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if level not in [0, 1, 2, 3, 4]:
            logger.warning(f"Invalid permission level {level} specified")
            if interaction.response.is_done():
                await interaction.followup.send("Invalid permission level. Please use 0 (User), 1 (Member), 2 (Mod), 3 (Admin), or 4 (Dev).", ephemeral=True)
            else:
                await interaction.response.send_message("Invalid permission level. Please use 0 (User), 1 (Member), 2 (Mod), 3 (Admin), or 4 (Dev).", ephemeral=True)
            return

        if level == PermissionLevel.REGULAR_USER:
            await self.bot.db.remove_manager(user.id, interaction.guild_id)
            logger.info(f"Removed all permissions for user {user.id}")
        else:
            guild_id = None if level == PermissionLevel.BOT_DEVELOPER else interaction.guild_id
            await self.bot.db.add_manager(user.id, guild_id, level)
            logger.info(f"Set permission level {level} for user {user.id} in guild {guild_id}")

        permission_names = {
            PermissionLevel.REGULAR_USER: "Regular User (User)",
            PermissionLevel.GROUP_MEMBER: "Group Member (User)",
            PermissionLevel.MODERATOR: "Moderator (Mod)",
            PermissionLevel.ADMIN: "Administrator (Admin)",
            PermissionLevel.BOT_DEVELOPER: "Bot Developer (Superuser)",
        }
        name_str = permission_names.get(PermissionLevel(level), str(level))
        if interaction.response.is_done():
            await interaction.followup.send(f"Set {user.name}'s permission level to {name_str}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Set {user.name}'s permission level to {name_str}.", ephemeral=True)

async def setup(bot):

    await bot.add_cog(Manager(bot))
    logger.info("Manager cog loaded")


