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
        # 1. Check if the user is a bot developer
        if user_id == self.bot.bot_developer_id:
            return True

        # 2. Check user-specific permissions
        user_permissions = await self.bot.db.fetch_user_permissions(user_id, guild_id)
        if user_permissions and permission in user_permissions.permissions:
            return True

        # 3. Check role-based permissions
        guild = self.bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member:
                for role in member.roles:
                    role_permissions = await self.bot.db.fetch_role_permissions(role.id, guild_id)
                    if role_permissions and permission in role_permissions.permissions:
                        return True

        return False

    @app_commands.command(name="grant_permission", description="Grant a permission to a user or role (Bot Developer only)")
    @app_commands.describe(entity="The user or role to grant the permission to", permission="The permission to grant")
    async def grant_permission(self, interaction: discord.Interaction, entity: discord.Object, permission: str):
        logger.info(f"Attempt to grant permission '{permission}' to {entity.id} by user {interaction.user.id}")

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

        if isinstance(entity, discord.User):
            # Grant permission to user
            user_permissions = await self.bot.db.fetch_user_permissions(entity.id, interaction.guild_id)
            if not user_permissions:
                user_permissions = UserPermissions(user_id=entity.id, guild_id=interaction.guild_id, permissions=[])

            if permission not in user_permissions.permissions:
                user_permissions.permissions.append(permission)
                if user_permissions._id is None:
                    await self.bot.db.add_user_permissions(user_permissions)
                else:
                    await self.bot.db.update_user_permissions(entity.id, interaction.guild_id, user_permissions.permissions)
                logger.info(f"Granted permission '{permission}' to user {entity.id} in guild {interaction.guild_id}")
                await interaction.response.send_message(f"Granted permission '{permission}' to {entity.name}.", ephemeral=True)
            else:
                logger.info(f"User {entity.id} already has permission '{permission}' in guild {interaction.guild_id}")
                await interaction.response.send_message(f"{entity.name} already has permission '{permission}'.", ephemeral=True)

        elif isinstance(entity, discord.Role):
            # Grant permission to role
            role_permissions = await self.bot.db.fetch_role_permissions(entity.id, interaction.guild_id)
            if not role_permissions:
                role_permissions = UserPermissions(user_id=None, guild_id=interaction.guild_id, permissions=[], role_id=entity.id)

            if permission not in role_permissions.permissions:
                role_permissions.permissions.append(permission)
                if role_permissions._id is None:
                    await self.bot.db.add_role_permissions(role_permissions)
                else:
                    await self.bot.db.update_role_permissions(entity.id, interaction.guild_id, role_permissions.permissions)
                logger.info(f"Granted permission '{permission}' to role {entity.id} in guild {interaction.guild_id}")
                await interaction.response.send_message(f"Granted permission '{permission}' to role {entity.name}.", ephemeral=True)
            else:
                logger.info(f"Role {entity.id} already has permission '{permission}' in guild {interaction.guild_id}")
                await interaction.response.send_message(f"Role {entity.name} already has permission '{permission}'.", ephemeral=True)

        else:
            await interaction.response.send_message("Invalid entity. Please specify a user or a role.", ephemeral=True)

    @app_commands.command(name="revoke_permission", description="Revoke a permission from a user or role (Bot Developer only)")
    @app_commands.describe(entity="The user or role to revoke the permission from", permission="The permission to revoke")
    async def revoke_permission(self, interaction: discord.Interaction, entity: discord.Object, permission: str):
        logger.info(f"Attempt to revoke permission '{permission}' from {entity.id} by user {interaction.user.id}")

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

        if isinstance(entity, discord.User):
            # Revoke permission from user
            user_permissions = await self.bot.db.fetch_user_permissions(entity.id, interaction.guild_id)
            if user_permissions:
                if permission in user_permissions.permissions:
                    user_permissions.permissions.remove(permission)
                    await self.bot.db.update_user_permissions(entity.id, interaction.guild_id, user_permissions.permissions)
                    logger.info(f"Revoked permission '{permission}' from user {entity.id} in guild {interaction.guild_id}")
                    await interaction.response.send_message(f"Revoked permission '{permission}' from {entity.name}.", ephemeral=True)
                else:
                    logger.info(f"User {entity.id} does not have permission '{permission}' in guild {interaction.guild_id}")
                    await interaction.response.send_message(f"{entity.name} does not have permission '{permission}'.", ephemeral=True)
            else:
                logger.info(f"User {entity.id} has no permissions in guild {interaction.guild_id}")
                await interaction.response.send_message(f"{entity.name} has no permissions in this guild.", ephemeral=True)

        elif isinstance(entity, discord.Role):
            # Revoke permission from role
            role_permissions = await self.bot.db.fetch_role_permissions(entity.id, interaction.guild_id)
            if role_permissions:
                if permission in role_permissions.permissions:
                    role_permissions.permissions.remove(permission)
                    await self.bot.db.update_role_permissions(entity.id, interaction.guild_id, role_permissions.permissions)
                    logger.info(f"Revoked permission '{permission}' from role {entity.id} in guild {interaction.guild_id}")
                    await interaction.response.send_message(f"Revoked permission '{permission}' from role {entity.name}.", ephemeral=True)
                else:
                    logger.info(f"Role {entity.id} does not have permission '{permission}' in guild {interaction.guild_id}")
                    await interaction.response.send_message(f"Role {entity.name} does not have permission '{permission}'.", ephemeral=True)
            else:
                logger.info(f"Role {entity.id} has no permissions in guild {interaction.guild_id}")
                await interaction.response.send_message(f"Role {entity.name} has no permissions in this guild.", ephemeral=True)

        else:
            await interaction.response.send_message("Invalid entity. Please specify a user or a role.", ephemeral=True)

    @app_commands.command(name="list_permissions", description="List all permissions granted to a user or role")
    @app_commands.describe(entity="The user or role to list permissions for")
    async def list_permissions(self, interaction: discord.Interaction, entity: discord.Object):
        logger.info(f"Attempt to list permissions for {entity.id} by user {interaction.user.id}")

        if isinstance(entity, discord.User):
            user_permissions = await self.bot.db.fetch_user_permissions(entity.id, interaction.guild_id)
            if user_permissions and user_permissions.permissions:
                permissions_list = "\n".join(user_permissions.permissions)
                await interaction.response.send_message(f"Permissions for {entity.name}:\n{permissions_list}", ephemeral=True)
            else:
                await interaction.response.send_message(f"{entity.name} has no permissions in this guild.", ephemeral=True)

        elif isinstance(entity, discord.Role):
            role_permissions = await self.bot.db.fetch_role_permissions(entity.id, interaction.guild_id)
            if role_permissions and role_permissions.permissions:
                permissions_list = "\n".join(role_permissions.permissions)
                await interaction.response.send_message(f"Permissions for role {entity.name}:\n{permissions_list}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Role {entity.name} has no permissions in this guild.", ephemeral=True)

        else:
            await interaction.response.send_message("Invalid entity. Please specify a user or a role.", ephemeral=True)

    @app_commands.command(name="list_users_with_permission", description="List all users with a specific permission in this server")
    @app_commands.describe(permission="The permission to list users for")
    async def list_users_with_permission(self, interaction: discord.Interaction, permission: str):
        logger.info(f"Listing users with permission '{permission}' for guild {interaction.guild_id}")

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

        # Fetch all users with the specified permission
        users_with_permission = []
        async for user_permissions in self.bot.db.db['user_permissions'].find({'guild_id': interaction.guild_id, 'permissions': permission}):
            user = await self.bot.fetch_user(user_permissions['user_id'])
            users_with_permission.append(user)

        # Create and send the embed
        embed = discord.Embed(title=f"Users with Permission: {permission}", color=discord.Color.blue())
        if users_with_permission:
            for user in users_with_permission:
                embed.add_field(name=f"{user.name}#{user.discriminator}", value=user.id, inline=False)
        else:
            embed.description = "No users found with this permission."

        logger.debug(f"Found {len(users_with_permission)} users with permission '{permission}' for guild {interaction.guild_id}")
        await interaction.response.send_message(embed=embed)

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
