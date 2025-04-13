import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils import seconds_to_hms
import random
from datetime import datetime, timedelta
import logging

# Set up logging
logger = logging.getLogger(__name__)

class PomodoroSession:
    def __init__(self, group_id: int, focus: int, short_break: int, long_break: int, message: discord.Message = None):
        """Initializes a Pomodoro session.

        Args:
            group_id (int): The ID of the study group.
            focus (int): The duration of the focus period in minutes.
            short_break (int): The duration of the short break in minutes.
            long_break (int): The duration of the long break in minutes.
            message (discord.Message, optional): The message associated with the Pomodoro session. Defaults to None.
        """
        self.group_id: int = group_id
        self.focus: int = focus  #: The duration of the focus period in minutes.
        self.short_break: int = short_break  #: The duration of the short break in minutes.
        self.long_break: int = long_break  #: The duration of the long break in minutes.
        self.current_stage: str = "focus"  #: The current stage of the Pomodoro session (focus, short_break, long_break).
        self.cycles: int = 0  #: The number of completed cycles.
        self.is_paused: bool = False  #: Indicates whether the Pomodoro session is paused.
        self.timer: int = None  #: The remaining time in seconds for the current stage.
        self.message: discord.Message = message  #: The message associated with the Pomodoro session.
        logger.info(
            f"Pomodoro session created for group {self.group_id} with focus: {self.focus}m, "
            f"short break: {self.short_break}m, long break: {self.long_break}m"
        )


