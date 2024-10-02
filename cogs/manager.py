import discord
from discord import app_commands
import logging
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    BOT_DEVELOPER = 4
    GUILD_MANAGER = 3
    GROUP_OWNER = 2
    GROUP_MEMBER = 1
    REGULAR_USER = 0

class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Manager cog initialized")

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

    async def is_group_creator(self, guild_id, user_id):
        group = await self.bot.db.get_study_group(guild_id)
        is_creator = group and group['creator_id'] == user_id
        logger.debug(f"Checked if user {user_id} is group creator for guild {guild_id}: {is_creator}")
        return is_creator

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
