import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from utils import parse_duration, parse_mentions, parse_seconds_to_hms, validate_parameters
import asyncio
import logging
import random
import uuid
import sys
from discord.ui import Button, View, Select
from typing import List, Dict, Optional
from database import DBHandler
from enum import Enum
from .manager import Manager
import json
from functools import wraps

# Setting up basic configuration for logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
current_namespace = sys.modules[__name__].__name__.split('.')[-1]


## Enums
# Enum to regularize the status of member_statuses
class MemberStatus(Enum):
    PRESENT = "present"
    ABSENT = "absent"
    EXITED = "exited"
    BREAK = "break"

# Enum regularize the keys of member_statuses
class MemberStatusKey(Enum):
    STATUS = "status"
    ABSENCES = "absences"



### CHECKIN SETTINGS CLASS
class CheckinGuildSettings:
    def __init__(self, interaction : discord.Interaction, max_members = 10, min_duration = 20, max_duration = 7200, max_absences = 3, max_breaks = 3, max_user_sessions = 5, permission_mode = "ALLOW"):
        self.guild = interaction.guild
        self.guild_id = interaction.guild.id
        # Initialize all settings for the guild here
        self.max_members = max_members
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_absences = max_absences
        self.max_breaks = max_breaks
        self.max_user_sessions = max_user_sessions

        # Permissions-related settings
        self.permission_mode = permission_mode
        self.whitelist_users: List[int] = []
        self.blacklist_users: List[int] = []
        self.whitelist_channels: List[int] = []
        self.blacklist_channels: List[int] = []
        self.whitelist_roles: List[int] = []
        self.blacklist_roles: List[int] = []

    def has_permission(self, user_id: int, channel_id: int, role_ids: List[int]) -> bool:
        """Checks if a user has permission based on the guild's settings."""
        logger.info(f"Checking permissions for user {user_id} in channel {channel_id} in guild {self.guild_id}...")

        if self.permission_mode == "ALLOW":
            if user_id in self.blacklist_users or channel_id in self.blacklist_channels:
                return False
            if self.whitelist_users and user_id not in self.whitelist_users:
                return False
            if self.whitelist_channels and channel_id not in self.whitelist_channels:
                return False
            if self.whitelist_roles:
                if not set(role_ids).intersection(self.whitelist_roles):
                    return False
        else:
            if user_id in self.whitelist_users or channel_id in self.whitelist_channels:
                return True
            if self.blacklist_users and user_id in self.blacklist_users:
                return False
            if self.blacklist_channels and channel_id in self.blacklist_channels:
                return False
            if self.blacklist_roles:
                if set(role_ids).intersection(self.blacklist_roles):
                    return False
        return True

    ### --- DECORATORS --- ###
    
    ## Check - Member
    def is_member(func):
        """Decorator to check if a user is a member of the session."""
        @wraps(func)
        async def wrapper(session : 'CheckinSession', interaction: discord.Interaction, *args, **kwargs):
            if interaction.user.id not in session.member_ids:
                await interaction.response.send_message("You are not a member of this session.", ephemeral=True)
                return
            return await func(session, interaction, *args, **kwargs)
        return wrapper

    ## Check - Owner
    def is_owner(func):
        """Decorator to check if a user is the owner of the session."""
        @wraps(func)
        async def wrapper(session : 'CheckinSession', interaction: discord.Interaction, *args, **kwargs):
            if interaction.user.id != session.owner_id:
                await interaction.response.send_message("You are not the owner of this session.", ephemeral=True)
                return
            return await func(session, interaction, *args, **kwargs)
        return wrapper
    
    # Check - /checkin Command Permissions
    def checkin_command_permissions(func):
        """Decorator to check permissions for the `/checkin` command."""
        @wraps(func)
        async def wrapper(cog : 'CheckinCog', interaction: discord.Interaction, *args, **kwargs):
            guild_settings : CheckinGuildSettings = cog.guild_settings[interaction.guild.id] if cog.guild_settings else None
            # role_ids = [role.id for role in interaction.user.roles]
            # if not guild_settings or not guild_settings.has_permission(interaction.user.id, interaction.channel.id, role_ids):
            #     await interaction.response.send_message("You don't have permission to use this command here.", ephemeral=True)
            #     return
            return await func(cog, interaction, *args, **kwargs)
        return wrapper
    
    ## Check - Max User Groups
    def check_user_groups(func):
        """Decorator to check if a user is within the limit of allowed sessions/groups."""
        @wraps(func)
        async def wrapper(cog : 'CheckinCog', interaction: discord.Interaction, *args, **kwargs):

            guild_settings : CheckinGuildSettings = cog.guild_settings[interaction.guild.id] if cog.guild_settings else None
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
            "How's your progress?",
            "Any updates on your task?",
            "What have you achieved so far?",
            "Let's hear about your current status!",
            "How are things going?",
            "How is your work progressing?",
            "What have you done since the last check-in?",
            "What's your status?",
            "Any progress to report?"
        ]

    def __init__(self, db : DBHandler, cog : 'CheckinCog', interaction : discord.Interaction, name : str, member_ids: List[int], duration : int, settings: CheckinGuildSettings):

        # Critical Info first
        self.guild_id : int = interaction.guild.id
        self.name : str = name
        self.session_id : str = self.generate_session_id()
        self.creator_id : int = interaction.user.id
        self.owner_id : int = self.creator_id
        self.text_id : int = interaction.channel.id
        self.member_ids : List[int] = member_ids
        
        self.duration : int = duration
        self.start_time : float = datetime.now().timestamp()
        self.last_reminder_time : float = datetime.now().timestamp()
        self.next_reminder_time : float = (datetime.now() + timedelta(seconds=duration)).timestamp()
        self.last_reminder_message_id : int = None
        self.reminder_count : int = 0

        self.member_statuses = {member_id : {MemberStatusKey.STATUS.value : MemberStatus.PRESENT.value, MemberStatusKey.ABSENCES.value : 0} for member_id in self.member_ids}
                
        self.max_members = settings.max_members
        self.max_absences = settings.max_absences
        self.max_breaks = settings.max_breaks
        
        # Other stuff, not stored in Database
        self.cog : CheckinCog = cog
        self.db : DBHandler = db
        self.guild : discord.Guild = interaction.guild
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
    def create_embed(self, initial=False) -> discord.Embed:
        try:
            member_objs = [self.guild.get_member(member_id) for member_id in self.member_ids]
            present_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status[MemberStatusKey.STATUS.value] == MemberStatus.PRESENT.value]
            absent_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status[MemberStatusKey.STATUS.value] == MemberStatus.ABSENT.value]
            break_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status[MemberStatusKey.STATUS.value] == MemberStatus.BREAK.value]
            exited_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status[MemberStatusKey.STATUS.value] == MemberStatus.EXITED.value]
            owner = self.guild.get_member(self.owner_id)

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
            instructions : str = "Click on Break to start a break. You won't be pinged.\nTo get back into the session, click on \`Present\` or \`Join\`."
            embed.add_field(name="How to Use", value=instructions, inline=False)
            # Add Field - List of Members
            embed.add_field(name="Members in the Session", value=", ".join([member_obj.mention for member_obj in member_objs]), inline=False)

            # Present
            embed.add_field(
                name="Present",
                value="\n".join([present_obj.mention for present_obj in present_objs]) or "No one yet!",
                inline=True
            )

            # Absent
            absent_members_str = [
                f"{absent_obj.mention} ({self.member_statuses.get(absent_obj.id, {}).get(MemberStatusKey.ABSENCES.value, 0)} Absences)" if self.member_statuses[absent_obj.id][MemberStatusKey.ABSENCES.value] >= self.max_absences - 1 else absent_obj.mention
                for absent_obj in absent_objs
            ]
            embed.add_field(name="Absent", value="\n".join(absent_members_str) or "Everyone is Present!", inline=True)

            
            # Break
            break_members_str =[
                f"{break_obj.mention} ({self.member_statuses.get(break_obj.id, {}).get(MemberStatusKey.ABSENCES.value, 0)} Breaks)" if self.member_statuses[break_obj.id][MemberStatusKey.ABSENCES.value] >= self.max_breaks - 1 else break_obj.mention
                for break_obj in break_objs
            ] 
            embed.add_field(
                name="On a Break",
                value = "\n".join(break_members_str) or "Everyone is working!",
                inline=True
            )

            # Exited/Dropped
            embed.add_field(
                name="Exited/Dropped",
                value="\n".join([exited_obj.mention for exited_obj in exited_objs]) or "None",
                inline=True
            )

            # Add Footer - Owner
            embed.set_footer(text=f"Owner: {owner.display_name}")

            return embed
        except Exception as e:
            logger.error(f"Failed to create embed for session {self.session_id}: {str(e)}")
            return discord.Embed(title="Error", description="An error occurred while creating the embed.", color=discord.Color.red())


    ## Embed Function - Update Embed
    async def update_embed(self) -> None:
        # Update the message embed after any interaction. 
        try:
            if self.last_reminder_message_id:
                text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
                reminder_message : discord.Message = await text_channel.fetch_message(self.last_reminder_message_id)
                embed = self.create_embed()
                await reminder_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update embed for session {self.session_id}: {str(e)}")
    

    ## Message Function - Disable Previous Buttons    
    async def disable_previous_buttons(self) -> None:
        try:
            text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
            if self.last_reminder_message_id:
                last_message = await text_channel.fetch_message(self.last_reminder_message_id)
                new_view = View()

                for component in last_message.components:
                    for item in component.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True
                            new_view.add_item(item)

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
            text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
            ping_members : List[discord.Member] =   [self.guild.get_member(member_id)
                                                        for member_id in self.member_statuses.keys() 
                                                            if  ( #Fetch only members who are present or absent, break and exited members won't be pinged.
                                                                self.member_statuses[member_id][MemberStatusKey.STATUS.value] == MemberStatus.PRESENT.value
                                                                or 
                                                                self.member_statuses[member_id][MemberStatusKey.STATUS.value] == MemberStatus.ABSENT.value
                                                                )
                                                    ]
            members_mention_msg = ", ".join([ping_member.mention for ping_member in ping_members])
            
            if initial:
                initial_embed = self.create_embed(initial=True)
                initial_button_view = self.create_buttons(initial=True)
                initial_message = await text_channel.send(content=members_mention_msg,embed=initial_embed, view=initial_button_view)
                self.last_reminder_message_id = initial_message.id
                logger.info(f"Initial message sent for session name: {self.name} and ID: {self.session_id}.")
            
            else:
                reminder_embed = self.create_embed()
                reminder_button_view = self.create_buttons()
                reminder_message = await text_channel.send(content=members_mention_msg,embed=reminder_embed, view=reminder_button_view)
                self.last_reminder_message_id = reminder_message.id
                logger.info(f"Initial message sent for session name: {self.name} and ID: {self.session_id}.")


        except Exception as e:
            logger.error(f"Failed to send initial message for session {self.session_id}: {str(e)}")


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
                    text_channel : discord.TextChannel= self.guild.get_channel(self.text_id)
                    logger.info(f"Session {self.name} and {self.session_id} ended due to no remaining members.")
                    await text_channel.send(embed=embed)
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
            present_button : discord.Button = Button(label='Present', style=discord.ButtonStyle.green, row= 1)
            break_button : discord.Button = Button(label='Break', style=discord.ButtonStyle.blurple, row= 1)
            join_button : discord.Button = Button(label='Join', style=discord.ButtonStyle.blurple, row= 1)
            leave_button : discord.Button = Button(label='Leave', style=discord.ButtonStyle.grey, row= 1)
            # Row 2
            end_button : discord.Button = Button(label='End', style=discord.ButtonStyle.red, row= 2)
            change_owner_button : discord.Button = Button(label='Change Owner', style=discord.ButtonStyle.grey, row= 2)

            # Assign callbacks
            present_button.callback = self.mark_present_callback
            break_button.callback = self.start_break_callback
            join_button.callback = self.join_session_callback
            leave_button.callback = self.leave_session_callback
            # Row 2
            end_button.callback = self.end_session_callback
            change_owner_button.callback = self.change_owner_callback

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
                await interaction.response.send_message(f"You are not part of this session. {interaction.user.mention}", ephemeral=True)
                return
            # If user is already marked as present
            if (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.PRESENT.value):
                await interaction.response.send_message(f"You are already marked as present. {interaction.user.mention}", ephemeral=True)
                return
            
            # If member is in break, change message
            if (user_id in self.member_statuses and self.member_statuses.get(user_id,{}).get(MemberStatusKey.STATUS.value)== MemberStatus.BREAK.value):
                await interaction.followup.send(f"Welcome back! Let's start working!. {interaction.user.mention}.", ephemeral=True)
            
            # If user is absent, or on a break, the update happens
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.PRESENT.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 0
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, self.member_statuses[user_id][MemberStatusKey.STATUS.value], self.member_statuses[user_id][MemberStatusKey.ABSENCES.value])

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
                await interaction.response.send_message(f"You are not part of this session. {interaction.user.mention}", ephemeral=True)
                return
            # If user is already on a break
            if (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) == MemberStatus.BREAK.value):
                await interaction.response.send_message(f"You are already on a break. {interaction.user.mention}", ephemeral=True)
                return
            
            # If user is present, or on absent, the update happens
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.BREAK.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 1
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, self.member_statuses[user_id][MemberStatusKey.STATUS.value], self.member_statuses[user_id][MemberStatusKey.ABSENCES.value])

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
            await self.db.add_or_update_checkin_member(self.session_id, user_id, self.member_statuses[user_id][MemberStatusKey.STATUS.value], self.member_statuses[user_id][MemberStatusKey.ABSENCES.value])
            
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
                await interaction.response.send_message(f"You are already not in this session. {interaction.user.mention}", ephemeral=True)
                return

            # If user is present, absent, or on a break
            self.member_statuses[user_id][MemberStatusKey.STATUS.value] = MemberStatus.EXITED.value
            self.member_statuses[user_id][MemberStatusKey.ABSENCES.value] = 0
            self.member_ids = [member_id for member_id in self.member_statuses.keys() if self.member_statuses.get(user_id, {}).get(MemberStatusKey.STATUS.value) != MemberStatus.EXITED.value]
            

            # Update DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, self.member_statuses[user_id][MemberStatusKey.STATUS.value], self.member_statuses[user_id][MemberStatusKey.ABSENCES.value])
            
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

            user_id = interaction.user.id
            menu_msg : Optional[discord.Message] = None
            if user_id != self.owner_id:
                await interaction.followup.send(f"You are NOT the owner of the session. {interaction.user.mention}. Exiting...", ephemeral=True)
                return
            
            await interaction.followup.send(f"You are the owner of the session. {interaction.user.mention}. Starting change ownership...", ephemeral=True)
            
            rest_members_list = [member_id for member_id in self.member_ids if member_id != self.owner_id]
            
            if not rest_members_list:
                await interaction.followup.send(f"There are no other members in this session to change owner to. Try again.", ephemeral=True)
                return
            
            new_owner_options : List[discord.SelectOption] = [
                discord.SelectOption(label= self.guild.get_member(member_id).display_name,
                    value= str(member_id))
                    for member_id in rest_members_list
            ]
            
            new_owner_select : Select = Select(placeholder= "Select a new owner from the list.",
                                                        min_values= 1,
                                                        max_values= 1,
                                                        options = new_owner_options,
                                                        )

            # Callback Function for New Owner Select Menu
            async def new_owner_callback(interaction : discord.Interaction):
                selected_user_id = int(new_owner_select.values[0])
                selected_user = self.guild.get_member(selected_user_id)

                old_owner_id = self.owner_id
                old_owner = self.guild.get_member(old_owner_id)

                if selected_user_id not in self.member_ids:
                    logger.error(f"The selected member with name {selected_user.display_name} is not in the Session named {self.name}. Exiting...")
                    await interaction.followup.send(f"The selected member {selected_user.mention} is not a part of the session. Try again...")

                self.owner_id = selected_user_id
                await menu_msg.edit(content=f"Ownership has been transferred to {selected_user.mention} from previous owner {old_owner.mention}.", view=None)
                await self.update_embed()
                

            new_owner_select.callback = new_owner_callback

            new_owner_view = View()
            new_owner_view.add_item(new_owner_select)

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

            if not self.can_end(interaction.user.id):
                await interaction.followup.send(f"Only the session creator: {self.guild.get_member(self.owner_id)} can end the session.", ephemeral=True)
                return

            await self.disable_previous_buttons()
            
            embed = discord.Embed(
                title=f"Check-in Session: {self.name} Ended",
                description=f"The session has been manually ended by {interaction.user.display_name}.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Session owner: {self.guild.get_member(self.owner_id)}")

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
        return user_id == self.creator_id


    ## Helper Function - Clear Session Data
    async def clear_session_data(self):
        # Clear all session data explicitly to avoid any future interaction
        try:
            
            # Delete session and members data from the database first
            await self.db.delete_checkin_session(self.session_id)
            
            # Clear in-memory session data
            self.member_ids.clear()
            self.member_statuses.clear()
            self.last_reminder_message_id = 0
            self.reminder_count = 0
            
            # Remove session from the active sessions list
            self.cog.active_sessions.pop(self.session_id)
            
            logger.debug(f"Session data for session name {self.name} and Session ID: {self.session_id} cleared successfully.")
        except Exception as e:
            logger.error(f"Failed to clear session data for session {self.session_id}: {str(e)}")




