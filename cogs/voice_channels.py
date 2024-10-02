import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import logging
import pymongo.errors

logger = logging.getLogger(__name__)

class VoiceChannelManager:
    """Manages voice channel creation, deletion, and permissions for study groups."""

    def __init__(self, bot, group_id):
        self.bot = bot
        self.group_id = group_id
        self.voice_channel_id = None  # Store the voice channel ID in memory

    async def get_voice_channel(self, interaction: discord.Interaction, name: str = None):
        """Gets or creates the voice channel for the study group."""
        try:
            if self.voice_channel_id:  # Check in-memory cache first
                channel = interaction.guild.get_channel(self.voice_channel_id)
                if channel:
                    return channel

            group = await self.bot.db.fetch_study_group_by_id(self.group_id)
            if not group:
                raise ValueError("No study group found.")

            self.voice_channel_id = group.get('vc_id')  # Update from database

            if self.voice_channel_id:  # Check if channel exists in database
                channel = interaction.guild.get_channel(self.voice_channel_id)
                if channel:
                    return channel

            # Create a new channel if not found in cache or database
            channel_name = name or f"{group['name']} VC"
            channel = await self._create_voice_channel(interaction, channel_name)
            self.voice_channel_id = channel.id  # Update in-memory cache
            await self.bot.db.update_study_group_by_id(
                {"group_id": self.group_id, "vc_id": channel.id}
            )  # Update database
            return channel

        except (discord.HTTPException, ValueError, pymongo.errors.PyMongoError) as e:
            logger.error(f"Error getting voice channel: {e}")
            await interaction.response.send_message(
                "Failed to get or create the voice channel. Please try again later.",
                ephemeral=True,
            )
            return None

    async def _create_voice_channel(self, interaction, channel_name):
        """Creates a new voice channel with appropriate permissions."""
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
            interaction.guild.me: discord.PermissionOverwrite(
                connect=True, manage_channels=True
            ),
        }

        _, session_role_id = await self.bot.db.get_group_roles(self.group_id)
        session_role = interaction.guild.get_role(session_role_id)
        if session_role:
            overwrites[session_role] = discord.PermissionOverwrite(connect=True)
            logger.debug(f"Added connect permission for role {session_role.name}")

        return await interaction.guild.create_voice_channel(
            channel_name, overwrites=overwrites
        )

    async def delete_voice_channel(self, interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
        """Deletes the voice channel associated with the study group."""
        try:
            if voice_channel.id != self.voice_channel_id:
                raise ValueError("This voice channel is not associated with the current study group.")

            await voice_channel.delete(reason="Voice channel deleted by group creator")
            self.voice_channel_id = None  # Update in-memory cache
            await self.bot.db.update_study_group_by_id(
                {"group_id": self.group_id, "vc_id": None}
            )  # Update database
            await interaction.response.send_message(
                "Voice channel deleted successfully.", ephemeral=True
            )

        except (discord.HTTPException, ValueError, pymongo.errors.PyMongoError) as e:
            logger.error(f"Error deleting voice channel: {e}")
            await interaction.response.send_message(
                "Failed to delete the voice channel. Please try again later.",
                ephemeral=True,
            )

class VoiceChannels(commands.Cog):
    """Cog for managing voice channels related to study groups."""

    def __init__(self, bot):
        self.bot = bot
        self.voice_channel_managers = {}  # Store managers by group ID
        logger.info("VoiceChannels cog initialized")

    async def get_voice_channel_manager(self, group_id: int) -> VoiceChannelManager:
        """Gets or creates a VoiceChannelManager for the given group ID."""
        if group_id not in self.voice_channel_managers:
            self.voice_channel_managers[group_id] = VoiceChannelManager(self.bot, group_id)
        return self.voice_channel_managers[group_id]

    @app_commands.command(name="create_vc", description="Create a voice channel for the study group")
    @app_commands.describe(name="Name of the voice channel (optional)")
    @is_group_creator()
    @app_is_manager()
    async def create_vc(self, interaction: discord.Interaction, name: str = None):
        """Creates a voice channel for the study group."""
        logger.info(f"create_vc command invoked by {interaction.user}")
        group = await self.bot.db.fetch_study_group_by_id(interaction.guild_id)
        if not group:
            logger.warning(f"No study group exists in server {interaction.guild_id}")
            await interaction.response.send_message(
                "No study group exists in this server.", ephemeral=True
            )
            return

        manager = await self.get_voice_channel_manager(group['id'])
        channel = await manager.get_voice_channel(interaction, name)
        if channel:
            await interaction.response.send_message(
                f"Voice channel {channel.mention} created for the study group."
            )

    @app_commands.command(name="delete_vc", description="Delete the selected VC from the Server")
    @app_commands.describe(voice_channel="Select the VC to delete")
    @is_group_creator()
    @app_is_manager()
    async def delete_vc(self, interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
        """Deletes the selected voice channel from the server."""
        logger.info(
            f"delete_vc command invoked by {interaction.user.display_name} in guild {interaction.guild.name}"
        )

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message(
                "No study group exists for this server.", ephemeral=True
            )
            return

        manager = await self.get_voice_channel_manager(group['id'])
        await manager.delete_voice_channel(interaction, voice_channel)

    # ... (delete_role, delete_text_channel commands - consider refactoring these similarly)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Automatically deletes empty study group voice channels."""
        logger.debug(
            f"Voice state update: {member} moved from {before.channel} to {after.channel}"
        )
        if before.channel and not after.channel:
            group = await self.bot.db.fetch_study_group_by_id(before.channel.guild.id)
            if group and group.get('vc_id') == before.channel.id:
                logger.debug(
                    f"Member {member} left study group voice channel {before.channel.id}"
                )
                if not before.channel.members:
                    try:
                        await before.channel.delete()
                        await self.bot.db.update_study_group_by_id(
                            {"group_id": group['id'], "vc_id": None}
                        )
                        logger.info(
                            f"Deleted empty voice channel {before.channel.id} for group {group['id']}"
                        )
                    except discord.HTTPException as e:
                        logger.error(f"Failed to delete empty voice channel: {str(e)}")

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))
    logger.info("VoiceChannels cog loaded")