class Pomodoro(commands.Cog):
    def __init__(self, bot: commands.Bot, db):
        self.bot: commands.Bot = bot
        self.db = db
        self.sessions: Dict[int, PomodoroSession] = {}
        logger.info("Pomodoro cog initialized.")
    
    def create_embed(self, session: PomodoroSession) -> discord.Embed:
        """Creates an embed to display the Pomodoro session status.

        Args:
            session (PomodoroSession): The Pomodoro session.

        Returns:
            discord.Embed: The embed containing the Pomodoro session status.
        """
        remaining_time = timedelta(seconds=session.timer) if session.timer else timedelta(seconds=session.focus * 60)
        status = "Paused" if session.is_paused else "Running"
        stage = session.current_stage.capitalize()

        embed = discord.Embed(title="Pomodoro Status", color=discord.Color.blue())
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Current Stage", value=stage, inline=False)
        embed.add_field(name="Time Remaining", value=str(remaining_time), inline=False)
        embed.add_field(name="Completed Cycles", value=str(session.cycles), inline=False)

        return embed

    @app_commands.command(name="start_pomodoro", description="Start a Pomodoro session for the study group")
    @app_commands.describe(
        focus="Focus duration in minutes",
        short_break="Short break duration in minutes",
        long_break="Long break duration in minutes"
    )
    async def start_pomodoro(self, interaction: discord.Interaction, focus: int = 25, short_break: int = 5, long_break: int = 15):
        """Starts a Pomodoro session for the study group.

        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
            focus (int, optional): The duration of the focus period in minutes. Defaults to 25.
            short_break (int, optional): The duration of the short break in minutes. Defaults to 5.
            long_break (int, optional): The duration of the long break in minutes. Defaults to 15.
        """
        try:
            logger.info(f"Attempt to start Pomodoro session by user {interaction.user.id}")
            group = await self.db.get_user_group(interaction.user.id)
            if not group:
                logger.warning(f"User {interaction.user.id} tried to start Pomodoro without being in a group")
                await interaction.followup.send("You're not in any study group.", ephemeral=True)
                return

            if group['id'] in self.sessions:
                logger.info(f"Pomodoro session already exists for group {group['id']}")
                await interaction.followup.send("A Pomodoro session is already in progress for this group.", ephemeral=True)
                return

            session = PomodoroSession(group['id'], focus, short_break, long_break)
            self.sessions[group['id']] = session

            voice_channel_id = group['voice_channel_id']
            if not voice_channel_id:
                voice_channel = await interaction.guild.create_voice_channel(f"{group['name']} VC")
                await self.db.update_voice_channel(group['id'], voice_channel.id)
                logger.info(f"Created new voice channel {voice_channel.id} for group {group['id']}")
            else:
                voice_channel = interaction.guild.get_channel(voice_channel_id)

            if interaction.user.voice:
                await interaction.user.move_to(voice_channel)
                logger.info(f"Moved user {interaction.user.id} to voice channel {voice_channel.id}")
            else:
                logger.warning(f"User {interaction.user.id} is not in a voice channel")
                await interaction.followup.send(f"Please join the voice channel {voice_channel.mention} to start the Pomodoro session.", ephemeral=True)
                return

            logger.info(f"Started Pomodoro session for group {group['id']}")
            embed = self.create_embed(session)
            await interaction.followup.send(embed=embed)
            self.run_timer.start(interaction.guild_id, group['id'])
        except Exception as e:
            logger.error(f"Error starting Pomodoro session: {e}")
            await interaction.followup.send("An error occurred while starting the Pomodoro session.", ephemeral=True)

    @app_commands.command(name="end_pomodoro", description="End the current Pomodoro session")
    async def end_pomodoro(self, interaction: discord.Interaction):
        """Ends the current Pomodoro session.

        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
        """
        try:
            logger.info(f"Attempt to end Pomodoro session by user {interaction.user.id}")
            group = await self.db.get_user_group(interaction.user.id)
            if not group or group['id'] not in self.sessions:
                logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
                await interaction.followup.send("No active Pomodoro session for your group.", ephemeral=True)
                return

            self.run_timer.stop()
            del self.sessions[group['id']]
            logger.info(f"Ended Pomodoro session for group {group['id']} by user {interaction.user.id}")
            await interaction.followup.send("Pomodoro session ended.")
        except Exception as e:
            logger.error(f"Error ending Pomodoro session: {e}")
            await interaction.followup.send("An error occurred while ending the Pomodoro session.", ephemeral=True)

    @app_commands.command(name="pause_pomodoro", description="Pause the current Pomodoro session")
    async def pause_pomodoro(self, interaction: discord.Interaction):
        """Pauses the current Pomodoro session.

        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
        """
        try:
            logger.info(f"Attempt to pause Pomodoro session by user {interaction.user.id}")
            group = await self.db.get_user_group(interaction.user.id)
            if not group or group['id'] not in self.sessions:
                logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
                await interaction.followup.send("No active Pomodoro session for your group.", ephemeral=True)
                return

            session = self.sessions[group['id']]
            if session.is_paused:
                logger.info(f"Pomodoro session for group {group['id']} is already paused")
                await interaction.followup.send("Session is already paused.", ephemeral=True)
                return

            session.is_paused = True
            logger.info(f"Paused Pomodoro session for group {group['id']} by user {interaction.user.id}")
            await interaction.followup.send("Pomodoro session paused.")
        except Exception as e:
            logger.error(f"Error pausing Pomodoro session: {e}")
            await interaction.followup.send("An error occurred while pausing the Pomodoro session.", ephemeral=True)

    @app_commands.command(name="resume_pomodoro", description="Resume the paused Pomodoro session")
    async def resume_pomodoro(self, interaction: discord.Interaction):
        """Resumes the paused Pomodoro session.

        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
        """
        try:
            logger.info(f"Attempt to resume Pomodoro session by user {interaction.user.id}")
            group = await self.db.get_user_group(interaction.user.id)
            if not group or group['id'] not in self.sessions:
                logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
                await interaction.followup.send("No active Pomodoro session for your group.", ephemeral=True)
                return

            session = self.sessions[group['id']]
            if not session.is_paused:
                logger.info(f"Pomodoro session for group {group['id']} is not paused")
                await interaction.followup.send("Session is not paused.", ephemeral=True)
                return

            session.is_paused = False
            logger.info(f"Resumed Pomodoro session for group {group['id']}")
            await interaction.followup.send("Pomodoro session resumed.")
        except Exception as e:
            logger.error(f"Error resuming Pomodoro session: {e}")
            await interaction.followup.send("An error occurred while resuming the Pomodoro session.", ephemeral=True)

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
                await self.send_notification(group_id, f"Focus session ended. Take a long break for {session.long_break} minutes!")
                else:
                    session.current_stage = "short_break"
                    session.timer = session.short_break * 60
                    logger.info(f"Group {group_id} starting short break")
                await self.send_notification(group_id, f"Focus session ended. Take a short break for {session.short_break} minutes!")

            else:
                session.current_stage = "focus"
                session.timer = session.focus * 60
                logger.info(f"Group {group_id} starting focus session")
                await self.send_notification(guild_id, group_id, f"Break ended. Focus for {session.focus} minutes!")

        # Check if voice channel is empty and end session if so
        guild = self.bot.get_guild(guild_id)
        group = await self.db.get_study_group(group_id)
        voice_channel_id = group['voice_channel_id']
        voice_channel = guild.get_channel(voice_channel_id)
        if voice_channel and not voice_channel.members:
            logger.info(f"All members left voice channel {voice_channel.id} for group {group_id}. Ending Pomodoro session.")
            await self.end_pomodoro_by_group_id(group_id)
            return

    async def send_notification(self, group_id: int, message: str):
        """Sends a notification to the group's voice channel or a fallback text channel.

        Args:
            group_id (int): The ID of the study group.
            message (str): The message to send.
        """
        guild = self.bot.get_guild(guild_id)
        group = await self.db.get_study_group(group_id)
        _, session_role_id = await self.db.get_group_roles(group['id'])
        session_role = guild.get_role(session_role_id)
        session = self.sessions.get(group_id)
        if session and session_role:
            voice_channel_id = group['voice_channel_id']
            voice_channel = guild.get_channel(voice_channel_id)
            text_channel = guild.get_channel(group['text_channel_id'])

            if voice_channel:
                await text_channel.send(f"{session_role.mention} {message}")
                logger.info(f"Sent notification to voice channel {text_channel.id} for group {group_id}")
            else:
                logger.warning(f"Voice channel not found for group {group_id}, no notification sent.")

    @app_commands.command(name="pomodoro_status", description="Check the status of the current Pomodoro session")
    async def pomodoro_status(self, interaction: discord.Interaction):
        """Checks the status of the current Pomodoro session.

        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
        """
        try:
            logger.info(f"Pomodoro status check by user {interaction.user.id}")
            group = await self.db.get_user_group(interaction.user.id)
            if not group or group['id'] not in self.sessions:
                logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
                await interaction.followup.send("No active Pomodoro session for your group.", ephemeral=True)
                return

            session = self.sessions[group['id']]
            remaining_time = timedelta(seconds=session.timer) if session.timer else timedelta(seconds=session.focus * 60)
            status = "Paused" if session.is_paused else "Running"
            stage = session.current_stage.capitalize()

            embed = discord.Embed(title="Pomodoro Status", color=discord.Color.blue())
            embed.add_field(name="Status", value=status, inline=False)
            embed.add_field(name="Current Stage", value=stage, inline=False)
            embed.add_field(name="Time Remaining", value=str(remaining_time), inline=False)
            embed.add_field(name="Completed Cycles", value=str(session.cycles), inline=False)

            logger.info(f"Sent Pomodoro status for group {group['id']}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error checking Pomodoro status: {e}")
            await interaction.followup.send("An error occurred while checking the Pomodoro status.", ephemeral=True)

    async def end_pomodoro_by_group_id(self, group_id):
        """Ends a Pomodoro session by group ID.
        """
        if group_id in self.sessions:
            self.run_timer.stop()
            del self.sessions[group_id]
            logger.info(f"Pomodoro session ended for group {group_id} due to empty voice channel.")
            #Send a notification
            guild = self.bot.get_guild(await self.bot.db.get_study_group(group_id).guild_id)
            if guild:
                await self.send_notification(guild.id, group_id, "Pomodoro session ended because all members left the voice channel.")

async def setup(bot):
    """Sets up the Pomodoro cog."""
    db = bot.db  # Assuming bot.db is the database handler
    await bot.add_cog(Pomodoro(bot, db))
    logger.info("Pomodoro cog loaded.")
