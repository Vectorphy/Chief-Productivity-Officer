import discord

from discord import app_commands
from discord.ext import commands
from utils import app_is_manager, is_group_creator
import logging
import database

# Set up logging for this module
logger = logging.getLogger(__name__)

class VoiceChannels(commands.Cog):
    """
    A cog for managing voice channels, roles, and text channels associated with study groups.

    This cog provides commands to create and delete voice channels, roles, and text channels,
    and automatically manages voice channels by deleting empty ones.
    """
    def __init__(self, bot: commands.Bot, db: database.DBHandler):
        """Initializes the VoiceChannels cog.
        """
        self.bot: commands.Bot = bot
        self.db: database.DBHandler = db
        logger.info("VoiceChannels cog initialized.")

    @app_commands.command(name="create_vc", description="Create a voice channel for the study group")
    @app_commands.describe(name="Name of the voice channel (optional)")
    @is_group_creator()
    @app_is_manager()
    async def create_vc(self, interaction: discord.Interaction, name: str = None):
        logger.info(f"create_vc command invoked by {interaction.user}")
        group = await self.bot.db.fetch_study_group_by_id(interaction.guild_id)
        if not group:
            logger.warning(f"No study group exists in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists in this server.", ephemeral=True)
            return

        if group[8]:  # Assuming voice_channel_id is at index 8
            logger.warning(f"Voice channel already exists for group {group[0]}")
            await interaction.response.send_message("A voice channel already exists for this group.", ephemeral=True)
            return

        channel_name = name or f"{group[1]} VC"
        logger.debug(f"Creating voice channel '{channel_name}'")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
            interaction.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
        }

        _, session_role_id = await self.bot.db.get_group_roles(group[0])
        session_role = interaction.guild.get_role(session_role_id)
        if session_role:
            overwrites[session_role] = discord.PermissionOverwrite(connect=True)
            logger.debug(f"Added connect permission for role {session_role.name}")

        try:
            channel = await interaction.guild.create_voice_channel(channel_name, overwrites=overwrites)
            await self.bot.db.update_voice_channel(group[0], channel.id)
            logger.info(f"Voice channel {channel.id} created for group {group[0]}")
            await interaction.response.send_message(f"Voice channel {channel.mention} created for the study group.")
        except discord.HTTPException as e:
            logger.error(f"Failed to create voice channel: {str(e)}")
            await interaction.response.send_message("Failed to create the voice channel. Please try again later.", ephemeral=True)

    @app_commands.command(name="delete_vc", description="Delete the selected VC from the Server")
    @app_commands.describe(voice_channel="Select the VC to delete")
    @is_group_creator()
    @app_is_manager()
    async def delete_vc(self, interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
        logger.info(f"delete_vc command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        if voice_channel.id != group[8]:  # Assuming voice_channel_id is at index 8
            logger.warning(f"Voice channel {voice_channel.id} is not associated with the study group {group[0]}")
            await interaction.response.send_message("This voice channel is not associated with the current study group.", ephemeral=True)
            return

        try:
            await voice_channel.delete(reason="Voice channel deleted by group creator")
            await self.bot.db.update_voice_channel(group[0], None)
            logger.info(f"Voice channel {voice_channel.id} deleted for group {group[0]}")
            await interaction.response.send_message("Voice channel deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete voice channel {voice_channel.id}: {str(e)}")
            await interaction.response.send_message("Failed to delete the voice channel. Please try again later.", ephemeral=True)

    @app_commands.command(name="delete_role", description="Delete the selected role for the study group")
    @app_commands.describe(role="Select the Role to delete")
    @is_group_creator()
    @app_is_manager()
    async def delete_role(self, interaction: discord.Interaction, role: discord.Role):
        logger.info(f"delete_role command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        if role.id != group[6]:  # Assuming group_role_id is at index 6
            logger.warning(f"Role {role.id} is not associated with the study group {group[0]}")
            await interaction.response.send_message("This role is not associated with the current study group.", ephemeral=True)
            return

        try:
            await role.delete(reason="Role deleted by group creator")
            await self.bot.db.update_group_roles(group[0], None, group[7])
            logger.info(f"Role {role.id} deleted for group {group[0]}")
            await interaction.response.send_message("Role deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete role {role.id}: {str(e)}")
            await interaction.response.send_message("Failed to delete the role. Please try again later.", ephemeral=True)


    @app_commands.command(name="delete_text_channel", description="Delete the selected text channel for the study group")
    @app_commands.describe(text_channel="Select the Text Channel to delete")
    @is_group_creator()
    @app_is_manager()
    async def delete_text_channel(self, interaction: discord.Interaction, text_channel: discord.TextChannel):
        logger.info(f"delete_text_channel command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        if text_channel.id != group[7]:  # Assuming text_channel_id is at index 7
            logger.warning(f"Text channel {text_channel.id} is not associated with the study group {group[0]}")
            await interaction.response.send_message("This text channel is not associated with the current study group.", ephemeral=True)
            return

        try:
            await text_channel.delete(reason="Text channel deleted by group creator")
            await self.bot.db.update_voice_channel(group[0], None)
            logger.info(f"Text channel {text_channel.id} deleted for group {group[0]}")
            await interaction.response.send_message("Text channel deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete text channel {text_channel.id}: {str(e)}")
            await interaction.response.send_message("Failed to delete the text channel. Please try again later.", ephemeral=True)





    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        logger.debug(f"Voice state update: {member} moved from {before.channel} to {after.channel}")
        if before.channel and not after.channel:
            group = await self.bot.db.fetch_study_group_by_id(before.channel.guild.id)
            if group and group[8] == before.channel.id:
                logger.debug(f"Member {member} left study group voice channel {before.channel.id}")
                if not before.channel.members:
                    try:
                        await before.channel.delete()
                        await self.bot.db.update_voice_channel(group[0], None)
                        logger.info(f"Deleted empty voice channel {before.channel.id} for group {group[0]}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to delete empty voice channel: {str(e)}")

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))
    logger.info("VoiceChannels cog loaded")
