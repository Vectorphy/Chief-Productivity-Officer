import discord
from discord import app_commands
from discord.ext import commands
import logging

from .models import UserPermissions

logger = logging.getLogger(__name__)

class Heimdall(commands.Cog):
    """Manages user permissions and bot settings."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("Heimdall cog initialized")

    async def has_permission(self, user_id: int, guild_id: int, permission: str) -> bool:
        """Checks if a user has a specific permission in a guild."""
        user_permissions = await self.bot.db.fetch_user_permissions(user_id, guild_id)
        if user_permissions:
            return permission in user_permissions.permissions
        return False

    @app_commands.command(name="grant_permission", description="Grant a permission to a user (Bot Developer only)")
    @app_commands.describe(user="The user to grant the permission to", permission="The permission to grant")
    async def grant_permission(self, interaction: discord.Interaction, user: discord.User, permission: str):
        logger.info(f"Attempt to grant permission '{permission}' to user {user.id} by user {interaction.user.id}")

        # Check if the command invoker is a bot developer
        if not await self.has_permission(interaction.user.id, interaction.guild_id, "modify_bot_settings"):
            logger.warning(f"User {interaction.user.id} attempted to grant permission without being a Bot Developer")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        # Check if the permission is valid
        valid_permissions = [
            "create_space", "manage_space", "end_space", 
            "start_checkin", "manage_checkin", 
            "manage_pomodoro", "manage_tasks", 
            "manage_voice_channels", "modify_bot_settings"
        ]
        if permission not in valid_permissions:
            logger.warning(f"Invalid permission '{permission}' specified")
            await interaction.response.send_message(f"Invalid permission. Valid permissions are: {', '.join(valid_permissions)}", ephemeral=True)
            return

        # Get existing user permissions or create a new UserPermissions object
        user_permissions = await self.bot.db.fetch_user_permissions(user.id, interaction.guild_id)
        if not user_permissions:
            user_permissions = UserPermissions(user_id=user.id, guild_id=interaction.guild_id, permissions=[])

        # Add the permission if it's not already granted
        if permission not in user_permissions.permissions:
            user_permissions.permissions.append(permission)
            if user_permissions._id is None:
                await self.bot.db.add_user_permissions(user_permissions)
            else:
                await self.bot.db.update_user_permissions(user.id, interaction.guild_id, user_permissions.permissions)
            logger.info(f"Granted permission '{permission}' to user {user.id} in guild {interaction.guild_id}")
            await interaction.response.send_message(f"Granted permission '{permission}' to {user.name}.", ephemeral=True)
        else:
            logger.info(f"User {user.id} already has permission '{permission}' in guild {interaction.guild_id}")
            await interaction.response.send_message(f"{user.name} already has permission '{permission}'.", ephemeral=True)

    # Revoke a specific permission from a user in a guild.
    @app_commands.command(name="revoke_permission", description="Revoke a permission from a user (Bot Developer only)")
    @app_commands.describe(user="The user to revoke the permission from", permission="The permission to revoke")
    async def revoke_permission(self, interaction: discord.Interaction, user: discord.User, permission: str):
        logger.info(f"Attempt to revoke permission '{permission}' from user {user.id} by user {interaction.user.id}")

        # Check if the command invoker is a bot developer
        if not await self.has_permission(interaction.user.id, interaction.guild_id, "modify_bot_settings"):
            logger.warning(f"User {interaction.user.id} attempted to revoke permission without being a Bot Developer")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        # Check if the permission is valid
        valid_permissions = [
            "create_space", "manage_space", "end_space", 
            "start_checkin", "manage_checkin", 
            "manage_pomodoro", "manage_tasks", 
            "manage_voice_channels", "modify_bot_settings"
        ]
        if permission not in valid_permissions:
            logger.warning(f"Invalid permission '{permission}' specified")
            await interaction.response.send_message(f"Invalid permission. Valid permissions are: {', '.join(valid_permissions)}", ephemeral=True)
            return

        # Get existing user permissions
        user_permissions = await self.bot.db.fetch_user_permissions(user.id, interaction.guild_id)
        if user_permissions:
            # Remove the permission if it's granted
            if permission in user_permissions.permissions:
                user_permissions.permissions.remove(permission)
                await self.bot.db.update_user_permissions(user.id, interaction.guild_id, user_permissions.permissions)
                logger.info(f"Revoked permission '{permission}' from user {user.id} in guild {interaction.guild_id}")
                await interaction.response.send_message(f"Revoked permission '{permission}' from {user.name}.", ephemeral=True)
            else:
                logger.info(f"User {user.id} does not have permission '{permission}' in guild {interaction.guild_id}")
                await interaction.response.send_message(f"{user.name} does not have permission '{permission}'.", ephemeral=True)
        else:
            logger.info(f"User {user.id} has no permissions in guild {interaction.guild_id}")
            await interaction.response.send_message(f"{user.name} has no permissions in this guild.", ephemeral=True)

    # List all permissions granted to a user in a guild.
    @app_commands.command(name="list_permissions", description="List all permissions granted to a user")
    @app_commands.describe(user="The user to list permissions for")
    async def list_permissions(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to list permissions for user {user.id} by user {interaction.user.id}")

        user_permissions = await self.bot.db.fetch_user_permissions(user.id, interaction.guild_id)
        if user_permissions and user_permissions.permissions:
            permissions_list = "\n".join(user_permissions.permissions)
            await interaction.response.send_message(f"Permissions for {user.name}:\n{permissions_list}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.name} has no permissions in this guild.", ephemeral=True)

    # Get the permission level of a user in a guild. Debug feature.
    @app_commands.command(name="get_permission_level", description="Get the permission level of a user (Bot Developer only)")
    @app_commands.describe(user="The user to get the permission level for")
    async def get_permission_level(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"Attempt to get permission level for user {user.id} by user {interaction.user.id}")

        # Check if the command invoker is a bot developer
        if not await self.has_permission(interaction.user.id, interaction.guild_id, "modify_bot_settings"):
            logger.warning(f"User {interaction.user.id} attempted to get permission level without being a Bot Developer")
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if user.id == self.bot.bot_developer_id:
            permission_level = "Bot Developer"
        else:
            user_permissions = await self.bot.db.fetch_user_permissions(user.id, interaction.guild_id)
            if user_permissions and "modify_bot_settings" in user_permissions.permissions:
                permission_level = "Bot Developer"
            elif user_permissions and any(perm in user_permissions.permissions for perm in ["create_space", "manage_space", "end_space"]):
                permission_level = "Space Manager"
            else:
                permission_level = "Regular User"

        await interaction.response.send_message(f"Permission level for {user.name}: {permission_level}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Heimdall(bot))
    logger.info("Heimdall cog loaded")
