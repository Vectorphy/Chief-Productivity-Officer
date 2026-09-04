import logging
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils import app_is_manager, is_group_creator

logger = logging.getLogger(__name__)

class VoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("VoiceChannels cog initialized")

    @app_commands.command(name="create_vc", description="Create a voice channel for the study group")
    @app_commands.describe(name="Name of the voice channel (optional)")
    @is_group_creator()
    async def create_vc(self, interaction: discord.Interaction, name: Optional[str] = None):
        logger.info(f"create_vc command invoked by {interaction.user}")
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group exists in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists in this server.", ephemeral=True)
            return

        group_id = group['id'] if 'id' in group.keys() else group[0]
        group_vc_id = group['vc_id'] if 'vc_id' in group.keys() else group[9]
        group_name = group['name'] if 'name' in group.keys() else group[2]

        if group_vc_id:
            logger.warning(f"Voice channel already exists for group {group_id}")
            await interaction.response.send_message("A voice channel already exists for this group.", ephemeral=True)
            return

        channel_name = name or f"{group_name} VC"
        logger.debug(f"Creating voice channel '{channel_name}'")
        overwrites: dict[Union[discord.Role, discord.Member, discord.Object], discord.PermissionOverwrite] = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
            interaction.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
        }

        _, session_role_id = await self.bot.db.get_group_roles(group_id)
        session_role = interaction.guild.get_role(session_role_id) if session_role_id else None
        if session_role:
            overwrites[session_role] = discord.PermissionOverwrite(connect=True)
            logger.debug(f"Added connect permission for role {session_role.name}")

        try:
            channel = await interaction.guild.create_voice_channel(channel_name, overwrites=overwrites)
            await self.bot.db.update_voice_channel(group_id, channel.id)
            logger.info(f"Voice channel {channel.id} created for group {group_id}")
            if interaction.response.is_done():
                await interaction.followup.send(f"Voice channel {channel.mention} created for the study group.")
            else:
                await interaction.response.send_message(f"Voice channel {channel.mention} created for the study group.")
        except discord.HTTPException as e:
            logger.error(f"Failed to create voice channel: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send("Failed to create the voice channel. Please try again later.", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to create the voice channel. Please try again later.", ephemeral=True)

    @app_commands.command(name="delete_vc", description="Delete the selected VC from the Server")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(voice_channel="Select the VC to delete")
    @is_group_creator()
    async def delete_vc(self, interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        logger.info(f"delete_vc command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        group_id = group['id'] if 'id' in group.keys() else group[0]
        group_vc_id = group['vc_id'] if 'vc_id' in group.keys() else group[9]

        if voice_channel.id != group_vc_id:
            logger.warning(f"Voice channel {voice_channel.id} is not associated with the study group {group_id}")
            await interaction.response.send_message("This voice channel is not associated with the current study group.", ephemeral=True)
            return

        try:
            await voice_channel.delete(reason="Voice channel deleted by group creator")
            await self.bot.db.update_voice_channel(group_id, None)
            logger.info(f"Voice channel {voice_channel.id} deleted for group {group_id}")
            if interaction.response.is_done():
                await interaction.followup.send("Voice channel deleted successfully.", ephemeral=True)
            else:
                await interaction.response.send_message("Voice channel deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete voice channel {voice_channel.id}: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send("Failed to delete the voice channel. Please try again later.", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to delete the voice channel. Please try again later.", ephemeral=True)

    @app_commands.command(name="delete_role", description="Delete the selected role for the study group")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(role="Select the Role to delete")
    @is_group_creator()
    async def delete_role(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        logger.info(f"delete_role command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        group_id = group['id'] if 'id' in group.keys() else group[0]
        group_role_id = group['group_role_id'] if 'group_role_id' in group.keys() else group[8]

        if role.id != group_role_id:
            logger.warning(f"Role {role.id} is not associated with the study group {group_id}")
            await interaction.response.send_message("This role is not associated with the current study group.", ephemeral=True)
            return

        try:
            await role.delete(reason="Role deleted by group creator")
            await self.bot.db.update_group_roles(group_id, None, None)
            logger.info(f"Role {role.id} deleted for group {group_id}")
            if interaction.response.is_done():
                await interaction.followup.send("Role deleted successfully.", ephemeral=True)
            else:
                await interaction.response.send_message("Role deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete role {role.id}: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send("Failed to delete the role. Please try again later.", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to delete the role. Please try again later.", ephemeral=True)


    @app_commands.command(name="delete_text_channel", description="Delete the selected text channel for the study group")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(text_channel="Select the Text Channel to delete")
    @is_group_creator()
    async def delete_text_channel(self, interaction: discord.Interaction, text_channel: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        logger.info(f"delete_text_channel command invoked by {interaction.user.display_name} in guild {interaction.guild.name}")

        group = await self.bot.db.get_study_group(interaction.guild_id)
        if not group:
            logger.warning(f"No study group found in server {interaction.guild_id}")
            await interaction.response.send_message("No study group exists for this server.", ephemeral=True)
            return

        group_id = group['id'] if 'id' in group.keys() else group[0]
        group_text_id = group['text_id'] if 'text_id' in group.keys() else group[10]

        if text_channel.id != group_text_id:
            logger.warning(f"Text channel {text_channel.id} is not associated with the study group {group_id}")
            await interaction.response.send_message("This text channel is not associated with the current study group.", ephemeral=True)
            return

        try:
            await text_channel.delete(reason="Text channel deleted by group creator")
            if 'group_id' in group.keys():
                await self.bot.db.update_study_group_by_id({'group_id': group['group_id'], 'text_id': 0})
            logger.info(f"Text channel {text_channel.id} deleted for group {group_id}")
            if interaction.response.is_done():
                await interaction.followup.send("Text channel deleted successfully.", ephemeral=True)
            else:
                await interaction.response.send_message("Text channel deleted successfully.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to delete text channel {text_channel.id}: {str(e)}")
            if interaction.response.is_done():
                await interaction.followup.send("Failed to delete the text channel. Please try again later.", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to delete the text channel. Please try again later.", ephemeral=True)





    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        logger.debug(f"Voice state update: {member} moved from {before.channel} to {after.channel}")
        if before.channel and not after.channel:
            group = await self.bot.db.get_study_group(before.channel.guild.id)
            if group:
                group_id = group['id'] if 'id' in group.keys() else group[0]
                group_vc_id = group['vc_id'] if 'vc_id' in group.keys() else group[9]
                if group_vc_id == before.channel.id:
                    logger.debug(f"Member {member} left study group voice channel {before.channel.id}")
                    if not before.channel.members:
                        try:
                            await before.channel.delete()
                            await self.bot.db.update_voice_channel(group_id, None)
                            logger.info(f"Deleted empty voice channel {before.channel.id} for group {group_id}")
                        except discord.HTTPException as e:
                            logger.error(f"Failed to delete empty voice channel: {str(e)}")

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))
    logger.info("VoiceChannels cog loaded")
