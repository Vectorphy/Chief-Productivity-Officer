import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from utils import parse_seconds_to_hms, parse_duration, parse_mentions, is_manager, app_is_manager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StudyGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Study Group cog initialized")

    async def create_session_role(self, guild, session_name):
        role_name = f"In {session_name}"
        return await guild.create_role(name=role_name, mentionable=True)

    @app_commands.command(name="create_group", description="Create a new study group")
    @app_commands.describe(name="Name of the study group", max_size="Maximum number of members")
    @app_is_manager()
    async def create_group(self, interaction: discord.Interaction, name: str, max_size: int = 10):
        logger.info(f"create_group command invoked by {interaction.user.id} for group '{name}'")
        # Check if a group with the same name already exists
        existing_group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
        if existing_group:
            await interaction.response.send_message(f"A study group named '{name}' already exists in this server.", ephemeral=True)
            return

        end_time = asyncio.get_event_loop().time() + 43200  # 12 hours
        group_id = await self.bot.db.create_study_group(name, interaction.user.id, max_size, end_time, interaction.guild_id)
        await self.bot.db.add_group_member(group_id, interaction.user.id)

        # Create roles for the group
        admin_role = await interaction.guild.create_role(name=f"Study Group Admin: {name}")
        session_role = await self.create_session_role(interaction.guild, name)

        await interaction.user.add_roles(admin_role, session_role)

        await self.bot.db.update_group_roles(group_id, admin_role.id, session_role.id)

        await interaction.response.send_message(
            f"Study group '{name}' created! Use /join_group to join.\n"
            f"You've been assigned the roles {admin_role.mention} and {session_role.mention}."
        )

    @app_commands.command(name="join_group", description="Join an existing study group")
    @app_commands.describe(name="Name of the study group to join")
    async def join_group(self, interaction: discord.Interaction, name: str):
        group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
        if not group:
            await interaction.response.send_message(f"No study group named '{name}' exists in this server.", ephemeral=True)
            return

        members = await self.bot.db.get_group_members(group['id'])
        if len(members) >= group['max_size']:
            await interaction.response.send_message("This group is full.", ephemeral=True)
            return

        if interaction.user.id in members:
            await interaction.response.send_message("You're already in this study group.", ephemeral=True)
            return

        await self.bot.db.add_group_member(group['id'], interaction.user.id)

        _, session_role_id = await self.bot.db.get_group_roles(group['id'])
        session_role = interaction.guild.get_role(session_role_id)

        if session_role:
            await interaction.user.add_roles(session_role)

        await interaction.response.send_message(
            f"You've joined the study group '{name}'!\n"
            f"You've been assigned the role {session_role.mention}."
        )

    @app_commands.command(name="leave_group", description="Leave a study group")
    @app_commands.describe(name="Name of the study group to leave")
    async def leave_group(self, interaction: discord.Interaction, name: str):
        group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
        if not group:
            await interaction.response.send_message(f"No study group named '{name}' exists in this server.", ephemeral=True)
            return

        members = await self.bot.db.get_group_members(group['id'])
        if interaction.user.id not in members:
            await interaction.response.send_message(f"You're not in the study group '{name}'.", ephemeral=True)
            return

        await self.bot.db.remove_group_member(group['id'], interaction.user.id)

        admin_role_id, session_role_id = await self.bot.db.get_group_roles(group['id'])
        session_role = interaction.guild.get_role(session_role_id)

        if session_role:
            await interaction.user.remove_roles(session_role)

        await interaction.response.send_message(f"You've left the study group '{name}'.")

        updated_members = await self.bot.db.get_group_members(group['id'])
        if not updated_members:
            await self._end_group(interaction.guild_id, name)  # Use internal function
            await interaction.response.send_message(f"The study group '{name}' has been ended.")

    @app_commands.command(name="end_group", description="End a study group")
    @app_commands.describe(name="Name of the study group to end")
    @app_is_manager()
    async def end_group(self, interaction: discord.Interaction, name: str):
        group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
        if not group:
            await interaction.response.send_message(f"No study group named '{name}' exists in this server.", ephemeral=True)
            return

        # Check if the user invoking the command is the group creator or a manager
        if not (group['creator_id'] == interaction.user.id or await is_manager(self.bot, interaction.guild_id, interaction.user.id)):
            await interaction.response.send_message("You don't have permission to end this group.", ephemeral=True)
            return

        await self._end_group(interaction.guild_id, name)
        await interaction.response.send_message(f"The study group '{name}' has been ended.")

    async def _end_group(self, guild_id, name):  # Internal helper function
        group = await self.bot.db.get_study_group_by_name(guild_id, name)
        if group:
            admin_role_id, session_role_id = await self.bot.db.get_group_roles(group['id'])
            guild = self.bot.get_guild(guild_id)

            admin_role = guild.get_role(admin_role_id)
            session_role = guild.get_role(session_role_id)

            if admin_role:
                await asyncio.sleep(2)  # Add a 2-second delay
                await admin_role.delete()
            if session_role:
                await asyncio.sleep(2)  # Add a 2-second delay
                await session_role.delete()

            await self.bot.db.delete_study_group(group['id'])

    @app_commands.command(name="list_groups", description="List all study groups in the server")
    async def list_groups(self, interaction: discord.Interaction):
        groups = await self.bot.db.get_all_study_groups(interaction.guild_id)
        if not groups:
            await interaction.response.send_message("There are no active study groups in this server.", ephemeral=True)
            return

        embed = discord.Embed(title="Active Study Groups", color=discord.Color.blue())
        for group in groups:
            members = await self.bot.db.get_group_members(group['id'])
            embed.add_field(
                name=group['name'],
                value=f"Members: {len(members)}/{group['max_size']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite_to_group", description="Invite a user to your study group")
    @app_commands.describe(group_name="Name of the study group", user="User to invite")
    async def invite_to_group(self, interaction: discord.Interaction, group_name: str, user: discord.Member):
        # Check if the group exists
        group = await self.bot.db.get_study_group_by_name(interaction.guild_id, group_name)
        if not group:
            await interaction.response.send_message(f"No study group named '{group_name}' exists in this server.", ephemeral=True)
            return

        # Check if the inviter is in the group
        members = await self.bot.db.get_group_members(group['id'])
        if interaction.user.id not in members:
            await interaction.response.send_message(f"You're not a member of the study group '{group_name}'.", ephemeral=True)
            return

        # Check if the invited user is already in the group
        if user.id in members:
            await interaction.response.send_message(f"{user.display_name} is already in the study group '{group_name}'.", ephemeral=True)
            return

        # Check if the group is full
        if len(members) >= group['max_size']:
            await interaction.response.send_message(f"The study group '{group_name}' is full.", ephemeral=True)
            return

        # Add the user to the group
        await self.bot.db.add_group_member(group['id'], user.id)

        # Assign the session role to the new member
        _, session_role_id = await self.bot.db.get_group_roles(group['id'])
        session_role = interaction.guild.get_role(session_role_id)
        if session_role:
            await user.add_roles(session_role)

        # Send confirmation messages
        await interaction.response.send_message(f"You've successfully invited {user.mention} to the study group '{group_name}'.")
        await user.send(f"You've been invited to join the study group '{group_name}' in {interaction.guild.name}. You've been automatically added to the group.")

async def setup(bot):
    await bot.add_cog(StudyGroups(bot))
    logger.info("StudyGroups cog loaded")