class CheckinCog(commands.Cog):

    def __init__(self, bot: commands.Cog):
        self.bot = bot
        self.db : DBHandler = bot.db
        self.active_sessions = {}
        self.guild_settings = {}
        logger.debug("Check-in Cog initialized.")

        bot.loop.create_task(self.load_active_sessions_from_db())
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
                    guild : discord.Guild = await self.bot.fetch_guild(guild_id)
                    if guild is None:
                        logger.warning(f"Guild with ID {guild_id} could not be fetched. Proceeding with default settings.")
                        # initialise with default settings without a guild object
                        self.guild_settings[guild_id] = CheckinGuildSettings(None)
                    else:
                        self.guild_settings[guild_id] = CheckinGuildSettings(None)
                this_guild_settings = self.guild_settings[guild_id]

                # Create a new CheckinSession object
                session = CheckinSession(
                    db=self.db,
                    cog=self,
                    interaction=None,  # Interaction is not available during bot restart
                    name=session_data["name"],
                    member_ids=[m['member_id'] for m in member_statuses],
                    duration=session_data["duration"],
                    settings=this_guild_settings
                )

                # Set session attributes
                session.session_id = session_data["session_id"]
                session.guild_id = session_data["guild_id"]
                session.creator_id = session_data["creator_id"]
                session.owner_id = session_data["owner_id"]
                session.text_id = session_data["text_channel_id"]
                session.start_time = float(session_data["start_time"])
                session.reminder_count = session_data["reminder_count"]
                session.last_reminder_time = float(session_data["last_reminder_time"])
                session.next_reminder_time = float(session_data["next_reminder_time"])
                session.member_statuses = member_status_dict

                # Add the session to active_sessions and start reminder loop
                self.active_sessions[session.session_id] = session

                # Staggered start for reminders (random small delay)
                # Delay between 30 and 150 seconds
                delay = random.uniform(30,150)
                await asyncio.sleep(delay)
                self.bot.loop.create_task(session.run_checkin_reminders())  # Start the reminder loop

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
        # Parse the duration and mentions

        duration_seconds = parse_duration(duration)
        member_ids : List[discord.Member] = parse_mentions(interaction, mentions)

        if interaction.guild.id not in self.guild_settings:
            self.guild_settings[interaction.guild.id] = CheckinGuildSettings(interaction)

         # Validate parameters before proceeding
        if not await validate_parameters(
            interaction = interaction,
            name = name,
            member_ids = member_ids,
            duration= duration,
            max_members=10,
            # settings=self.guild_settings[interaction.guild.id] or CheckinGuildSettings(interaction=interaction)
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
            logger.info(f"Check-in session with ID {session.session_id} started by {interaction.user.display_name} in channel {interaction.channel.id}.")

            # Send the initial message with buttons
            await session.setup_checkin_resources()
            await session.send_reminder_message(initial=True)
            self.bot.loop.create_task(session.run_checkin_reminders())
        except Exception as e:
            logger.error(f"Error starting check-in session: {str(e)}")
            await interaction.followup.send("An error occurred while starting the check-in session.", ephemeral=True)


    ## Command - /setup_checkin
    @app_commands.command(name="settings_checkin", description="Changes the Settings of Checkin Module")
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

        await interaction.response.defer()
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
