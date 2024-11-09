import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import logging

# Set up logging
logger = logging.getLogger(__name__)

class PomodoroSession:
    def __init__(self, group_id, focus, short_break, long_break):
        self.group_id = group_id
        self.focus = focus
        self.short_break = short_break
        self.long_break = long_break
        self.current_stage = "focus"
        self.cycles = 0
        self.is_paused = False
        self.timer = None
        logger.info(f"Pomodoro session created for group {group_id} with focus: {focus}m, short break: {short_break}m, long break: {long_break}m")

class Pomodoro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        logger.info("Pomodoro cog initialized")

    @app_commands.command(name="start_pomodoro", description="Start a Pomodoro session for the study group")
    @app_commands.describe(
        focus="Focus duration in minutes",
        short_break="Short break duration in minutes",
        long_break="Long break duration in minutes"
    )
    async def start_pomodoro(self, interaction: discord.Interaction, focus: int = 25, short_break: int = 5, long_break: int = 15):
        logger.info(f"Attempt to start Pomodoro session by user {interaction.user.id}")
        group = await self.bot.db.get_user_group(interaction.user.id)
        if not group:
            logger.warning(f"User {interaction.user.id} tried to start Pomodoro without being in a group")
            await interaction.response.send_message("You're not in any study group.", ephemeral=True)
            return

        if group['id'] in self.sessions:
            logger.info(f"Pomodoro session already exists for group {group['id']}")
            await interaction.response.send_message("A Pomodoro session is already in progress for this group.", ephemeral=True)
            return

        session = PomodoroSession(group['id'], focus, short_break, long_break)
        self.sessions[group['id']] = session

        voice_channel_id = group['vc_id']
        if not voice_channel_id:
            voice_channel = await interaction.guild.create_voice_channel(f"{group['name']} VC")
            await self.bot.db.update_voice_channel(group['id'], voice_channel.id)
            logger.info(f"Created new voice channel {voice_channel.id} for group {group['id']}")
        else:
            voice_channel = interaction.guild.get_channel(voice_channel_id)

        if interaction.user.voice:
            await interaction.user.move_to(voice_channel)
            logger.info(f"Moved user {interaction.user.id} to voice channel {voice_channel.id}")
        else:
            logger.warning(f"User {interaction.user.id} is not in a voice channel")
            await interaction.response.send_message(f"Please join the voice channel {voice_channel.mention} to start the Pomodoro session.", ephemeral=True)
            return

        logger.info(f"Started Pomodoro session for group {group['id']}")
        await interaction.response.send_message(f"Pomodoro session started! Focus for {focus} minutes.")
        self.run_timer.start(interaction.guild_id, group['id'])

    @app_commands.command(name="end_pomodoro", description="End the current Pomodoro session")
    async def end_pomodoro(self, interaction: discord.Interaction):
        logger.info(f"Attempt to end Pomodoro session by user {interaction.user.id}")
        group = await self.bot.db.get_user_group(interaction.user.id)
        if not group or group['id'] not in self.sessions:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            await interaction.response.send_message("No active Pomodoro session for your group.", ephemeral=True)
            return

        self.run_timer.stop()
        del self.sessions[group['id']]
        logger.info(f"Ended Pomodoro session for group {group['id']}")
        await interaction.response.send_message("Pomodoro session ended.")

    @app_commands.command(name="pause_pomodoro", description="Pause the current Pomodoro session")
    async def pause_pomodoro(self, interaction: discord.Interaction):
        logger.info(f"Attempt to pause Pomodoro session by user {interaction.user.id}")
        group = await self.bot.db.get_user_group(interaction.user.id)
        if not group or group['id'] not in self.sessions:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            await interaction.response.send_message("No active Pomodoro session for your group.", ephemeral=True)
            return

        session = self.sessions[group['id']]
        if session.is_paused:
            logger.info(f"Pomodoro session for group {group['id']} is already paused")
            await interaction.response.send_message("Session is already paused.", ephemeral=True)
            return

        session.is_paused = True
        logger.info(f"Paused Pomodoro session for group {group['id']}")
        await interaction.response.send_message("Pomodoro session paused.")

    @app_commands.command(name="resume_pomodoro", description="Resume the paused Pomodoro session")
    async def resume_pomodoro(self, interaction: discord.Interaction):
        logger.info(f"Attempt to resume Pomodoro session by user {interaction.user.id}")
        group = await self.bot.db.get_user_group(interaction.user.id)
        if not group or group['id'] not in self.sessions:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            await interaction.response.send_message("No active Pomodoro session for your group.", ephemeral=True)
            return

        session = self.sessions[group['id']]
        if not session.is_paused:
            logger.info(f"Pomodoro session for group {group['id']} is not paused")
            await interaction.response.send_message("Session is not paused.", ephemeral=True)
            return

        session.is_paused = False
        logger.info(f"Resumed Pomodoro session for group {group['id']}")
        await interaction.response.send_message("Pomodoro session resumed.")

    @tasks.loop(seconds=1)
    async def run_timer(self, guild_id, group_id):
        session = self.sessions[group_id]
        if session.is_paused:
            return

        if session.timer is None:
            session.timer = session.focus * 60

        session.timer -= 1

        if session.timer <= 0:
            if session.current_stage == "focus":
                session.cycles += 1
                if session.cycles % 4 == 0:
                    session.current_stage = "long_break"
                    session.timer = session.long_break * 60
                    logger.info(f"Group {group_id} starting long break")
                    await self.send_notification(guild_id, group_id, f"Focus session ended. Take a long break for {session.long_break} minutes!")
                else:
                    session.current_stage = "short_break"
                    session.timer = session.short_break * 60
                    logger.info(f"Group {group_id} starting short break")
                    await self.send_notification(guild_id, group_id, f"Focus session ended. Take a short break for {session.short_break} minutes!")
            else:
                session.current_stage = "focus"
                session.timer = session.focus * 60
                logger.info(f"Group {group_id} starting focus session")
                await self.send_notification(guild_id, group_id, f"Break ended. Focus for {session.focus} minutes!")

    async def send_notification(self, guild_id, group_id, message):
        guild = self.bot.get_guild(guild_id)
        if guild:
            group = await self.bot.db.get_study_group(guild_id)
            if group:
                _, session_role_id = await self.bot.db.get_group_roles(group['id'])
                session_role = guild.get_role(session_role_id)
                if session_role:
                    voice_channel_id = group['vc_id']
                    voice_channel = guild.get_channel(voice_channel_id)
                    if voice_channel:
                        await voice_channel.send(f"{session_role.mention} {message}")
                        logger.info(f"Sent notification to voice channel {voice_channel.id} for group {group_id}")
                    else:
                        # Fallback to the first text channel if voice channel is not found
                        channel = guild.text_channels[0]
                        await channel.send(f"{session_role.mention} {message}")
                        logger.warning(f"Voice channel not found for group {group_id}, sent notification to text channel {channel.id}")

    @app_commands.command(name="pomodoro_status", description="Check the status of the current Pomodoro session")
    async def pomodoro_status(self, interaction: discord.Interaction):
        logger.info(f"Pomodoro status check by user {interaction.user.id}")
        group = await self.bot.db.get_user_group(interaction.user.id)
        if not group or group['id'] not in self.sessions:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            await interaction.response.send_message("No active Pomodoro session for your group.", ephemeral=True)
            return

        session = self.sessions[group['id']]
        remaining_time = timedelta(seconds=session.timer)
        status = "Paused" if session.is_paused else "Running"
        stage = session.current_stage.capitalize()

        embed = discord.Embed(title="Pomodoro Status", color=discord.Color.blue())
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Current Stage", value=stage, inline=False)
        embed.add_field(name="Time Remaining", value=str(remaining_time), inline=False)
        embed.add_field(name="Completed Cycles", value=str(session.cycles), inline=False)

        logger.info(f"Sent Pomodoro status for group {group['id']}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Pomodoro(bot))
    logger.info("Pomodoro cog loaded")