import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from utils import parse_seconds_to_hms, parse_duration, parse_mentions, app_is_manager
import random

# Array of user-friendly error phrases
ERROR_PHRASES = [
    "Oops! Something went wrong. Please try again.",
    "Whoops! Let's give that another shot.",
    "Hmm, that didn't work as expected. Try again?",
    "Yikes! An error occurred. Please try later.",
    "Oh no! We hit a snag. Please try once more.",
    "Sorry about that! Let's try again.",
    "Something didn't go as planned. Try again?",
    "Looks like something went wrong. Please try again.",
    "An unexpected error occurred. Please try again later.",
    "We're having a little trouble. Please try again.",
    "Sorry! We encountered an issue. Let's try again.",
    "Hmmm, something's not right. Try again soon!",
    "Our system stumbled. Please try again.",
    "Let's try that again—something went wrong.",
    "Oops! That didn't work as planned. Please try again.",
    "We encountered an error. Please try again.",
    "Apologies! Something went wrong. Please try once more.",
    "It looks like there was an error. Try again?",
    "Whoops! We ran into an issue. Please try again later.",
    "Something went wrong on our end. Please try again."
]

class StudyGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_session_role(self, guild, session_name):
        try:
            role_name = f"In {session_name}"
            return await guild.create_role(name=role_name, mentionable=True)
        except discord.errors.Forbidden:
            return None

    @app_commands.command(name="create_group", description="Create a new study group")
    @app_commands.describe(name="Name of the study group", max_size="Maximum number of members")
    @app_is_manager()
    async def create_group(self, interaction: discord.Interaction, name: str, max_size: int = 10):
        try:
            await interaction.response.defer()

            existing_group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
            if existing_group:
                await interaction.followup.send(f"A study group named '{name}' already exists in this server.", ephemeral=True)
                return

            end_time = asyncio.get_event_loop().time() + 43200  # 12 hours
            group_id = await self.bot.db.create_study_group(name, interaction.user.id, max_size, end_time, interaction.guild_id)
            await self.bot.db.add_group_member(group_id, interaction.user.id)

            admin_role = await interaction.guild.create_role(name=f"Study Group Admin: {name}")
            session_role = await self.create_session_role(interaction.guild, name)
            
            await interaction.user.add_roles(admin_role, session_role)

            await self.bot.db.update_group_roles(group_id, admin_role.id, session_role.id)

            await interaction.followup.send(
                f"Study group '{name}' created! Use /join_group to join.\n"
                f"You've been assigned the roles {admin_role.mention} and {session_role.mention}."
            )
        except discord.errors.Forbidden:
            await interaction.followup.send("I don't have permission to create roles or assign them. Please check my permissions and try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

    @app_commands.command(name="join_group", description="Join an existing study group")
    @app_commands.describe(name="Name of the study group to join")
    async def join_group(self, interaction: discord.Interaction, name: str):
        try:
            await interaction.response.defer()

            group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
            if not group:
                await interaction.followup.send(f"No study group named '{name}' exists in this server.", ephemeral=True)
                return

            members = await self.bot.db.get_group_members(group['id'])
            if len(members) >= group['max_size']:
                await interaction.followup.send("This group is full.", ephemeral=True)
                return

            if interaction.user.id in members:
                await interaction.followup.send("You're already in this study group.", ephemeral=True)
                return

            await self.bot.db.add_group_member(group['id'], interaction.user.id)

            _, session_role_id = await self.bot.db.get_group_roles(group['id'])
            session_role = interaction.guild.get_role(session_role_id)

            if session_role:
                await interaction.user.add_roles(session_role)

            await interaction.followup.send(
                f"You've joined the study group '{name}'!\n"
                f"You've been assigned the role {session_role.mention}."
            )
        except discord.errors.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles. Please check my permissions and try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

    @app_commands.command(name="leave_group", description="Leave a study group")
    @app_commands.describe(name="Name of the study group to leave")
    async def leave_group(self, interaction: discord.Interaction, name: str):
        try:
            await interaction.response.defer()

            group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
            if not group:
                await interaction.followup.send(f"No study group named '{name}' exists in this server.", ephemeral=True)
                return

            members = await self.bot.db.get_group_members(group['id'])
            if interaction.user.id not in members:
                await interaction.followup.send(f"You're not in the study group '{name}'.", ephemeral=True)
                return

            await self.bot.db.remove_group_member(group['id'], interaction.user.id)
            
            admin_role_id, session_role_id = await self.bot.db.get_group_roles(group['id'])
            session_role = interaction.guild.get_role(session_role_id)
            
            if session_role:
                await interaction.user.remove_roles(session_role)
            
            await interaction.followup.send(f"You've left the study group '{name}'.")

            updated_members = await self.bot.db.get_group_members(group['id'])
            if not updated_members:
                await self.end_group(interaction.guild_id, name)
        except discord.errors.Forbidden:
            await interaction.followup.send("I don't have permission to remove roles. Please check my permissions and try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

    @app_commands.command(name="end_group", description="End a study group")
    @app_commands.describe(name="Name of the study group to end")
    @app_is_manager()
    async def end_group_command(self, interaction: discord.Interaction, name: str):
        try:
            await interaction.response.defer()

            group = await self.bot.db.get_study_group_by_name(interaction.guild_id, name)
            if not group:
                await interaction.followup.send(f"No study group named '{name}' exists in this server.", ephemeral=True)
                return

            await self.end_group(interaction.guild_id, name)
            await interaction.followup.send(f"The study group '{name}' has been ended.")
        except discord.errors.Forbidden:
            await interaction.followup.send("I don't have permission to delete roles. Please check my permissions and try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

    async def end_group(self, guild_id, name):
        try:
            group = await self.bot.db.get_study_group_by_name(guild_id, name)
            if group:
                admin_role_id, session_role_id = await self.bot.db.get_group_roles(group['id'])
                guild = self.bot.get_guild(guild_id)
                
                admin_role = guild.get_role(admin_role_id)
                session_role = guild.get_role(session_role_id)
                
                if admin_role:
                    await admin_role.delete()
                if session_role:
                    await session_role.delete()
                
                await self.bot.db.delete_study_group(group['id'])
        except Exception as e:
            print(f"Error ending group: {e}")

    @app_commands.command(name="list_groups", description="List all study groups in the server")
    async def list_groups(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            groups = await self.bot.db.get_all_study_groups(interaction.guild_id)
            if not groups:
                await interaction.followup.send("There are no active study groups in this server.", ephemeral=True)
                return

            embed = discord.Embed(title="Active Study Groups", color=discord.Color.blue())
            for group in groups:
                members = await self.bot.db.get_group_members(group['id'])
                embed.add_field(
                    name=group['name'],
                    value=f"Members: {len(members)}/{group['max_size']}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

    @app_commands.command(name="invite_to_group", description="Invite a user to your study group")
    @app_commands.describe(group_name="Name of the study group", user="User to invite")
    async def invite_to_group(self, interaction: discord.Interaction, group_name: str, user: discord.Member):
        try:
            await interaction.response.defer()

            group = await self.bot.db.get_study_group_by_name(interaction.guild_id, group_name)
            if not group:
                await interaction.followup.send(f"No study group named '{group_name}' exists in this server.", ephemeral=True)
                return

            members = await self.bot.db.get_group_members(group['id'])
            if interaction.user.id not in members:
                await interaction.followup.send(f"You're not a member of the study group '{group_name}'.", ephemeral=True)
                return

            if user.id in members:
                await interaction.followup.send(f"{user.display_name} is already in the study group '{group_name}'.", ephemeral=True)
                return

            if len(members) >= group['max_size']:
                await interaction.followup.send(f"The study group '{group_name}' is full.", ephemeral=True)
                return

            await self.bot.db.add_group_member(group['id'], user.id)

            _, session_role_id = await self.bot.db.get_group_roles(group['id'])
            session_role = interaction.guild.get_role(session_role_id)
            if session_role:
                await user.add_roles(session_role)

            await interaction.followup.send(f"You've successfully invited {user.mention} to the study group '{group_name}'.")
            await user.send(f"You've been invited to join the study group '{group_name}' in {interaction.guild.name}. You've been automatically added to the group.")
        except discord.errors.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles or send DMs. Please check my permissions and try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{random.choice(ERROR_PHRASES)} (Only you can see this message)", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StudyGroups(bot))