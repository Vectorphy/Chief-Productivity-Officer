import asyncio
import logging
import random
import sys
import uuid
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Select, View

from database import DBHandler
from utils import check_manager, parse_duration, parse_mentions, parse_seconds_to_hms, validate_parameters

# Setting up basic configuration for logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
current_namespace = sys.modules[__name__].__name__.split('.')[-1]


## Enums
# Enum to regularize the status of member_statuses
class MemberStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    EXITED = "exited"
    BREAK = "break"

# Enum regularize the keys of member_statuses
class MemberStatusKey(str, Enum):
    STATUS = "status"
    ABSENCES = "absences"



## Permission Class
class CheckinGuildSettings:
    def __init__(
        self,
        interaction : Optional[discord.Interaction] = None,
        max_members : int = 10,
        min_duration : int = 20,
        max_duration : int = 7200,
        max_absences : int = 3,
        max_breaks : int = 3,
        max_user_sessions : int = 5,
        permission_mode : str = "ALLOW"
    ):

        self.guild_id = interaction.guild.id if interaction and interaction.guild else 0
        self.max_members = max_members
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_absences = max_absences
        self.max_breaks = max_breaks
        self.max_user_sessions = max_user_sessions
        self.permission_mode = permission_mode

        self.whitelist_channels: List[int] = []
        self.whitelist_roles: List[int] = []
        self.blacklist_channels: List[int] = []
        self.blacklist_roles: List[int] = []

    def has_permission(self, user_id: int, channel_id: int, role_ids: List[int]) -> bool:
        """Checks if a user has permission based on the guild's settings."""
        logger.info(f"Checking permissions for user {user_id} in channel {channel_id} in guild {self.guild_id}...")

        if self.permission_mode == "ALLOW":
            if self.whitelist_channels and channel_id not in self.whitelist_channels:
                return False
            if self.whitelist_roles:
                if not set(role_ids).intersection(self.whitelist_roles):
                    return False
        elif self.permission_mode == "DENY":
            if user_id == self.guild_id:
                return False
            if self.blacklist_channels and channel_id in self.blacklist_channels:
                return False
            if self.blacklist_roles:
                if set(role_ids).intersection(self.blacklist_roles):
                    return False
        return True

    ### --- DECORATORS --- ###

    ## Check - Member
    @staticmethod
    def is_member(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if a user is a member of the session."""
        @wraps(func)
        async def wrapper(session : 'CheckinSession', interaction: discord.Interaction, *args, **kwargs):
            if interaction.user.id not in session.member_ids:
                await interaction.response.send_message("You are not a member of this session.", ephemeral=True)
                return
            return await func(session, interaction, *args, **kwargs)
        return wrapper

    ## Check - Member Limit
    @staticmethod
    def check_member_limit(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if adding a member exceeds the max_members limit."""
        @wraps(func)
        async def wrapper(session: 'CheckinSession', interaction: discord.Interaction, *args: Any, **kwargs: Any) -> Any:
            if len(session.member_ids) >= session.max_members:
                await interaction.response.send_message("The session has reached its maximum member capacity.", ephemeral=True)
                return
            return await func(session, interaction, *args, **kwargs)
        return wrapper

    ## Check - Absence Limit
    @staticmethod
    def check_absence_limit(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if member absences exceed the max_absences limit."""
        @wraps(func)
        async def wrapper(session: 'CheckinSession', member_id: int, *args: Any, **kwargs: Any) -> Any:
            member_status = session.member_statuses.get(member_id, {})
            if member_status.get(MemberStatusKey.ABSENCES.value, 0) >= session.max_absences:
                logger.info("Member %s has reached the maximum absence limit.", member_id)
                session.member_statuses[member_id][MemberStatusKey.STATUS.value] = MemberStatus.EXITED.value
                return
            return await func(session, member_id, *args, **kwargs)
        return wrapper

    ## Check - Break Limit
    @staticmethod
    def check_break_limit(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if member break count exceeds the max_breaks limit."""
        @wraps(func)
        async def wrapper(session: 'CheckinSession', member_id: int, *args: Any, **kwargs: Any) -> Any:
            member_status = session.member_statuses.get(member_id, {})
            if member_status.get("break_count", 0) >= session.max_breaks:
                logger.info("Member %s has reached the maximum break limit.", member_id)
                return
            return await func(session, member_id, *args, **kwargs)
        return wrapper

    ## Check - Owner
    @staticmethod
    def is_owner(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if a user is the owner/creator of the session or a server manager/moderator."""
        @wraps(func)
        async def wrapper(session : 'CheckinSession', interaction: discord.Interaction, *args, **kwargs):
            is_authorized = interaction.user.id in (session.owner_id, session.creator_id) or await check_manager(interaction)
            if not is_authorized:
                if interaction.response.is_done():
                    await interaction.followup.send("You are not authorized to control this session.", ephemeral=True)
                else:
                    await interaction.response.send_message("You are not authorized to control this session.", ephemeral=True)
                return
            return await func(session, interaction, *args, **kwargs)
        return wrapper

    # Check - /checkin Command Permissions
    @staticmethod
    def checkin_command_permissions(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check permissions for the `/checkin` command."""
        @wraps(func)
        async def wrapper(cog : 'CheckinCog', interaction: discord.Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
                return
            if cog.guild_settings is None:
                cog.guild_settings = {}
            if interaction.guild.id not in cog.guild_settings:
                cog.guild_settings[interaction.guild.id] = CheckinGuildSettings(interaction)
            guild_settings: CheckinGuildSettings = cog.guild_settings[interaction.guild.id]

            # Bypass check for bot developer or server administrator
            is_dev = getattr(interaction.client, 'bot_developer_id', None) == interaction.user.id
            is_admin = getattr(interaction.user, 'guild_permissions', None) and interaction.user.guild_permissions.administrator  # type: ignore[union-attr]
            if is_dev or is_admin:
                return await func(cog, interaction, *args, **kwargs)

            role_ids = [role.id for role in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
            if not guild_settings.has_permission(interaction.user.id, interaction.channel.id if interaction.channel else 0, role_ids):
                await interaction.response.send_message("You don't have permission to use this command here.", ephemeral=True)
                return
            return await func(cog, interaction, *args, **kwargs)
        return wrapper

    ## Check - Max User Groups
    @staticmethod
    def check_user_groups(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to check if a user is within the limit of allowed sessions/groups."""
        @wraps(func)
        async def wrapper(cog : 'CheckinCog', interaction: discord.Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
                return

            guild_settings : Optional[CheckinGuildSettings] = cog.guild_settings.get(interaction.guild.id) if cog.guild_settings else None
            if guild_settings:
                user_sessions_count = sum(interaction.user.id in session.member_ids for session in cog.active_sessions.values())
                if user_sessions_count >= guild_settings.max_user_sessions:
                    await interaction.response.send_message("You've reached the limit for active sessions you can join.", ephemeral=True)
                    return
            return await func(cog, interaction, *args, **kwargs)
        return wrapper







class CheckinSession:
    # It's in class
    prompt_messages = [
        "How's it going?",
        "What's the progress?",
        "Hey, you there?",
        "Quick status pulse: What are you actively working on right now?",
        "Brain check! Are you locked in, hyperfocusing, or wandering off into Wikipedia?",
        "Executive function checkpoint: Did you start the thing or are you planning to start the thing?",
        "Dopamine ping! What's one micro-win you've notched since the last ping?",
        "Tab triage: Are you on your target tab or did you open 37 new ones?",
        "Shoulders down, jaw unclenched, deep breath. Now: how's the task coming along?",
        "Zero shame zone: If you got stuck on a side quest, here is your friendly portal back to the main quest!",
        "Hydration & posture check! Take a sip, sit upright, and give us a quick status update.",
        "What's the very next step on your plate? Just one sentence!",
        "Side-quest radar: Did you accidentally reorganize your workspace instead of doing the task?",
        "How is the friction level right now? Smooth sailing or pulling teeth?",
        "Accountability wave! Drop a word or hit Present to log your attendance.",
        "Did you hit a roadblock? Remember, making it ugly is better than not making it at all!",
        "Task paralysis check-in: If you're staring blankly at the screen, pick the tiniest micro-step.",
        "How are the energy levels holding up? Steady, surging, or fading?",
        "Progress check! Did you cross anything off, or did you make the task smaller?",
        "Quick sensory check: Room too loud? Lights too bright? Temperature okay? How's focus?",
        "Friendly reminder: Done is better than perfect. What's moving forward right now?",
        "Are you in the flow zone or fighting the distraction gremlins?",
        "Dopamine dispenser here! Tell us one good thing you tackled.",
        "Did you get trapped in research mode? Time to switch from collecting info to doing the work!",
        "Knock knock! How goes the battle against procrastination today?",
        "Just checking in: Are you making headway on your current milestone?",
        "Momentum check: Even a 1% progress step counts. What's yours?",
        "Have you looked away from your screen in the last 20 minutes? Blink, stretch, and report in!",
        "Did an interesting side idea pop up? Jot it on a sticky note for later and stay on course!",
        "What are you working on right this second? Type it out or hit Present!",
        "Is the task boss fight almost defeated, or is it in phase two?",
        "Reality check: You don't have to finish everything today, just make a dent. How's that dent looking?",
        "Hey! Don't let perfectionism stop you. Where are you at right now?",
        "Status drop time! What's currently occupying your working memory?",
        "Are you riding the hyperfocus wave or paddling against the current?",
        "Quick breath, quick sip of water. How is the work progressing?",
        "If your brain checked out, that's completely valid. Hit Present and gently ease back in.",
        "Did you write any words, code any lines, or read any pages? Share a snippet!",
        "Ping! What's the main obstacle standing between you and the finish line right now?",
        "Time check! Has time flown by in a blink, or is every minute crawling?",
        "Gentle nudge: You're doing great just by showing up here. How's the task going?",
        "What's the current objective on your radar?",
        "Did you take your meds / drink your water / eat a snack today? Quick bodily needs check!",
        "Are you stuck on how to start? Write the worst first draft possible just to get going.",
        "Checking in on the squad! Who is crushing tasks and who needs a dopamine boost?",
        "Micro-update request: What's one thing you figured out or completed?",
        "Focus beacon active! Beam in your current coordinates and status.",
        "Are you multitasking (aka opening 12 apps at once)? Let's single-task for the next sprint.",
        "How does your to-do list look right now? Shrinking or holding strong?",
        "Look at you, still here and persisting! How is progress looking?",
        "Hey champion, checking in! What are you conquering right now?",
        "Are you in waiting-mode or actively moving things forward?",
        "Don't judge yourself for a slow start; momentum builds slowly. What's the next action?",
        "Status update! Drop a quick reaction or update on your progress.",
        "Quick checkpoint: Are you working on the priority task, or the fun easy task?",
        "Breathe in for 4, hold for 4, exhale for 4. What's the current mission?",
        "Did you get caught in a rabbit hole? Grab a rope, climb back out, and tell us where you're at!",
        "Are your headphones playing the same song on repeat? How's the rhythm going?",
        "Check-in time! Let us know: are you still in the study trenches?",
        "If you're stuck, try explaining your problem out loud (rubber duck style). What are you working on?",
        "Accountability check! One word to describe your current progress right now?",
        "How's the mental bandwidth? Need to switch gears or keep rolling?",
        "Did you finish that thing you were dreading? If so, celebrate! If not, take one swing at it.",
        "Notice check: Unclench your jaw, drop your tongue from the roof of your mouth. How goes it?",
        "Just a quick poke to make sure you didn't wander off into a YouTube documentary!",
        "What's your current victory count for this study session?",
        "Is your focus crystal clear, mildly fuzzy, or completely scattered? We support all three!",
        "Checking in! Remember: any action creates motivation, not the other way around.",
        "Are you staring at an intimidating wall of text? Break it into bullet points and tell us your status.",
        "Hey study buddy! Drop a ping so we know you're alive and kicking.",
        "What's the hardest part of what you're doing right now? You got this!",
        "How is your focus stamina? Let us know if you need to take a quick break.",
        "Progress pulse: Give us a percentage of how close you are to finishing your current goal.",
        "Did you remember to blink? Screen fatigue is real. How's the assignment/project looking?",
        "Friendly reminder: Low stimulation causes drift. Put on lo-fi/white noise and check in!",
        "Are you fighting an urgent urge to clean the whole kitchen? Resist and report your progress!",
        "Checking in! What's one sentence about what you're tackling right now?",
        "How goes the productivity battle? Are we winning, regrouping, or holding the line?",
        "Micro-step shoutout: Did you open the document? That counts! What's next?",
        "Did the shiny object syndrome strike? Park that thought and tell us your current task!",
        "Hey there! Sending some virtual body-doubling focus your way. How's it going?",
        "Check-in chime! Give us the scoop: what's the latest update?",
        "Are you stuck in analysis paralysis? Roll a die or flip a coin to pick the next step!",
        "Status check: What's the title of the document or window currently open?",
        "How is the concentration bubble holding up? Still intact or popped?",
        "Check-in call! Are you actively working, taking notes, or thinking deeply?",
        "You're doing awesome just sitting here and giving it effort. How's the progress?",
        "Quick reality pulse: Are you working on what you intended to work on?",
        "Are you feeling overwhelmed? Zoom in on just the next 5 minutes. What's the plan?",
        "Check-in alert! Hit that Present button to keep your streak alive!",
        "How goes the deep dive? Did you discover anything cool or finish a section?",
        "Fidget check! Grab your stim toy, shake your hands out, and tell us where you're at.",
        "Are you running low on fuel? Remember snacks exist! How is the work coming along?",
        "Quick accountability scan: Are you on track with your target for this session?",
        "What's one thing you can cross off or simplify right now?",
        "Hey! Body double check-in: We are working alongside you. How's your current sprint?",
        "Did you finish a hard step? Give yourself high fives and let us know your status!",
        "Still hanging in there? Hit Present or Drop an update so we know you're here.",
        "What's the main takeaway from this work block so far?",
        "Final stretch mindset: What's the last piece of the puzzle you want to finish?"
    ]

    def __init__(self, db : DBHandler, cog : 'CheckinCog', interaction : Optional[discord.Interaction], name : str, member_ids: List[int], duration : int, settings: CheckinGuildSettings):

        # Critical Info first
        self.guild_id : int = interaction.guild.id if interaction and interaction.guild else 0
        self.name : str = name
        self.session_id : str = self.generate_session_id()
        self.creator_id : int = interaction.user.id if interaction else 0
        self.owner_id : int = self.creator_id
        self.text_id : int = interaction.channel.id if interaction and interaction.channel else 0
        self.member_ids : List[int] = member_ids

        self.duration : int = duration
        self.start_time : float = datetime.now().timestamp()
        self.last_reminder_time : float = datetime.now().timestamp()
        self.next_reminder_time : float = (datetime.now() + timedelta(seconds=duration)).timestamp()
        self.last_reminder_message_id : Optional[int] = None
        self.reminder_count : int = 0

        self.member_statuses: Dict[int, Dict[str, Any]] = {member_id : {MemberStatusKey.STATUS.value : MemberStatus.PRESENT.value, MemberStatusKey.ABSENCES.value : 0} for member_id in self.member_ids}

        self.max_members = settings.max_members
        self.max_absences = settings.max_absences
        self.max_breaks = settings.max_breaks

        # Other stuff, not stored in Database
        self.cog : CheckinCog = cog
        self.db : DBHandler = db
        self.guild : Optional[discord.Guild] = interaction.guild if interaction else None
        self.end_session_event = asyncio.Event()

        logger.debug("Check-in session created with duration: %s seconds", duration)

    ## Helper Function - Generate Session ID
    def generate_session_id(self):
        return str(uuid.uuid4())  # Generates a random unique session ID


    ## Session Management Function - Setup Checkin Resources
    async def setup_checkin_resources(self):
        try:
            session_data = {
                "session_id": self.session_id,
                "guild_id": self.guild_id,
                "name": self.name,
                "creator_id": self.creator_id,
                "owner_id": self.owner_id,
                "text_id": self.text_id,
                "duration": self.duration,
                "start_time": self.start_time,
                "last_reminder_time": self.last_reminder_time,
                "next_reminder_time": self.next_reminder_time,
                "reminder_count": self.reminder_count,
                "last_reminder_message_id": self.last_reminder_message_id,
                "active": 1  # Active sessions are marked as 1 (True)
            }

            # Save the check-in session to the database
            await self.db.save_checkin_session(session_data)
            logger.info(f"Check-in session {self.name} with ID {self.session_id} saved to the database.")

            # Save members' data to the database
            for member_id, status_data in self.member_statuses.items():
                await self.db.add_or_update_checkin_member(
                    self.session_id,
                    member_id,
                    status_data[MemberStatusKey.STATUS.value],
                    status_data[MemberStatusKey.ABSENCES.value]
                )
            logger.info(f"Members' statuses for session {self.session_id} saved to the database.")

        except Exception as e:
            logger.error(f"Failed to setup check-in resources: {str(e)}")
            raise


    """Attendance Functions"""

    ## Attendance Function - Increment Reminder Count
    def increment_reminder(self) -> None:
        self.reminder_count += 1
        asyncio.create_task(self.db.update_checkin_session({
        "session_id": self.session_id,
        "reminder_count": self.reminder_count,
        "last_reminder_message_id": self.last_reminder_message_id,
        "active": 1
        }))
        logger.debug(f"Incremented reminder count to: {self.reminder_count}")


    ## Attendance Function - Move People to Absent
    async def update_member_statuses(self):
        """
        Update member statuses at the end of each reminder cycle.
        Move all present members to absent.
        Increment absences for absent members, and mark those who exceed max absences as exited.
        """
        try:
            for member_id, status_info in self.member_statuses.items():
                if status_info[MemberStatusKey.STATUS.value] == MemberStatus.PRESENT.value:
                    # Move present members to absent and absence is set to 0
                    self.member_statuses[member_id][MemberStatusKey.STATUS.value] = MemberStatus.ABSENT.value
                    self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] = 1
                    logger.debug(f"Member {member_id} moved to absent and started their absence counter from 1")

                elif status_info[MemberStatusKey.STATUS.value] == MemberStatus.ABSENT.value:
                    # Increment absence count
                    self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] += 1
                    logger.debug(f"Incremented absences for member {member_id}: {self.member_statuses[member_id][MemberStatusKey.ABSENCES.value]} absences.")

                    # Remove members who exceed max absences and mark them as exited
                    if self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] >= self.max_absences:
                        self.member_statuses[member_id][MemberStatusKey.STATUS.value] = MemberStatus.EXITED.value
                        self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] = 0
                        self.member_ids.remove(member_id)
                        logger.info(f"Member {member_id} exceeded max absences. Status set to exited.")

                elif status_info[MemberStatusKey.STATUS.value] == MemberStatus.BREAK.value:
                    # Using the absence counter for breaks as well
                    self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] += 1
                    logger.debug(f"Incremented absences (For Break) for member {member_id}: {self.member_statuses[member_id][MemberStatusKey.ABSENCES.value]} absences.")

                    # Remove members who exceed max breaks and move them to present:
                    if self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] >= self.max_breaks:
                        self.member_statuses[member_id][MemberStatusKey.STATUS.value] = MemberStatus.PRESENT.value
                        self.member_statuses[member_id][MemberStatusKey.ABSENCES.value] = 0
                        logger.info(f"Member {member_id} exceeded max breaks. Status set to present.")

            # Update member statuses in the database
            for member_id, status_info in self.member_statuses.items():
                await self.db.add_or_update_checkin_member(
                    self.session_id,
                    member_id,
                    status_info[MemberStatusKey.STATUS.value],
                    status_info[MemberStatusKey.ABSENCES.value]
                )
            logger.debug(f"Updated member statuses in the database for session {self.session_id}.")

        except Exception as e:
            logger.error(f"Failed to update member statuses: {str(e)}")



    """Message Functions"""

    ## Embed Function - Create Embed
    def create_embed(self, initial: bool = False) -> discord.Embed:
        try:
            if not self.guild:
                return discord.Embed(title="Error", description="Guild not found for session.", color=discord.Color.red())

            def get_mention(m_id: int) -> str:
                assert self.guild is not None
                m = self.guild.get_member(m_id)
                return m.mention if m else f"<@{m_id}>"

            member_mentions = [get_mention(mid) for mid in self.member_ids]
            present_mentions = [get_mention(mid) for mid, status in self.member_statuses.items() if status.get(MemberStatusKey.STATUS.value) == MemberStatus.PRESENT.value]
            absent_ids = [mid for mid, status in self.member_statuses.items() if status.get(MemberStatusKey.STATUS.value) == MemberStatus.ABSENT.value]
            break_ids = [mid for mid, status in self.member_statuses.items() if status.get(MemberStatusKey.STATUS.value) == MemberStatus.BREAK.value]
            exited_mentions = [get_mention(mid) for mid, status in self.member_statuses.items() if status.get(MemberStatusKey.STATUS.value) == MemberStatus.EXITED.value]

            owner = self.guild.get_member(self.owner_id)
            owner_name = owner.display_name if owner else f"User {self.owner_id}"

            # Create the embed for the session
            embed = discord.Embed(
                title="Let's get started!" if initial else random.choice(CheckinSession.prompt_messages),
                color=discord.Color.blue(),
                description=f"Reminder No: {self.reminder_count}"
            )
            embed.set_author(name=f"{self.name}")
            # Add Field - Show Time started since
            embed.add_field(name="Check-in Started", value=f"<t:{int(self.start_time)}:R>", inline=True)
            # Add Field - Duration of reminders
            embed.add_field(name="Duration", value=f"{parse_seconds_to_hms(self.duration)}", inline=True)
            # Instructions
            instructions : str = "Click on Break to start a break. You won't be pinged.\nTo get back into the session, click on \\`Present\\` or \\`Join\\`."
            embed.add_field(name="How to Use", value=instructions, inline=False)
            # Add Field - List of Members
            embed.add_field(name="Members in the Session", value=", ".join(member_mentions), inline=False)

            # Present
            embed.add_field(
                name="Present",
                value="\n".join(present_mentions) or "No one yet!",
                inline=True
            )

            # Absent
            absent_members_str = [
                f"{get_mention(mid)} ({self.member_statuses.get(mid, {}).get(MemberStatusKey.ABSENCES.value, 0)} Absences)"
                if int(self.member_statuses.get(mid, {}).get(MemberStatusKey.ABSENCES.value, 0)) >= self.max_absences - 1
                else get_mention(mid)
                for mid in absent_ids
            ]
            embed.add_field(name="Absent", value="\n".join(absent_members_str) or "Everyone is Present!", inline=True)

            # Break
            break_members_str = [
                f"{get_mention(mid)} ({self.member_statuses.get(mid, {}).get(MemberStatusKey.ABSENCES.value, 0)} Breaks)"
                if int(self.member_statuses.get(mid, {}).get(MemberStatusKey.ABSENCES.value, 0)) >= self.max_breaks - 1
                else get_mention(mid)
                for mid in break_ids
            ]
            embed.add_field(
                name="On a Break",
                value="\n".join(break_members_str) or "Everyone is working!",
                inline=True
            )

            # Exited/Dropped
            embed.add_field(
                name="Exited/Dropped",
                value="\n".join(exited_mentions) or "None",
                inline=True
            )

            # Add Footer - Owner
            embed.set_footer(text=f"Owner: {owner_name}")

            return embed
        except Exception as e:
            logger.error(f"Failed to create embed for session {self.session_id}: {str(e)}")
            return discord.Embed(title="Error", description="An error occurred while creating the embed.", color=discord.Color.red())


    ## Embed Function - Update Embed
    async def update_embed(self) -> None:
        # Update the message embed after any interaction.
        try:
            if not self.guild:
                return
            channel = self.guild.get_channel(self.text_id)
            if self.last_reminder_message_id and isinstance(channel, discord.TextChannel):
                reminder_message : discord.Message = await channel.fetch_message(self.last_reminder_message_id)
                embed = self.create_embed()
                await reminder_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update embed for session {self.session_id}: {str(e)}")


    ## Message Function - Disable Previous Buttons
    async def disable_previous_buttons(self) -> None:
        try:
            if not self.guild:
                return
            channel = self.guild.get_channel(self.text_id)
            if self.last_reminder_message_id and isinstance(channel, discord.TextChannel):
                last_message = await channel.fetch_message(self.last_reminder_message_id)
                new_view = View.from_message(last_message)
                for item in new_view.children:
                    if isinstance(item, (Button, discord.ui.Select)):
                        item.disabled = True

                await last_message.edit(view=new_view)
                logger.info("Disabled buttons in the previous reminder message.")
        except discord.NotFound:
            logger.warning(f"Previous reminder message not found (ID: {self.last_reminder_message_id}).")
        except discord.HTTPException as e:
            logger.error(f"Failed to disable buttons in previous reminder message: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error disabling buttons: {str(e)}")


    ## Message Function - Send Reminder Message (along with Initial)
    async def send_reminder_message(self, initial : bool = False) -> None:
        try:
            if not self.guild:
                return
            channel = self.guild.get_channel(self.text_id)
            if not isinstance(channel, discord.TextChannel):
                return
            ping_mentions: List[str] = []
            for member_id in self.member_statuses.keys():
                status_val = self.member_statuses[member_id][MemberStatusKey.STATUS.value]
                if status_val in (MemberStatus.PRESENT.value, MemberStatus.ABSENT.value):
                    member = self.guild.get_member(member_id)
                    ping_mentions.append(member.mention if member else f"<@{member_id}>")

            members_mention_msg = ", ".join(ping_mentions)

            if initial:
                initial_embed = self.create_embed(initial=True)
                initial_button_view = self.create_buttons(initial=True)
                initial_message = await channel.send(content=members_mention_msg, embed=initial_embed, view=initial_button_view)
                self.last_reminder_message_id = initial_message.id
                logger.info(f"Initial message sent for session name: {self.name} and ID: {self.session_id}.")

            else:
                reminder_embed = self.create_embed()
                reminder_button_view = self.create_buttons()
                reminder_message = await channel.send(content=members_mention_msg, embed=reminder_embed, view=reminder_button_view)
                self.last_reminder_message_id = reminder_message.id
                logger.info(f"Reminder message sent for session name: {self.name} and ID: {self.session_id}.")


        except Exception as e:
            logger.error(f"Failed to send reminder message for session {self.session_id}: {str(e)}")


    ## Message Function - Send Reminder Message
    async def run_checkin_reminders(self):
        try:
            while self.session_id in self.cog.active_sessions:

                # Calculate how much time to sleep until the next reminder
                now = datetime.now().timestamp()
                time_until_next_reminder = self.next_reminder_time - now

                sleep_task = asyncio.create_task(asyncio.sleep(time_until_next_reminder))
                end_event_task = asyncio.create_task(self.end_session_event.wait())

                if time_until_next_reminder > 0:
                    done, pending = await asyncio.wait([sleep_task, end_event_task], return_when=asyncio.FIRST_COMPLETED)

                # If the session has ended, break out of the loop
                if self.end_session_event.is_set():
                    logger.info(f"Session {self.name} has been ended. Stopping reminders.")
                    return

                # 1. Disable buttons of previous message
                if self.last_reminder_message_id:
                    await self.disable_previous_buttons()

                # 2. Update Member statuses
                await self.update_member_statuses()

                # 3. If no members are left, the session is over
                if not self.member_ids:
                    embed = discord.Embed(
                        title=f"Check-in Session: {self.name} ended",
                        description="No more members are left in the session.",
                        color=discord.Color.red()
                    )
                    if self.guild:
                        channel = self.guild.get_channel(self.text_id)
                        if isinstance(channel, discord.TextChannel):
                            await channel.send(embed=embed)
                    logger.info(f"Session {self.name} and {self.session_id} ended due to no remaining members.")
                    await self.clear_session_data()
                    return                  # Exit the loop

                # 4. Send next reminder message
                await self.send_reminder_message()

                # 5. Update the reminder time
                self.last_reminder_time = datetime.now().timestamp()
                self.next_reminder_time = self.last_reminder_time + self.duration

                # 6. Increment reminder count
                self.increment_reminder()

                # Update session in the db
                await self.db.update_checkin_session({
                    "session_id": self.session_id,
                    "last_reminder_time": self.last_reminder_time,
                    "next_reminder_time": self.next_reminder_time,
                    "reminder_count": self.reminder_count
                })


                logger.info(f"Reminder {self.reminder_count} sent with updated members.")
        except Exception as e:
            logger.error(f"Failed to send reminder message for session {self.session_id}: {str(e)}")



    """Button & Callback Functions"""


    ## Button Function - Create Buttons
    def create_buttons(self, initial=False) -> discord.ui.View:
        try:
            # Create the buttons, Row 1
            present_button : Button[Any] = Button(label='Present', style=discord.ButtonStyle.green, row= 1)
            break_button : Button[Any] = Button(label='Break', style=discord.ButtonStyle.blurple, row= 1)
            join_button : Button[Any] = Button(label='Join', style=discord.ButtonStyle.blurple, row= 1)
            leave_button : Button[Any] = Button(label='Leave', style=discord.ButtonStyle.grey, row= 1)
            # Row 2
            end_button : Button[Any] = Button(label='End', style=discord.ButtonStyle.red, row= 2)
            change_owner_button : Button[Any] = Button(label='Change Owner', style=discord.ButtonStyle.grey, row= 2)

            # Assign callbacks
            present_button.callback = self.mark_present_callback  # type: ignore[method-assign]
            break_button.callback = self.start_break_callback  # type: ignore[method-assign]
            join_button.callback = self.join_session_callback  # type: ignore[method-assign]
            leave_button.callback = self.leave_session_callback  # type: ignore[method-assign]
            # Row 2
            end_button.callback = self.end_session_callback  # type: ignore[method-assign]
            change_owner_button.callback = self.change_owner_callback  # type: ignore[method-assign]

            # Create View
            view = discord.ui.View()
            # Row 1
            if not initial:
                view.add_item(present_button)
                view.add_item(break_button)
            view.add_item(join_button)
            view.add_item(leave_button)
            # Row 2
            view.add_item(end_button)
            view.add_item(change_owner_button)

            return view
        except Exception as e:
            logger.error(f"Failed to create buttons: {str(e)}")
            return discord.ui.View()


    ## Button Function - Mark Present
    @CheckinGuildSettings.is_member
    async def mark_present_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"Mark present initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id

            # If user is not already a member, or if they have left the session
            if (user_id not in self.member_statuses) or (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.EXITED.value):
                await interaction.followup.send(f"You are not part of this session. {interaction.user.mention}", ephemeral=True)
                return
            # If user is already marked as present
            if (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.PRESENT.value):
                await interaction.followup.send(f"You are already marked as present. {interaction.user.mention}", ephemeral=True)
                return

            # If member is in break, change message
            if (user_id in self.member_statuses and self.member_statuses.get(user_id,{}).get(MemberStatusKey.STATUS.value)== MemberStatus.BREAK.value):
                await interaction.followup.send(f"Welcome back! Let's start working!. {interaction.user.mention}.", ephemeral=True)

            # If user is absent, or on a break, the update happens
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.PRESENT.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 0
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, str(self.member_statuses[user_id][MemberStatusKey.STATUS.value]), int(self.member_statuses[user_id][MemberStatusKey.ABSENCES.value]))

            await interaction.followup.send(f"You are marked as present. {interaction.user.mention}", ephemeral=True)
            await self.update_embed()

        except Exception as e:
            logger.error(f"Failed to mark user: {interaction.user.display_name} present: {str(e)}")
            await interaction.followup.send(f"Failed to mark present for user {interaction.user.mention}.", ephemeral=True)


    ## Button Function - Start Break
    @CheckinGuildSettings.is_member
    async def start_break_callback(self, interaction : discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"Start break initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id

            # If user is not already a member, or if they have left the session
            if (user_id not in self.member_statuses) or (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.EXITED.value):
                await interaction.followup.send(f"You are not part of this session. {interaction.user.mention}", ephemeral=True)
                return
            # If user is already on a break
            if (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.BREAK.value):
                await interaction.followup.send(f"You are already on a break. {interaction.user.mention}", ephemeral=True)
                return

            # If user is present, or on absent, the update happens
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.BREAK.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 1
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, str(self.member_statuses[user_id][MemberStatusKey.STATUS.value]), int(self.member_statuses[user_id][MemberStatusKey.ABSENCES.value]))

            await interaction.followup.send(f"Your break has started! Take a deep breath! {interaction.user.mention}", ephemeral=True)
            await self.update_embed()

        except Exception as e:
            logger.error(f"Failed to mark user: {interaction.user.display_name} present: {str(e)}")
            await interaction.followup.send(f"Failed to mark present for user {interaction.user.mention}.", ephemeral=True)


    ## Button Function - Join Session
    async def join_session_callback(self, interaction : discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"Join session initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id
            # If Members are present or absent, return
            if (user_id in self.member_statuses
                and
                (self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value)== MemberStatus.PRESENT.value
                or
                self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value)== MemberStatus.ABSENT.value
                )
                ):
                await interaction.followup.send("You are already in the session.", ephemeral=True)
                return

            # If member is in break, change message
            if (user_id in self.member_statuses and self.member_statuses.get(user_id,{}).get(MemberStatusKey.STATUS.value)== MemberStatus.BREAK.value):
                await interaction.followup.send(f"Welcome back! Let's start working!. {interaction.user.mention}.", ephemeral=True)

            # If user is not in the members_statuses, or has exited the session
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.PRESENT.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 0
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]


            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, str(self.member_statuses[user_id][MemberStatusKey.STATUS.value]), int(self.member_statuses[user_id][MemberStatusKey.ABSENCES.value]))

            await interaction.followup.send("You have joined the session.", ephemeral=True)
            await self.update_embed()

        except Exception as e:
            logger.error(f"Failed to join session for user: {interaction.user.display_name}: {str(e)}")
            await interaction.followup.send(f"Failed to join session. {str(e)}", ephemeral=True)


    ## Button Function - Leave Session
    @CheckinGuildSettings.is_member
    async def leave_session_callback(self, interaction : discord.Interaction):
        # Remove user from the session and update absent and members lists
        try:
            await interaction.response.defer()
            logger.info(f"Leave session initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id

            # If user is not already a member, or if they have left the session
            if (user_id not in self.member_statuses) or (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.EXITED.value):
                await interaction.followup.send(f"You are already not in this session. {interaction.user.mention}", ephemeral=True)
                return

            # If user is present, absent, or on a break
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.EXITED.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 0
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]


            # Update DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, str(self.member_statuses[user_id][MemberStatusKey.STATUS.value]), int(self.member_statuses[user_id][MemberStatusKey.ABSENCES.value]))

            await interaction.followup.send(f"You have left the session. {interaction.user.mention}", ephemeral=True)
            await self.update_embed()

        except Exception as e:
            logger.error(f"Failed to leave session for user: {interaction.user.display_name}: {str(e)}")
            await interaction.followup.send(f"Failed to leave session. {str(e)}", ephemeral=True)


    ## Button Function - Change Owner
    @CheckinGuildSettings.is_owner
    async def change_owner_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"Ownership change for session name: {self.name} initiated by {interaction.user.display_name}. Session ID: {self.session_id}")

            if not self.guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            user_id = interaction.user.id
            menu_msg : Optional[discord.Message] = None
            is_authorized = user_id in (self.owner_id, self.creator_id) or await check_manager(interaction)
            if not is_authorized:
                await interaction.followup.send(f"You are NOT authorized to change the owner of this session {interaction.user.mention}. Exiting...", ephemeral=True)
                return

            await interaction.followup.send(f"Authorization verified for {interaction.user.mention}. Starting change ownership...", ephemeral=True)

            rest_members_list = [member_id for member_id in self.member_ids if member_id != self.owner_id]

            if not rest_members_list:
                await interaction.followup.send("There are no other members in this session to change owner to. Try again.", ephemeral=True)
                return

            new_owner_options : List[discord.SelectOption] = []
            for member_id in rest_members_list:
                m = self.guild.get_member(member_id)
                disp_name = m.display_name if m else f"User {member_id}"
                new_owner_options.append(discord.SelectOption(label=disp_name, value=str(member_id)))

            new_owner_select : Select[Any] = Select(placeholder= "Select a new owner from the list.",
                                                         min_values= 1,
                                                         max_values= 1,
                                                         options = new_owner_options,
                                                         )

            # Callback Function for New Owner Select Menu
            async def new_owner_callback(select_interaction : discord.Interaction):
                await select_interaction.response.defer(ephemeral=True)
                assert self.guild is not None
                selected_user_id = int(new_owner_select.values[0])
                selected_user = self.guild.get_member(selected_user_id)
                selected_mention = selected_user.mention if selected_user else f"<@{selected_user_id}>"

                old_owner_id = self.owner_id
                old_owner = self.guild.get_member(old_owner_id)
                old_mention = old_owner.mention if old_owner else f"<@{old_owner_id}>"

                if selected_user_id not in self.member_ids:
                    logger.error(f"The selected member with id {selected_user_id} is not in the Session named {self.name}. Exiting...")
                    await select_interaction.followup.send(f"The selected member {selected_mention} is not a part of the session. Try again...")
                    return

                self.owner_id = selected_user_id
                if menu_msg:
                    await menu_msg.edit(content=f"Ownership has been transferred to {selected_mention} from previous owner {old_mention}.", view=None)
                await self.update_embed()

            new_owner_select.callback = new_owner_callback  # type: ignore[method-assign,assignment]

            new_owner_view = View()
            new_owner_view.add_item(new_owner_select)

            if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                menu_msg = await interaction.channel.send("Please select the new owner from the list:", view=new_owner_view)

        except Exception as e:
            logger.error(f"Failed to change owner by {interaction.user.mention} in session Name {self.name} with ID {self.session_id}. {str(e)}")
            await interaction.followup.send(f"Failed to change the owner by {interaction.user.mention}.", ephemeral=True)


    ## Button Function - End Session
    @CheckinGuildSettings.is_owner
    async def end_session_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"End session initiated by {interaction.user.display_name} for session {self.session_id}.")

            owner_member = self.guild.get_member(self.owner_id) if self.guild else None
            owner_str = owner_member.display_name if owner_member else f"User {self.owner_id}"

            can_end_session = self.can_end(interaction.user.id) or interaction.user.id == self.owner_id or await check_manager(interaction)
            if not can_end_session:
                await interaction.followup.send("Only the session owner, creator, or server managers/moderators can end the session.", ephemeral=True)
                return

            await self.disable_previous_buttons()

            embed = discord.Embed(
                title=f"Check-in Session: {self.name} Ended",
                description=f"The session has been manually ended by {interaction.user.display_name}.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Session owner: {owner_str}")

            await interaction.followup.send(embed=embed)

            # Mark the session as inactive in the DB
            await self.db.update_checkin_session({
                "session_id": self.session_id,
                "reminder_count": self.reminder_count,
                "last_reminder_message_id": self.last_reminder_message_id,
                "active": 0
            })

            # Trigger the end of event to stop reminders
            self.end_session_event.set()
            await self.clear_session_data()
            logger.info(f"Check-in session {self.session_id} successfully ended by {interaction.user.display_name}.")
            await interaction.followup.send("Check-in session has been manually ended.", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed in end_session_callback for user: {interaction.user.display_name}: {str(e)}")
            await interaction.followup.send(f"Failed to end session. {str(e)}", ephemeral=True)



    """End Session Helper Functions"""
    ## Helper Function - Can End
    def can_end(self, user_id : int):
        # Determine if the user can end the session.
        return user_id in (self.creator_id, self.owner_id)


    ## Helper Function - Clear Session Data
    async def clear_session_data(self):
        # Clear all session data explicitly to avoid any future interaction
        try:

            # Delete session and members data from the database first
            await self.db.delete_checkin_session(self.session_id)

            # Clear in-memory session data
            self.member_ids.clear()
            self.member_statuses.clear()
            self.last_reminder_message_id = None
            self.reminder_count = 0

            # Remove session from the active sessions list
            self.cog.active_sessions.pop(self.session_id, None)

            logger.debug(f"Session data for session name {self.name} and Session ID: {self.session_id} cleared successfully.")
        except Exception as e:
            logger.error(f"Failed to clear session data for session {self.session_id}: {str(e)}")




class CheckinCog(commands.Cog):

    def __init__(self, bot: Any):
        self.bot = bot
        self.db : DBHandler = bot.db
        self.active_sessions : Dict[str, CheckinSession] = {}
        self.guild_settings : Dict[int, CheckinGuildSettings] = {}
        logger.debug("Check-in Cog initialized.")

    async def cog_load(self):
        await self.load_active_sessions_from_db()
        logger.info(f"Loaded {len(self.active_sessions)} active sessions from the database.")



    ## Function - Load Active Sessions from DB
    async def load_active_sessions_from_db(self):
        """
        Load all active check-in sessions from the database and start their reminder loops.
        """
        try:
            # Fetch active sessions from the database
            active_sessions = await self.db.fetch_active_checkin_sessions()

            for session_data in active_sessions:
                session_id = session_data["session_id"]
                # Fetch member statuses from the database
                member_statuses = await self.db.fetch_checkin_members(session_id)

                # Recreate member_statuses dict
                member_status_dict = {
                    member['member_id']: {
                        MemberStatusKey.STATUS.value: MemberStatus(member[MemberStatusKey.STATUS.value]),
                        MemberStatusKey.ABSENCES.value: member[MemberStatusKey.ABSENCES.value]
                    }
                    for member in member_statuses
                }

                guild_id = session_data["guild_id"]
                if guild_id not in self.guild_settings:
                    self.bot.get_guild(guild_id)
                    self.guild_settings[guild_id] = CheckinGuildSettings(None)
                this_guild_settings = self.guild_settings[guild_id]

                # Create a new CheckinSession object
                session = CheckinSession(
                    db=self.db,
                    cog=self,
                    interaction=None,  # Interaction is not available during bot restart
                    name=session_data["name"],
                    member_ids=[m['member_id'] for m in member_statuses],
                    duration=int(session_data["duration"]),
                    settings=this_guild_settings
                )

                # Set session attributes
                session.session_id = session_data["session_id"]
                session.guild_id = session_data["guild_id"]
                session.creator_id = session_data["creator_id"]
                session.text_id = session_data["text_id"] if "text_id" in session_data else session_data.get("text_channel_id", 0)
                session.start_time = float(session_data["start_time"])
                session.reminder_count = session_data["reminder_count"]
                session.last_reminder_time = float(session_data["last_reminder_time"])
                session.next_reminder_time = float(session_data["next_reminder_time"])
                session.member_statuses = member_status_dict

                # Add the session to active_sessions and start reminder loop
                self.active_sessions[session.session_id] = session

                # Staggered start for reminders (random small delay in background task)
                async def start_staggered_reminder(s: CheckinSession) -> None:
                    delay = random.uniform(5, 30)
                    await asyncio.sleep(delay)
                    await s.run_checkin_reminders()

                asyncio.create_task(start_staggered_reminder(session))

                logger.info(f"Loaded check-in session with name: {session.name} and ID: {session.session_id} from the database.\n And reminder loop started.")

            logger.info(f"Loaded {len(active_sessions)} active sessions from the database.")

        except Exception as e:
            logger.error(f"Failed to load active sessions from database: {str(e)}")



    """Cog Commands"""

    ## Command - /checkin
    @app_commands.command(name='checkin', description='Starts a check-in session with specified duration and mentions. This is the true version.')
    @app_commands.describe(name= 'Name of the Checkin Session', duration='The duration of the check-in session in format \'2d 14h 25m 30s\'', mentions='The users/roles to be included in the check-in session.')
    @CheckinGuildSettings.check_user_groups
    @CheckinGuildSettings.checkin_command_permissions
    async def start_checkin(self, interaction : discord.Interaction, name: str, mentions: str, duration: str):
        await interaction.response.defer()
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        # Parse the duration and mentions
        duration_seconds = parse_duration(duration)
        if duration_seconds is None:
            await interaction.followup.send("Invalid duration format.", ephemeral=True)
            return

        member_ids : List[int] = parse_mentions(interaction, mentions)

        if interaction.guild.id not in self.guild_settings:
            self.guild_settings[interaction.guild.id] = CheckinGuildSettings(interaction)

         # Validate parameters before proceeding
        if not await validate_parameters(
            interaction = interaction,
            name = name,
            member_ids = member_ids,
            duration= duration,
            max_members=self.guild_settings[interaction.guild.id].max_members,
        ):
            logger.error(f"Checkin Session: Validation failed for {name} by user {interaction.user.display_name}")
            return          # Exit if validation fails

        # Create a new session and save it
        try:
            session = CheckinSession(
                db=self.bot.db,
                cog=self,
                interaction=interaction,
                name=name,
                member_ids=member_ids,
                duration=duration_seconds,
                settings=self.guild_settings[interaction.guild.id]
            )
            self.active_sessions[session.session_id] = session  # Store session by its ID
            channel_id = interaction.channel.id if interaction.channel else 0
            logger.info(f"Check-in session with ID {session.session_id} started by {interaction.user.display_name} in channel {channel_id}.")

            # Send the initial message with buttons
            await session.setup_checkin_resources()
            await session.send_reminder_message(initial=True)
            asyncio.create_task(session.run_checkin_reminders())
        except Exception as e:
            logger.error(f"Error starting check-in session: {str(e)}")
            await interaction.followup.send("An error occurred while starting the check-in session.", ephemeral=True)


    ## Command - /setup_checkin
    @app_commands.command(name="settings_checkin", description="Changes the Settings of Checkin Module")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(max_members = "Maximum members allowed in a Checkin Session",
                           min_duration = "Minimum Duration Allowed",
                           max_duration = "Maximum Duration Allowed",
                           max_absences = "Maximum absences allowed before a user is kicked",
                           max_breaks = "Maximum breaks allowed before a user is brought back to Checkin Session",
                           max_user_sessions = "Maximum sessions a user is allowed to be in",
                           permission_mode = "Set permission mode: ALLOW or DENY"
                        )
    async def settings_checkin(
        self,
        interaction: discord.Interaction,
        max_members : int = 10,
        min_duration : int = 20,
        max_duration : int = 7200,
        max_absences : int = 3,
        max_breaks : int = 3,
        max_user_sessions : int = 5,
        permission_mode : str = "ALLOW"
    ):

        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        if not await check_manager(interaction):
            await interaction.followup.send("You do not have permission to manage check-in settings.", ephemeral=True)
            return

        guild_id = interaction.guild.id

        try:
            if guild_id not in self.guild_settings:
                self.guild_settings[guild_id] = CheckinGuildSettings(
                    interaction = interaction,
                    max_members=max_members,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    max_absences=max_absences,
                    max_breaks=max_breaks,
                    max_user_sessions=max_user_sessions,
                    permission_mode = permission_mode
                )
            else:
                guild_settings : CheckinGuildSettings = self.guild_settings[guild_id]
                guild_settings.max_members = max_members
                guild_settings.min_duration = min_duration
                guild_settings.max_duration = max_duration
                guild_settings.max_absences = max_absences
                guild_settings.max_breaks = max_breaks
                guild_settings.max_user_sessions = max_user_sessions
                guild_settings.permission_mode = permission_mode

            # Optional - Save to database

            '''
            await self.bot.db.update_checkin_settings(
                guild_id = guild_id,
                max_members = max_members,
                min_duration = min_duration,
                max_duration = max_duration,
                max_absences = max_absences,
                max_breaks = max_breaks,
                max_user_sessions = max_user_sessions
            )
            '''

            # Provide feedback to the user
            response = (
                f"Check-in settings updated for this server:\n\n"
                f"**Max Members**: {max_members}\n"
                f"**Min Duration**: {min_duration} seconds\n"
                f"**Max Duration**: {max_duration} seconds\n"
                f"**Max Absences**: {max_absences}\n"
                f"**Max Breaks**: {max_breaks}\n"
                f"**Max User Sessions**: {max_user_sessions}"
            )

            await interaction.followup.send(response, ephemeral=True)
            logger.info(f"Updated Check-in settings for guild {guild_id} by user {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error updating check-in settings: {str(e)}")
            await interaction.followup.send("An error occurred while updating the check-in settings.", ephemeral=True)



"""Setup Bot"""
async def setup(bot):
    await bot.add_cog(CheckinCog(bot))
    logger.info("CheckinCog loaded successfully.")
