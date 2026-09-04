import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from database import DBHandler
from utils import check_manager, parse_mentions, parse_seconds_to_hms, validate_parameters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
current_namespace = sys.modules[__name__].__name__.split('.')[-1]

class StudyGroup:
    def __init__(self, db, cog, guild_id: int, name: str, creator_id: int, category_id: int, max_members: int, member_ids: List[int] ):
        # Initializes the StudyGroup class.

        # Critical Info first
        self.guild_id : int = guild_id
        self.name : str = name
        self.group_id : str = self.generate_group_id()
        self.creator_id : int = creator_id
        self.owner_id : int = creator_id                            # Initially, creator is owner
        self.category_id : int = category_id
        self.max_members : int = max_members
        self.member_ids : List[int] = member_ids

        # IDs for roles and channels (will be set later)
        self.group_role_id: int = 0
        self.vc_id: int = 0
        self.text_id: int = 0
        self.info_embed_id = 0

        # VC Settings
        self.speak_enabled : bool = True
        self.video_mode : str = "off"
        self.video_timer : int = 10                                 # in seconds

        # Time related attributes
        self.start_time : float = datetime.now().timestamp()
        self.duration : int = 12*60*60                              # Default duration of 12 hours
        self.end_time: float = (datetime.fromtimestamp(self.start_time) + timedelta(seconds=self.duration)).timestamp()
        self.current_time : float = datetime.now().timestamp()

        # Final Stuff
        self.active : bool = False

        # Other stuff, not stored in Database
        self.cog : 'StudyGroupCog' = cog
        self.bot : Any = getattr(cog, 'bot', None)
        self.db : DBHandler = db
        self.guild : Optional[discord.Guild] = None
        self.view : Optional[View] = None




    ## Setup - Generate Group ID
    def generate_group_id(self) -> str:
        # Generate a unique UUID v4 for the group
        return str(uuid.uuid4())



    ## Setup - Group Resources
    async def setup_group_resources(self, interaction: discord.Interaction) -> str:
        """
        Sets up Discord resources (roles, channels, permissions) for the study group.
        Sends welcome and group info messages, then writes to the database.
        Returns a string indicating success or failure.
        """
        if not interaction.guild:
            logger.error(f"Interaction guild not found for StudyGroup '{self.name}'")
            return "Failed to set up resources: Guild not found."
        self.guild = interaction.guild
        logger.info(f"Starting resource setup for StudyGroup '{self.name}' in guild '{self.guild_id}'")

        # 1. Role and channel creation
        try:
            # Create group role
            group_role = await self.guild.create_role(name=f"{self.name} Group", reason="Role for study group")
            self.group_role_id = group_role.id
            logger.info(f"Role '{group_role.name}' created for StudyGroup '{self.name}'")

            # Create channels in the specified category
            category = self.guild.get_channel(self.category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                logger.error(f"Category not found with ID {self.category_id} in {self.guild_id}")
                raise ValueError(f"Invalid category: {self.category_id} for StudyGroup '{self.name}'")

            text_channel = await category.create_text_channel(name=f"{self.name}-text", reason="Text channel for study group")
            voice_channel = await category.create_voice_channel(name=f"{self.name}-voice", reason="Voice channel for study group")
            self.text_id = text_channel.id
            self.vc_id = voice_channel.id
            logger.info(f"Text and voice channels created for StudyGroup '{self.name}': Text ID: {self.text_id}, Voice ID: {self.vc_id}")

            # Set permissions for group role in channels
            await text_channel.set_permissions(group_role, read_messages=True, send_messages=True)
            await voice_channel.set_permissions(group_role, connect=True, speak=True)

        except discord.Forbidden as forbidden_e:
            logger.error(f"Permission error during role/channel setup: {forbidden_e}")
            return f"Failed to set up resources for '{self.name}': Permission error."

        except discord.HTTPException as http_e:
            logger.error(f"HTTP error during role/channel setup: {http_e}")
            return f"Failed to set up resources for '{self.name}': HTTP error."

        except Exception as e:
            logger.error(f"Error creating role/channels for StudyGroup '{self.name}': {e}")
            return f"Failed to create role/channels for '{self.name}'."

        # 2. Member role assignment
        try:
            for member_id in self.member_ids:
                member = self.guild.get_member(member_id)
                if member:
                    await member.add_roles(group_role)
                    await self.db.add_member_to_study_group_db(self.group_id, member_id)
                    logger.info(f"Assigned role to member '{member.display_name}' for StudyGroup '{self.name}'")
                else:
                    logger.warning(f"Member with ID '{member_id}' not found in guild '{self.guild_id}'")
        except Exception as e:
            logger.error(f"Error assigning roles to members for StudyGroup '{self.name}': {e}")
            return f"Failed to assign roles to members for '{self.name}'."

        # 3. Sending messages
        try:
            await self.send_welcome_message()
            await self.group_info_embed()
            await self.button_view()
            await self.send_ping_message()
            logger.info(f"Messages sent for StudyGroup '{self.name}'")
        except Exception as e:
            logger.error(f"Error sending messages for StudyGroup '{self.name}': {e}")
            return f"Failed to send messages for StudyGroup '{self.name}': {e}"

        self.active = True
        logger.info(f"Study Group {self.name} is now active.")

        # 5. Saving to the database
        try:
            await self.db.save_study_group(study_group_data={
                "guild_id": self.guild_id,
                "name": self.name,
                "group_id": self.group_id,
                "category_id": self.category_id,
                "max_members": self.max_members,
                "member_ids": self.member_ids,
                "creator_id": self.creator_id,
                "owner_id": self.owner_id,
                "group_role_id": self.group_role_id,
                "text_id": self.text_id,
                "vc_id": self.vc_id,
                "info_embed_id": self.info_embed_id,
                "start_time": self.start_time,
                "duration": self.duration,
                "end_time": self.end_time,
                "speak_enabled": self.speak_enabled,
                "video_mode": self.video_mode,
                "video_timer": self.video_timer,
                "active": self.active
            })
            logger.info(f"StudyGroup '{self.name}' saved to the database.")
        except Exception as e:
            self.active = False
            asyncio.create_task(self.end_group())
            logger.error(f"Failed to save StudyGroup '{self.name}' to the database: {e}")
            return f"Failed to save StudyGroup '{self.name}' to the database."

        # Log if all goes well
        logger.info(f"StudyGroup '{self.name}'created successfully with roles, channels, and database entry.")
        return f"StudyGroup '{self.name}' created successfully with roles, channels, and database entry."



    ### --- MEMBERSHIP FUNCTIONS --- ###
    """
    Functions to manager membership:
    Functions
     - is_owner - returns bool
     - is_member - returns bool
     - add_member - returns None (also updates DB)
        DB Function - add_member_to_db
     - remove_member - returns None (also updates DB)
        DB Function - remove_member_from_db
     - transfer_ownership - returns None (also updates DB)
        DB Function - transfer_ownership_db
    """

    ## Membership - Check Owner
    def is_owner(self, user_id: int) -> bool:
        ### Check if the given user is the owner of the group
        return self.owner_id == user_id


    ## Membership - Check if member
    def is_member(self, user_id : int) -> bool:
        ### Check if the given user is a member of the group
        return user_id in self.member_ids


    ## Membership - Add Member to Group
    async def add_member(self, user_or_id: Union[discord.Member, int], interaction: Optional[discord.Interaction] = None) -> None:
        ### Add a member to the group
        try:
            if not self.guild:
                logger.error(f"Guild not set for study group '{self.name}'")
                return

            user_id = user_or_id.id if isinstance(user_or_id, (discord.Member, discord.User)) else int(user_or_id)

            if len(self.member_ids) >= self.max_members:
                logger.warning(f"Group is full with No. of Members: {len(self.member_ids)} and Max members: {self.max_members}.")
                if interaction:
                    await interaction.followup.send(f"This group is full with No. of Members: {len(self.member_ids)}", ephemeral=True)
                return

            if user_id in self.member_ids:
                logger.warning(f"Member with ID {user_id} already in the group.")
                if interaction:
                    await interaction.followup.send(f"Member with ID {user_id} already in the group.", ephemeral=True)
                return

            member = self.guild.get_member(user_id)
            if not member:
                logger.warning(f"Member with ID {user_id} not found in the guild.")
                if interaction:
                    await interaction.followup.send(f"Member with ID {user_id} not found.", ephemeral=True)
                return

            group_role = self.guild.get_role(self.group_role_id)
            if group_role:
                await member.add_roles(group_role)
            self.member_ids.append(user_id)

            # Update the database after adding the member
            await self.db.add_member_to_study_group_db(self.group_id, user_id)

            logger.info(f"Member {member.display_name} added to the group {self.name}.")
            if interaction:
                await interaction.followup.send(f"Member {member.display_name} added to the group.", ephemeral=True)
            return

        except Exception as e:
            logger.error(f"Error adding member: {e}")
            if interaction:
                await interaction.followup.send(f"Error adding member to group {self.name}.", ephemeral=True)
            return


    ## Membership - Remove Member from Group
    async def remove_member(self, interaction: discord.Interaction, user_id : int) -> None:
        ### Remove a member from group
        try:
            if not self.guild:
                return

            if len(self.member_ids) < 0:
                logger.warning(f"There are no members ({len(self.member_ids)}) in the group: {self.name}.")
                await interaction.followup.send(f"There are no members in this group. No. of Members: {len(self.member_ids)}.", ephemeral=True)
                return

            if user_id not in self.member_ids:
                logger.warning(f"Member with ID {user_id} is not part of the group: {self.name}.")
                await interaction.followup.send(f"Member with ID {user_id} is not part of the group.", ephemeral=True)
                return

            member = self.guild.get_member(user_id)
            if not member:
                logger.warning(f"Member with ID {user_id} not found in the guild {self.name}.")
                await interaction.followup.send(f"Member with ID {user_id} not found.", ephemeral=True)
                return

            # Remove the group role from the member
            group_role = self.guild.get_role(self.group_role_id)
            if group_role:
                await member.remove_roles(group_role)
            self.member_ids.remove(user_id)

            # Update the database after removing the member
            await self.db.remove_member_from_study_group_db(self.group_id, user_id)

            logger.info(f"Member {member.display_name} removed from the study group '{self.name}'.")
            await interaction.followup.send(f"Member {member.display_name} successfully removed from the group.", ephemeral=True)
            return

        except Exception as e:
            logger.error(f"Error removing member {user_id} from group '{self.name}': {e}")
            await interaction.followup.send(f"Error removing member {user_id} from the group.", ephemeral=True)
            return


    ## Permission Helper - Can Control Group
    async def can_control(self, user: Union[discord.Member, discord.User]) -> bool:
        """Determines if the given user has permission to manage/control the study group."""
        if getattr(self.bot, 'bot_developer_id', None) == user.id:
            return True
        if user.id in (self.owner_id, self.creator_id):
            return True
        if self.guild:
            if getattr(self.guild, 'owner_id', None) == user.id:
                return True
            member = user if isinstance(user, discord.Member) else self.guild.get_member(user.id)
            if member:
                perms = member.guild_permissions
                if perms.administrator or perms.manage_guild or perms.manage_channels or perms.manage_roles or perms.moderate_members:
                    return True
                mod_keywords = {'admin', 'administrator', 'mod', 'moderator', 'manager', 'lead', 'owner', 'staff'}
                if any(any(kw in r.name.lower() for kw in mod_keywords) for r in member.roles):
                    return True
            if hasattr(self.db, 'get_manager'):
                try:
                    mgr = await self.db.get_manager(user.id, self.guild.id)
                    if mgr and (mgr['permission_level'] >= 3 or mgr['guild_id'] is None):
                        return True
                except Exception:
                    pass
        return False

    ## Membership - Transfer Ownership
    async def transfer_ownership(self, interaction : discord.Interaction, new_owner_id : int) -> None:
        ### Transfer ownership of the group to another member
        try:
            if not interaction.guild:
                return

            if not await self.can_control(interaction.user):
                logger.warning(f"User {interaction.user.display_name} lacks permission to transfer group '{self.name}'.")
                if interaction.response.is_done():
                    await interaction.followup.send("You don't have permission to transfer this group. Only the group owner, server owner, or moderators can transfer ownership.", ephemeral=True)
                else:
                    await interaction.response.send_message("You don't have permission to transfer this group. Only the group owner, server owner, or moderators can transfer ownership.", ephemeral=True)
                return

            if new_owner_id == self.owner_id:
                logger.warning(f"User with ID {new_owner_id} is already the owner of the group '{self.name}'.")
                if interaction.response.is_done():
                    await interaction.followup.send("That user is already the owner of the group.", ephemeral=True)
                else:
                    await interaction.response.send_message("That user is already the owner of the group.", ephemeral=True)
                return

            new_owner = interaction.guild.get_member(new_owner_id)
            if not new_owner:
                try:
                    new_owner = await interaction.guild.fetch_member(new_owner_id)
                except Exception:
                    new_owner = None

            if not new_owner:
                logger.warning(f"Member with ID {new_owner_id} not found in the guild.")
                if interaction.response.is_done():
                    await interaction.followup.send(f"Member with ID {new_owner_id} not found in this server.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Member with ID {new_owner_id} not found in this server.", ephemeral=True)
                return

            # If new owner is not already a member, add them to the group
            if new_owner_id not in self.member_ids:
                await self.add_member(new_owner)

            # Transfer ownership
            old_owner = interaction.guild.get_member(self.owner_id)
            old_owner_str = old_owner.mention if old_owner else f"<@{self.owner_id}>"
            self.owner_id = new_owner_id

            # Update database
            await self.db.transfer_ownership_study_group_db(self.group_id, new_owner_id)
            await self.group_info_embed(update=True)

            logger.info(f"Ownership of group '{self.name}' transferred to {new_owner.display_name} by {interaction.user.display_name}.")
            if interaction.response.is_done():
                await interaction.followup.send(content=f"Ownership of **{self.name}** successfully transferred from {old_owner_str} to {new_owner.mention}.")
            else:
                await interaction.response.send_message(content=f"Ownership of **{self.name}** successfully transferred from {old_owner_str} to {new_owner.mention}.")

        except Exception as e:
            logger.error(f"Error transferring ownership: {e}")
            if interaction.response.is_done():
                await interaction.followup.send("An error occurred while transferring group ownership.", ephemeral=True)
            else:
                await interaction.response.send_message("An error occurred while transferring group ownership.", ephemeral=True)




    ### --- MESSAGE FUNCTIONS --- ###
    """
    List of functions for sending messages to the group
    Functions:
     - send_welcome_message
     - disable_buttons
     - group_info_embed
     - button_view
     - send_ping_message
    """

    ## Message - Send Group Buttons in VIEW
    async def button_view(self) -> None:
        ### Create the view of buttons that people can interact with
        try:
            if not self.guild:
                return
            ch = self.guild.get_channel(self.text_id)
            if not isinstance(ch, discord.TextChannel):
                logger.error(f"Text channel with ID {self.text_id} not found for group '{self.name}'.")
                return
            text_channel = ch

            # Create Buttons - Row 0: Core Group Operations
            leave_button: Button[Any] = Button(label="Leave", style=discord.ButtonStyle.danger, row=0)
            end_button: Button[Any] = Button(label="End Group", style=discord.ButtonStyle.danger, row=0)
            transfer_button: Button[Any] = Button(label="Transfer", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
            rename_button: Button[Any] = Button(label="Rename", style=discord.ButtonStyle.success, row=0)
            refresh_button: Button[Any] = Button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔃", row=0)

            # Row 1: VC and Session Controls
            speak_toggle_button: Button[Any] = Button(label="Speak On/Off", style=discord.ButtonStyle.secondary, row=1)
            video_toggle_button: Button[Any] = Button(label="Video On/Off", style=discord.ButtonStyle.secondary, row=1)
            extend_button: Button[Any] = Button(label="Extend", style=discord.ButtonStyle.secondary, row=1)
            votekick_button: Button[Any] = Button(label="Votekick", style=discord.ButtonStyle.secondary, row=1)

            # Row 2: Pomodoro & Check-in Integrated Controls
            checkin_present_btn: Button[Any] = Button(label="Check-in: Present", style=discord.ButtonStyle.success, emoji="✅", row=2)
            checkin_break_btn: Button[Any] = Button(label="Check-in: Break", style=discord.ButtonStyle.primary, emoji="☕", row=2)
            pomo_toggle_btn: Button[Any] = Button(label="Pomo: Pause/Resume", style=discord.ButtonStyle.secondary, emoji="⏯️", row=2)
            pomo_end_btn: Button[Any] = Button(label="Pomo: End", style=discord.ButtonStyle.danger, emoji="⏹️", row=2)

            # Assign Callbacks
            leave_button.callback = self.leave_group_callback  # type: ignore[method-assign]
            end_button.callback = self.end_group_callback  # type: ignore[method-assign]
            transfer_button.callback = self.transfer_group_callback  # type: ignore[method-assign]
            rename_button.callback = self.rename_group_callback  # type: ignore[method-assign]
            refresh_button.callback = self.refresh_gui_callback  # type: ignore[method-assign]

            speak_toggle_button.callback = self.speak_toggle_callback  # type: ignore[method-assign]
            video_toggle_button.callback = self.video_toggle_callback  # type: ignore[method-assign]
            extend_button.callback = self.extend_duration_callback  # type: ignore[method-assign]
            votekick_button.callback = self.votekick_callback  # type: ignore[method-assign]

            checkin_present_btn.callback = self.checkin_present_callback  # type: ignore[method-assign]
            checkin_break_btn.callback = self.checkin_break_callback  # type: ignore[method-assign]
            pomo_toggle_btn.callback = self.pomo_toggle_callback  # type: ignore[method-assign]
            pomo_end_btn.callback = self.pomo_end_callback  # type: ignore[method-assign]

            # Create View and add all components
            self.view = View()
            self.view.add_item(leave_button)
            self.view.add_item(end_button)
            self.view.add_item(transfer_button)
            self.view.add_item(rename_button)
            self.view.add_item(refresh_button)

            self.view.add_item(speak_toggle_button)
            self.view.add_item(video_toggle_button)
            self.view.add_item(extend_button)
            self.view.add_item(votekick_button)

            self.view.add_item(checkin_present_btn)
            self.view.add_item(checkin_break_btn)
            self.view.add_item(pomo_toggle_btn)
            self.view.add_item(pomo_end_btn)

            # self.view.add_item(select)

            # Send the message with the button view
            await text_channel.send(content="Here are your group control buttons:", view=self.view)
            logger.info(f"Button view sent in channel '{text_channel.name}' for group '{self.name}'.")

        except Exception as e:
            logger.error(f"Error sending button view in channel '{text_channel.name}' for group '{self.name}': {e}")


    ## Message - Send Welcome Message in MESSAGE
    async def send_welcome_message(self):
        try:
            # Retrieve the group role object
            role : discord.Role = self.guild.get_role(self.group_role_id)
            send_channel : discord.TextChannel = self.guild.get_channel(self.text_id)

            # Compose the welcome message
            welcome_message = (
                f"🎉 Welcome to the **{self.name}** study group!\n"
                f"{role.mention}, you've been added to the group. Let's get studying together! 📚"
            )

            # Send the message in the specified text channel
            await send_channel.send(welcome_message)
            logger.info(f"Welcome message sent in channel '{send_channel.name}' for group '{self.name}'.")

        except Exception as e:
            logger.error(f"Error sending welcome message in channel {send_channel.name} for group '{self.name}': {e}")


    ## Message - Disable buttons of a given message
    async def disable_buttons(self, message: discord.Message) -> None:
        ### Disable all buttons in the given message
        try:
            view = discord.ui.View.from_message(message)
            for item in view.children:
                if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                    item.disabled = True
            await message.edit(view=view)
            channel_name = getattr(message.channel, 'name', 'channel')
            logger.info(f"Buttons disabled in message '{message.content}' in the channel '{channel_name}' for group '{self.name}'.")

        except Exception as e:
            channel_name = getattr(message.channel, 'name', 'channel')
            logger.error(f"Error disabling buttons in message '{message.content}' in channel '{channel_name}' for group '{self.name}': {e}")


    ## Message - Send Group Info in EMBED
    async def group_info_embed(self, update : bool = False) -> None:
        try:
            if not self.guild:
                logger.error(f"Guild not set for study group '{self.name}'")
                return

            text_channel = self.guild.get_channel(self.text_id)
            voice_channel = self.guild.get_channel(self.vc_id)
            role = self.guild.get_role(self.group_role_id)
            creator = self.guild.get_member(self.creator_id)
            owner = self.guild.get_member(self.owner_id)

            if not isinstance(text_channel, discord.TextChannel) or not isinstance(voice_channel, discord.VoiceChannel):
                logger.error(f"Text or voice channel missing for group '{self.name}'")
                return

            # Create the embed
            embed = discord.Embed(title=self.name)
            embed.description = "This group is for studying, and people are going to study hard in this!!!"
            embed.add_field(name = "Text Channel", value = text_channel.mention)
            embed.add_field(name = "Voice Channel", value = voice_channel.mention)
            embed.add_field(name = "Creator", value = creator.mention if creator else str(self.creator_id), inline=True)
            embed.add_field(name = "Owner", value = owner.mention if owner else str(self.owner_id), inline=True)
            embed.add_field(name = "Group Role", value = role.mention if role else str(self.group_role_id))
            embed.add_field(name = "Number of Members", value = len(self.member_ids), inline=True)
            embed.add_field(name = "Max Size", value = self.max_members, inline=True)
            embed.add_field(name = "Group Duration", value = parse_seconds_to_hms(self.duration), inline=True)
            embed.add_field(name="Video", value=f"Video Mode: {self.video_mode.capitalize()}", inline=True)
            embed.add_field(name="Video Timer", value=f"{self.video_timer} seconds", inline=True)
            embed.add_field(name="Speak", value="On" if self.speak_enabled else "Off", inline=True)

            # Check for active Pomodoro session
            pomo_cog = self.bot.get_cog("Pomodoro") if self.bot else None
            pomo_session = None
            if pomo_cog:
                pomo_session = pomo_cog.sessions.get(self.group_id)
                if not pomo_session:
                    for s in pomo_cog.sessions.values():
                        if str(getattr(s, 'group_id', '')) == str(self.group_id) or (getattr(s, 'text_id', 0) and getattr(s, 'text_id', 0) == self.text_id):
                            pomo_session = s
                            break

            if pomo_session:
                stage_names = {
                    "focus": "🎯 Focus",
                    "short_break": "☕ Short Break",
                    "long_break": "🌴 Long Break"
                }
                stage_str = stage_names.get(pomo_session.current_stage, pomo_session.current_stage.capitalize())
                status_str = "⏸️ Paused" if pomo_session.is_paused else "▶️ Running"
                timer_sec = pomo_session.timer if pomo_session.timer is not None else pomo_session.focus * 60
                remaining = str(timedelta(seconds=max(0, timer_sec)))
                vc_mode = "🔊 Voice Required" if getattr(pomo_session, 'require_vc', True) else "💬 Text-Only"
                embed.add_field(
                    name="⏱️ Pomodoro Session",
                    value=f"**Status**: {status_str} | **Stage**: {stage_str}\n**Remaining**: {remaining} | **Cycles**: {pomo_session.cycles}\n**Mode**: {vc_mode}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⏱️ Pomodoro Session",
                    value="*No active session. Use `/start_pomodoro` to begin.*",
                    inline=False
                )

            # Check for active Check-in session
            checkin_cog = self.bot.get_cog("CheckinCog") if self.bot else None
            checkin_session = None
            if checkin_cog:
                for s in checkin_cog.active_sessions.values():
                    if s.text_id == self.text_id:
                        checkin_session = s
                        break

            if checkin_session:
                present_list = [f"<@{uid}>" for uid, data in checkin_session.member_statuses.items() if data.get("status") == "present"]
                break_list = [f"<@{uid}>" for uid, data in checkin_session.member_statuses.items() if data.get("status") == "break"]
                absent_list = [f"<@{uid}>" for uid, data in checkin_session.member_statuses.items() if data.get("status") == "absent"]
                next_rem = f"<t:{int(checkin_session.next_reminder_time)}:R>" if checkin_session.next_reminder_time else "N/A"

                checkin_text = (
                    f"**Session**: {checkin_session.name} (Next check-in: {next_rem})\n"
                    f"✅ **Present** ({len(present_list)}): {', '.join(present_list) if present_list else 'None'}\n"
                    f"☕ **On Break** ({len(break_list)}): {', '.join(break_list) if break_list else 'None'}\n"
                    f"❌ **Absent** ({len(absent_list)}): {', '.join(absent_list) if absent_list else 'None'}"
                )
                embed.add_field(name="📋 Check-in Status", value=checkin_text, inline=False)
            else:
                embed.add_field(
                    name="📋 Check-in Status",
                    value="*No active check-in. Use `/checkin` to start standups.*",
                    inline=False
                )

             # If updating an existing message
            if update and self.info_embed_id:
                try:
                    # Fetch the message by ID and edit it
                    message = await text_channel.fetch_message(self.info_embed_id)
                    await message.edit(embed=embed)
                    logger.info(f"Group info embed updated in channel '{text_channel.name}' for group '{self.name}'.")
                except discord.NotFound:
                    logger.warning(f"Message with ID {self.info_embed_id} not found, sending a new message.")
                    # If the message was deleted, send a new one
                    new_message = await text_channel.send(embed=embed)
                    self.info_embed_id = new_message.id
                    logger.info(f"Group info embed sent in channel '{text_channel.name}' for group '{self.name}' (new message).")

            else:
                # Send a new message and store its message ID
                new_message = await text_channel.send(embed=embed)
                self.info_embed_id = new_message.id
                logger.info(f"Group info embed sent in channel '{text_channel.name}' for group '{self.name}' (first message).")


        except Exception as e:
            logger.error(f"Error sending group info embed for group '{self.name}': {e}")


    ## Message - Send Ping Message in MESSAGE
    async def send_ping_message(self, send_channel: Optional[discord.TextChannel] = None) -> None:
        if not self.guild:
            return

        if send_channel is None:
            ch = self.guild.get_channel(self.text_id)
            if isinstance(ch, discord.TextChannel):
                send_channel = ch
            else:
                return

        role = self.guild.get_role(self.group_role_id)
        members : List[discord.Member] = []

        for member_id in self.member_ids:
            member = self.guild.get_member(member_id)
            if member:
                members.append(member)

        message = ", ".join([member.mention for member in members])
        role_mention = role.mention if role else f"<@&{self.group_role_id}>"
        await send_channel.send(content=f"Hello group! {role_mention}")
        await send_channel.send(content=f"Hello All Members! \n {message}")



    ### --- CALLBACK FUNCTIONS --- ###
    """
    These are the callback functions for Button and Select Menu Interactions
     - Invite Members - Select Menu
     - Kick Members - Select Menu
     - Leave Group - Button
        - Placeholder Set up
     - End Group - Button
         - Implemented
     - Rename Group - Button
         - Implemented
     - Extend Duration - Button
         - Implemented
     - Votekick - Button 
         - Placeholder Set up
     - Speak on/off - Button
         - Placeholder Set up
     - Video on/off/force - Button
         - Placeholder Set up
    """

    ## Callback - End Group
    async def end_group_callback(self, interaction: discord.Interaction):
        if not await self.can_control(interaction.user):
            await interaction.response.send_message("Only the group owner, creator, or server managers/moderators can end this study group.", ephemeral=True)
            return

        role = self.guild.get_role(self.group_role_id) if self.guild else None
        role_mention = role.mention if role else f"<@&{self.group_role_id}>"

        await interaction.response.send_message(f"❗❗Attention❗❗\n{role_mention}\nThe group will be destroyed in 60 seconds.\nPlease disconnect from the VCs and wrap up your activities.")
        asyncio.create_task(self.end_group())
        await interaction.followup.send("End Group function has started. The group will end shortly.")
        logger.info(f"User: {interaction.user.name} has called for the closure of Group'{self.name}', End Group function has started. The group will end shortly.")


    ## Callback - Transfer Group
    async def transfer_group_callback(self, interaction: discord.Interaction):
        try:
            if not await self.can_control(interaction.user):
                await interaction.response.send_message("Only the group owner, creator, or server managers/moderators can transfer this study group.", ephemeral=True)
                return

            study_group_ref = self

            class TransferUserSelect(discord.ui.UserSelect):
                def __init__(self):
                    super().__init__(placeholder="Select the new group owner...", min_values=1, max_values=1)

                async def callback(self, select_interaction: discord.Interaction):
                    if not await study_group_ref.can_control(select_interaction.user):
                        await select_interaction.response.send_message("You are not authorized to transfer this group.", ephemeral=True)
                        return
                    selected_user = self.values[0]
                    await study_group_ref.transfer_ownership(select_interaction, selected_user.id)

            view = View(timeout=120)
            view.add_item(TransferUserSelect())
            await interaction.response.send_message("Select the user you want to transfer group ownership to:", view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error initiating transfer group callback for '{self.name}': {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Failed to initiate group transfer.", ephemeral=True)
            else:
                await interaction.followup.send("Failed to initiate group transfer.", ephemeral=True)


    ## Callback - Rename Group
    async def rename_group_callback(self, interaction: discord.Interaction):
        if not await self.can_control(interaction.user):
            await interaction.response.send_message("Only the group owner, creator, or server managers/moderators can rename this study group.", ephemeral=True)
            return

    # Define the modal subclass inside the callback (local to this scope)
        class RenameGroupModal(Modal):
            def __init__(self, study_group, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.study_group : 'StudyGroup'= study_group

                # Add a text input field for the new group name
                self.new_name_input = TextInput(
                    label="New Group Name",
                    placeholder="Enter the new group name",
                    required=True,
                    max_length=100
                )
                self.add_item(self.new_name_input)

            # Define the submission logic
            async def on_submit(self, interaction: discord.Interaction):
                new_name = self.new_name_input.value

                try:
                    # Defer the interaction to avoid timeout
                    await interaction.response.defer(ephemeral=True)

                    # Update the group's name
                    self.study_group.name = new_name

                    # Rename Role, VC, Text Channel
                    if not interaction.guild:
                        return

                    role = interaction.guild.get_role(self.study_group.group_role_id)
                    if role:
                        await role.edit(name=f"{new_name} Group")
                        logger.info(f"Role '{old_name} Group' renamed to '{new_name} Group'")

                    ch_text = interaction.guild.get_channel(self.study_group.text_id)
                    if isinstance(ch_text, discord.TextChannel):
                        await ch_text.edit(name=f"{new_name}-text")
                        logger.info(f"Text Channel '{old_name}-text' renamed to '{new_name}-text'")

                    ch_vc = interaction.guild.get_channel(self.study_group.vc_id)
                    if isinstance(ch_vc, discord.VoiceChannel):
                        await ch_vc.edit(name=f"{new_name}-voice")
                        logger.info(f"Voice Channel '{old_name}-voice' renamed to '{new_name}-voice'")

                    # Update into database
                    await self.study_group.db.update_study_group_by_id({
                        "group_id": self.study_group.group_id,
                        "name": new_name
                    })

                    # Update Group Info Embed
                    await self.study_group.group_info_embed(update=True)

                    # Send a follow-up confirmation message
                    await interaction.followup.send(f"Group renamed to '{new_name}'", ephemeral=True)
                    logger.info(f"The group renamed from {self.study_group.name} to {new_name}")

                except Exception as e:
                    logger.error(f"Error renaming group '{self.study_group.name}': {e}")
                    await interaction.followup.send("Error renaming group", ephemeral=True)

        try:
            old_name = self.name
            # Create an instance of the modal
            rename_group_modal = RenameGroupModal(self, title=f"Rename Study Group: {old_name}")

            # Show the modal to the user
            await interaction.response.send_modal(rename_group_modal)

        except Exception as e:
            logger.error(f"Error renaming group '{self.name}': {e}")
            await interaction.followup.send("Error renaming group", ephemeral=True)


    ## Callback - Extend Duration
    async def extend_duration_callback(self, interaction: discord.Interaction):
        if not await self.can_control(interaction.user):
            await interaction.response.send_message("Only the group owner, creator, or server managers/moderators can extend duration of this study group.", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
            extra_time : int = 3600  # Example: Extend by 1 hour
            self.duration += extra_time
            self.end_time += float(extra_time)
            # Update in the database (DBHandler function)
            await self.db.update_study_group_by_id({
                "group_id": self.group_id,
                "duration": self.duration,
                "end_time": self.end_time
            })

            await self.group_info_embed(update=True)
            end_timestamp = int(self.end_time)
            await interaction.followup.send(f"Duration extended by 1 hour. New end time: <t:{end_timestamp}:F> (<t:{end_timestamp}:R>)", ephemeral=True)
            logger.info(f"Duration extended by 1 hour. New end time: {self.end_time}. Database updated.")
        except Exception as e:
            logger.error(f"Error extending duration: {e}")
            if interaction.response.is_done():
                await interaction.followup.send("Failed to extend duration.", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to extend duration.", ephemeral=True)


    ## Callback (Not Implemented)- Speak on/off
    async def speak_toggle_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Speak Toggle feature will be implemented later.", ephemeral=True)


    ## Callback (Not Implemented)- Video on/off/force
    async def video_toggle_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Video Toggle feature will be implemented later.", ephemeral=True)


    ## Callback (Not Implemented)- Votekick
    async def votekick_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This feature will be implemented later.", ephemeral=True)


    ## Callback - Leave Group
    async def leave_group_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if interaction.user.id not in self.member_ids:
                await interaction.followup.send(f"You are not a member of '{self.name}'.", ephemeral=True)
                return
            await self.remove_member(interaction, interaction.user.id)
            await self.group_info_embed(update=True)
        except Exception as e:
            logger.error(f"Error in leave_group_callback for group '{self.name}': {e}")
            if interaction.response.is_done():
                await interaction.followup.send("An error occurred while leaving the group.", ephemeral=True)
            else:
                await interaction.response.send_message("An error occurred while leaving the group.", ephemeral=True)

    ## Callback - Refresh GUI
    async def refresh_gui_callback(self, interaction: discord.Interaction):
        try:
            await self.group_info_embed(update=True)
            await interaction.response.send_message("🔄 Study group dashboard refreshed!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error refreshing GUI for group '{self.name}': {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Failed to refresh dashboard.", ephemeral=True)

    ## Callback - Check-in Present
    async def checkin_present_callback(self, interaction: discord.Interaction):
        try:
            checkin_cog = self.bot.get_cog("CheckinCog") if self.bot else None
            checkin_session = None
            if checkin_cog:
                for s in checkin_cog.active_sessions.values():
                    if s.text_id == self.text_id:
                        checkin_session = s
                        break
            if not checkin_session:
                await interaction.response.send_message("No active Check-in session in this group. Use `/checkin` to start one!", ephemeral=True)
                return

            uid = interaction.user.id
            checkin_session.member_statuses[uid] = {"status": "present", "absences": 0}
            if uid not in checkin_session.member_ids:
                checkin_session.member_ids.append(uid)

            await self.db.add_or_update_checkin_member(checkin_session.session_id, uid, "present", 0)
            await interaction.response.send_message(f"✅ {interaction.user.mention} marked **Present** for check-in!", ephemeral=True)
            await self.group_info_embed(update=True)
        except Exception as e:
            logger.error(f"Error in checkin_present_callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Error recording check-in status.", ephemeral=True)

    ## Callback - Check-in Break
    async def checkin_break_callback(self, interaction: discord.Interaction):
        try:
            checkin_cog = self.bot.get_cog("CheckinCog") if self.bot else None
            checkin_session = None
            if checkin_cog:
                for s in checkin_cog.active_sessions.values():
                    if s.text_id == self.text_id:
                        checkin_session = s
                        break
            if not checkin_session:
                await interaction.response.send_message("No active Check-in session in this group. Use `/checkin` to start one!", ephemeral=True)
                return

            uid = interaction.user.id
            checkin_session.member_statuses[uid] = {"status": "break", "absences": 1}
            if uid not in checkin_session.member_ids:
                checkin_session.member_ids.append(uid)

            await self.db.add_or_update_checkin_member(checkin_session.session_id, uid, "break", 1)
            await interaction.response.send_message(f"☕ {interaction.user.mention} marked on **Break**!", ephemeral=True)
            await self.group_info_embed(update=True)
        except Exception as e:
            logger.error(f"Error in checkin_break_callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Error recording break status.", ephemeral=True)

    ## Callback - Pomodoro Pause/Resume
    async def pomo_toggle_callback(self, interaction: discord.Interaction):
        try:
            pomo_cog = self.bot.get_cog("Pomodoro") if self.bot else None
            pomo_session = None
            if pomo_cog:
                pomo_session = pomo_cog.sessions.get(self.group_id)
                if not pomo_session:
                    for s in pomo_cog.sessions.values():
                        if str(getattr(s, 'group_id', '')) == str(self.group_id) or (getattr(s, 'text_id', 0) and getattr(s, 'text_id', 0) == self.text_id):
                            pomo_session = s
                            break

            if not pomo_session:
                await interaction.response.send_message("No active Pomodoro session in this group. Use `/start_pomodoro` to start one!", ephemeral=True)
                return

            pomo_session.is_paused = not pomo_session.is_paused
            state_text = "paused ⏸️" if pomo_session.is_paused else "resumed ▶️"
            await interaction.response.send_message(f"Pomodoro timer {state_text}!", ephemeral=True)
            await self.group_info_embed(update=True)
        except Exception as e:
            logger.error(f"Error in pomo_toggle_callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Error toggling Pomodoro state.", ephemeral=True)

    ## Callback - Pomodoro End
    async def pomo_end_callback(self, interaction: discord.Interaction):
        try:
            if not await self.can_control(interaction.user):
                await interaction.response.send_message("You do not have permission to end the Pomodoro session for this group.", ephemeral=True)
                return

            pomo_cog = self.bot.get_cog("Pomodoro") if self.bot else None
            pomo_session = None
            if pomo_cog:
                pomo_session = pomo_cog.sessions.get(self.group_id)
                if not pomo_session:
                    for s in pomo_cog.sessions.values():
                        if str(getattr(s, 'group_id', '')) == str(self.group_id) or (getattr(s, 'text_id', 0) and getattr(s, 'text_id', 0) == self.text_id):
                            pomo_session = s
                            break

            if not pomo_session:
                await interaction.response.send_message("No active Pomodoro session in this group.", ephemeral=True)
                return

            if pomo_cog:
                pomo_cog.sessions.pop(self.group_id, None)
                pomo_cog.sessions.pop(getattr(pomo_session, 'group_id', None), None)
                if not pomo_cog.sessions and pomo_cog.run_timer.is_running():
                    pomo_cog.run_timer.stop()

            await interaction.response.send_message("Pomodoro session ended.", ephemeral=True)
            await self.group_info_embed(update=True)
        except Exception as e:
            logger.error(f"Error in pomo_end_callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Error ending Pomodoro session.", ephemeral=True)




    ### --- END FUNCTIONS --- ###
    """
    Flow of Logic - 
    End Group function is called in the following situtations:
        1. Check End Condition
            - Check if the group is active
            - Check if the group's duration has elapsed
            - Check if there are no members left
        2. User Presses End Button
            - end_group_callback function is called
    End Group Function is activated
    - It has a delay of 60 seconds
    - Then it does the following:
        - Text Channel Deletion / Permission Revoking
        - Delete Voice Channel
        - De-assign role from all members
        - Delete role
        - Clear group_data in memory (using clear_group_data function)
    """


    ## End - Check End Condition
    async def check_end_condition(self):
        """Periodically checks the end conditions for a study group and triggers the end when conditions are met."""
        try:
            logger.info(f"Started end condition check for group '{self.name}' with a duration of {parse_seconds_to_hms(self.duration)}.")

            # Continuously check the conditions
            while True:
                current_time : float = datetime.now().timestamp()

                # 1. Check if the group is marked inactive (active = False)
                if not self.active:
                    logger.info(f"Group '{self.name}' is being ended by the owner or due to manual condition.")
                    await self.end_group(delete_text_channel=False)
                    return

                # 2. Check if there are no members left in the group
                if len(self.member_ids) == 0:
                    logger.warning(f"Group '{self.name}' has no members left and is being ended.")
                    self.active = False  # Mark as inactive
                    await self.end_group(delete_text_channel=False)
                    return

                # 3. Check if the group's duration has elapsed
                if current_time >= self.end_time:
                    logger.info(f"Group '{self.name}' duration of {parse_seconds_to_hms(self.duration)} has elapsed. Ending the group.")
                    self.active = False  # Mark as inactive
                    await self.end_group(delete_text_channel=False)
                    return

                # Wait for 1 minute before checking the conditions again
                await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info(f"End condition check for group '{self.name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in checking end conditions for group '{self.name}': {e}")


    ## End - End Group Function
    async def end_group(self, delete_text_channel: bool = True, delay: int = 60):
        """End the study group by clearing data, deleting channels, removing roles, and clearing permissions."""
        try:
            if not self.guild:
                logger.error("Guild is None in end_group")
                return

            # Fetch the role, text channel, and voice channel by their IDs
            role = self.guild.get_role(self.group_role_id)
            ch_text = self.guild.get_channel(self.text_id)
            text_channel = ch_text if isinstance(ch_text, discord.TextChannel) else None
            ch_vc = self.guild.get_channel(self.vc_id)
            voice_channel = ch_vc if isinstance(ch_vc, discord.VoiceChannel) else None

            # Calculate end timestamp
            end_timestamp = int((datetime.now() + timedelta(seconds=delay)).timestamp())
            countdown_text = f"<t:{end_timestamp}:R>"

            if text_channel and delay > 0:
                role_mention = role.mention if role else f"<@&{self.group_role_id}>"
                await text_channel.send(content=f"Hey people of {role_mention}\nThe End Function will start in {delay} seconds.")
                logger.info(f"The End condition has been triggered. from this namespae: {__name__}")
                await text_channel.send(content=countdown_text)

            if delay > 0:
                await asyncio.sleep(delay)

            # 1. Handle text channel deletion or permission revoking
            if text_channel:
                if delete_text_channel:
                    try:
                        await text_channel.delete(reason="Study group ended, deleting text channel.")
                        logger.info(f"Text channel '{text_channel.name}' deleted for group '{self.name}'.")
                    except Exception as e:
                        logger.error(f"Error deleting text channel '{text_channel.name}': {e}")
                else:
                    if role:
                        try:
                            # Revoke the group's role permissions from the text channel
                            await text_channel.set_permissions(role, overwrite=None)
                            logger.info(f"Permissions revoked from text channel '{text_channel.name}' for role '{role.name}'.")
                        except Exception as e:
                            logger.error(f"Error revoking permissions in text channel '{text_channel.name}': {e}")

            # 2. Delete the voice channel
            if voice_channel:
                try:
                    await voice_channel.delete(reason="Study group ended, deleting voice channel.")
                    logger.info(f"Voice channel '{voice_channel.name}' deleted for group '{self.name}'.")
                except Exception as e:
                    logger.error(f"Error deleting voice channel '{voice_channel.name} from {self.name}': {e}")

            # 3. De-assign the role from all members
            if role:
                try:
                    for member in self.guild.members:
                        if role in member.roles:
                            await member.remove_roles(role, reason="Study group ended, removing group role.")
                    logger.info(f"Role '{role.name}' removed from all members of group '{self.name}'.")
                except Exception as e:
                    logger.error(f"Error de-assigning role '{role.name}' from members: {e}")

                # 4. Delete the role
                try:
                    await role.delete(reason="Study group ended, deleting group role.")
                    logger.info(f"Role '{role.name}' deleted for group '{self.name}'.")
                except Exception as e:
                    logger.error(f"Error deleting role '{role.name}': {e}")

            # 5. Clean up associated Pomodoro and Checkin sessions
            pomo_cog = self.bot.get_cog("Pomodoro") if self.bot else None
            if pomo_cog:
                pomo_cog.sessions.pop(self.group_id, None)
                if not pomo_cog.sessions and pomo_cog.run_timer.is_running():
                    pomo_cog.run_timer.stop()

            checkin_cog = self.bot.get_cog("CheckinCog") if self.bot else None
            if checkin_cog and self.text_id:
                for sid, s in list(checkin_cog.active_sessions.items()):
                    if s.text_id == self.text_id:
                        await s.clear_session_data()

            # 6. Delete group from database
            if self.group_id:
                await self.db.delete_study_group(self.group_id)

            # 7. Clear group data
            self.clear_group_data()
            logger.info(f"Data cleared for group '{self.name}'.")

        except Exception as e:
            logger.critical(f"Unexpected error while ending group {self.group_id}: {e}")


    ## End - Clear Class Variables / Attributes and Trackers
    def clear_group_data(self):
        """Clear all data associated with the study group."""
        try:
            # Remove instance of group from StudyGroupCog
            if self.group_id in self.cog.active_study_groups:
                self.cog.active_study_groups.pop(self.group_id)


            # Clear critical information
            self.guild_id = None
            self.name = None
            self.group_id = None
            self.creator_id = None
            self.owner_id = None
            self.category_id = None
            self.max_members = 0
            self.member_ids.clear()  # Clear member list

            # Clear IDs for roles and channels
            self.group_role_id = None
            self.vc_id = None
            self.text_id = None

            # Clear VC settings
            self.speak_enabled = None
            self.video_mode = None
            self.video_timer = None

            # Clear time-related attributes
            self.start_time = None
            self.duration = None
            self.end_time = None
            self.current_time = None

            # Clear final state
            self.active = False
            self.guild = None
            self.view = None  # Clear the View object if applicable

            logger.info(f"Group data cleared for group '{self.name}'.")
        except Exception as e:
            logger.error(f"Error clearing data for group '{self.name}': {e}")



    class VCFunctions:
        def __init__(self, study_group):
            self.study_group = study_group
            self.speak_enabled = True  # Track whether speaking is enabled in the VC
            self.video_mode = "on"  # "on", "off", or "force"
            self.video_timer = 10  # Timer for forcing video to be on, default to 10 seconds

        def create_vc(self, guild):
            """Create a voice channel for the group and return its ID."""
            # Pseudocode to create a voice channel
            vc_id = 67890  # Placeholder for the created voice channel ID
            return vc_id

        def delete_vc(self, guild):
            """Delete the voice channel when the group ends."""
            # Pseudocode to delete the voice channel
            pass

        def update_vc_permissions(self, guild):
            """Update permissions for the group's voice channel."""
            # Pseudocode to update VC permissions for the group role
            pass

        def set_speak(self, enable):
            """Enable or disable speaking in the VC."""
            self.speak_enabled = enable
            # Update the permissions in the VC to enable/disable speaking
            pass

        def set_video(self, mode):
            """Set video mode in the VC ('on', 'off', or 'force')."""
            if mode in ["on", "off", "force"]:
                self.video_mode = mode
                # Apply video permissions in the VC based on this mode
            else:
                raise ValueError("Invalid video mode")

        def force_video_timer(self, user_id):
            """Warn user to turn on video, and kick them out if they fail to do so in time."""
            # Pseudocode for tracking time and kicking user if video is not turned on
            pass



    ## Send invite message to a member
    async def send_invite(self, interaction: discord.Interaction, invited_member: discord.Member, send_channel: discord.TextChannel) -> None:
        ### Invite a user to the group
        try:
            invite_message: Optional[discord.Message] = None

            def check(interaction : discord.Interaction) -> bool:
                check_counter = interaction.message == invite_message and interaction.user == invited_member

                if check_counter:
                    logger.info(f"Interaction clicked by invited member: {interaction.user.display_name}.")
                else:
                    logger.info(f"Not correct interaction or interaction not clicked by invited member: {interaction.user.display_name}.")

                return bool(check_counter)

            await interaction.followup.send(
                f"{invited_member.display_name} has been invited to the group {self.name}.",
                ephemeral=True
            )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.green, emoji="✅", custom_id="accept"))
            view.add_item(discord.ui.Button(label="Decline", style=discord.ButtonStyle.red, emoji="❌", custom_id="decline"))

            invite_message = await send_channel.send(
                f"{invited_member.mention}, you have been invited to the group {self.name}.",
                view=view
            )

            if not self.bot:
                logger.error("Bot instance not available for waiting for interaction")
                return

            try:
                res_interaction = await self.bot.wait_for("interaction", check=check, timeout=120.0)
                custom_id = None
                if hasattr(res_interaction, 'data') and res_interaction.data:
                    if isinstance(res_interaction.data, dict):
                        custom_id = res_interaction.data.get("custom_id")
                    else:
                        custom_id = getattr(res_interaction.data, "custom_id", None)

                if custom_id == "accept":
                    # handle accept logic
                    await self.add_member(invited_member)
                    await invite_message.edit(content=f"{invited_member.mention}, you have been invited to the group {self.name}.\n You have accepted the invitation to the group {self.name} and have been added!", view=None)
                    logger.info(f"Member {invited_member.display_name} accepted the invitation to the group and has been added.")
                elif custom_id == "decline":
                    # handle decline logic
                    await self.disable_buttons(invite_message)
                    await invite_message.edit(content=f"{invited_member.mention}, you have been invited to the group {self.name}.\nYou have declined the invitation to the group {self.name}.", view=view)
                    logger.info(f"Member {invited_member.display_name} declined the invitation to the group.")
            except asyncio.TimeoutError:
                await self.disable_buttons(invite_message)
            except Exception as wait_err:
                logger.debug(f"wait_for interaction handled: {wait_err}")

        except Exception as e:
            logger.error(f"Error inviting member {invited_member.display_name} to the group: {e}")






class StudyGroupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_study_groups = {}
        logger.info("Study Group cog initialized")



    @app_commands.command(name="create_group", description="Create a new study group")
    @app_commands.describe(name="Set a name for your study group", max_members="Set the Max number of members", mentions="Mention roles or users to add", category="Category where the group channels will be created")
    async def create_group(self, interaction: discord.Interaction, name: str, mentions : str, category: discord.CategoryChannel, max_members: int = 10):
        # Defer the message to prevent delays and avoid timeouts
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        # Parsing members list into member IDs (will incorporate into parse_mentions directly later)
        mentioned_member_ids : List[int] = parse_mentions(interaction, mentions)


        # Validate parameters before proceeding
        if not await validate_parameters(
            interaction = interaction,
            name = name,
            member_ids = mentioned_member_ids,
            max_members = max_members,
            category = category,
        ):
            logger.error(f"Validation failed for {name} by user {interaction.user}")
            return          # Exit if validation fails


        study_group = StudyGroup(
            db= self.bot.db,
            cog = self,
            guild_id = interaction.guild.id,
            name = name,
            creator_id = interaction.user.id,
            category_id=category.id,
            max_members=max_members,
            member_ids=mentioned_member_ids
        )

        # Collect result messages
        result = await study_group.setup_group_resources(interaction)

        if study_group.active:
            # If the setup was successful, start the end-condition check
            asyncio.create_task(study_group.check_end_condition())

        # Add the study group to the dictionary
        self.active_study_groups[study_group.group_id] = study_group

        # Send a single message to the user with the result of the operation
        await interaction.followup.send(result, ephemeral=True)

    @app_commands.command(name="transfer_group", description="Transfer ownership of a study group to another member")
    @app_commands.describe(new_owner="The member to transfer group ownership to", group_name="The name of the study group (optional if inside group channel)")
    async def transfer_group(self, interaction: discord.Interaction, new_owner: discord.Member, group_name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        target_group: Optional[StudyGroup] = None
        if group_name:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.name.lower() == group_name.lower():
                    target_group = grp
                    break
        else:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.text_id == interaction.channel_id:
                    target_group = grp
                    break

        if not target_group:
            # Check database for active group
            db_grp = None
            if group_name:
                db_grp = await self.bot.db.fetch_study_group_by_name(group_name, str(interaction.guild.id))
            elif interaction.channel_id:
                db_grp = await self.bot.db.get_study_group_by_channel(interaction.channel_id)
            if not db_grp:
                db_grp = await self.bot.db.get_user_group(interaction.user.id, interaction.channel_id)

            if db_grp:
                is_mgr = await check_manager(interaction)
                if interaction.user.id not in (db_grp.get('creator_id'), db_grp.get('owner_id')) and not is_mgr:
                    await interaction.followup.send("You don't have permission to transfer this group.", ephemeral=True)
                    return
                grp_id = db_grp.get('group_id') or db_grp.get('id')
                await self.bot.db.transfer_ownership_study_group_db(str(grp_id), new_owner.id)
                await interaction.followup.send(f"Ownership of study group **{db_grp['name']}** transferred to {new_owner.mention}.", ephemeral=True)
                return

            await interaction.followup.send("Could not find the target study group. Please specify `group_name` or run this command inside the study group channel.", ephemeral=True)
            return

        if not await target_group.can_control(interaction.user):
            await interaction.followup.send("Only the group owner, creator, or server managers/moderators can transfer this study group.", ephemeral=True)
            return

        await target_group.transfer_ownership(interaction, new_owner.id)

    @app_commands.command(name="end_group", description="End a study group and cleanup its resources")
    @app_commands.describe(name="Name of the study group to end (optional if inside group channel)")
    async def end_group(self, interaction: discord.Interaction, name: Optional[str] = None):
        await interaction.response.defer()
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        target_group: Optional[StudyGroup] = None
        if name:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.name.lower() == name.lower():
                    target_group = grp
                    break
        else:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.text_id == interaction.channel_id:
                    target_group = grp
                    break

        if target_group:
            if not await target_group.can_control(interaction.user):
                await interaction.followup.send("You don't have permission to end this group.", ephemeral=True)
                return
            await interaction.followup.send(f"Ending study group **{target_group.name}**...")
            await target_group.end_group(delay=0)
            return

        db_grp = None
        if name:
            db_grp = await self.bot.db.fetch_study_group_by_name(name, str(interaction.guild.id))
        elif interaction.channel_id:
            db_grp = await self.bot.db.get_study_group_by_channel(interaction.channel_id)

        if not db_grp:
            await interaction.followup.send("No study group found to end.", ephemeral=True)
            return

        is_mgr = await check_manager(interaction)
        if interaction.user.id not in (db_grp.get('creator_id'), db_grp.get('owner_id')) and not is_mgr:
            await interaction.followup.send("You don't have permission to end this group.", ephemeral=True)
            return

        grp_id = db_grp.get('group_id') or db_grp.get('id')
        text_id = db_grp.get('text_id')
        vc_id = db_grp.get('vc_id')
        role_id = db_grp.get('group_role_id')

        # Clean up text channel
        if text_id:
            ch_text = interaction.guild.get_channel(text_id)
            if ch_text:
                try:
                    await ch_text.delete(reason="Study group ended from DB fallback")
                    logger.info(f"Deleted text channel {text_id} for group {grp_id}")
                except Exception as e:
                    logger.error(f"Error deleting text channel {text_id}: {e}")

        # Clean up voice channel
        if vc_id:
            ch_vc = interaction.guild.get_channel(vc_id)
            if ch_vc:
                try:
                    await ch_vc.delete(reason="Study group ended from DB fallback")
                    logger.info(f"Deleted voice channel {vc_id} for group {grp_id}")
                except Exception as e:
                    logger.error(f"Error deleting voice channel {vc_id}: {e}")

        # Clean up role
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await role.delete(reason="Study group ended from DB fallback")
                    logger.info(f"Deleted role {role_id} for group {grp_id}")
                except Exception as e:
                    logger.error(f"Error deleting role {role_id}: {e}")

        # Clean up active Pomodoro & Checkin sessions if any
        pomo_cog = self.bot.get_cog("Pomodoro") if self.bot else None
        if pomo_cog:
            pomo_cog.sessions.pop(grp_id, None)
            pomo_cog.sessions.pop(db_grp.get('id'), None)
            pomo_cog.sessions.pop(db_grp.get('group_id'), None)
            if not pomo_cog.sessions and pomo_cog.run_timer.is_running():
                pomo_cog.run_timer.stop()

        checkin_cog = self.bot.get_cog("CheckinCog") if self.bot else None
        if checkin_cog and text_id:
            for sid, s in list(checkin_cog.active_sessions.items()):
                if s.text_id == text_id:
                    await s.clear_session_data()

        await self.bot.db.delete_study_group(grp_id)
        try:
            await interaction.followup.send(f"Study group **{db_grp['name']}** and its associated channels have been ended.")
        except Exception:
            pass

    @app_commands.command(name="list_groups", description="List all active study groups in the server")
    async def list_groups(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        groups = await self.bot.db.get_all_study_groups_of_guild(interaction.guild.id)
        active_groups = [g for g in groups if g['active']]
        if not active_groups:
            await interaction.followup.send("There are no active study groups in this server.", ephemeral=True)
            return

        embed = discord.Embed(title="Active Study Groups", color=discord.Color.blue())
        for g in active_groups:
            members = await self.bot.db.fetch_members_of_group(g['group_id'] if 'group_id' in g else str(g['id']))
            embed.add_field(
                name=g['name'],
                value=f"👥 Members: {len(members)}/{g['max_members']}\nCreated by: <@{g['creator_id']}>",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join_group", description="Join an active study group")
    @app_commands.describe(name="Name of the study group to join")
    async def join_group(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        # Check in active in-memory groups first
        target_group: Optional[StudyGroup] = None
        for grp in self.active_study_groups.values():
            if grp.guild_id == interaction.guild.id and grp.name.lower() == name.lower() and grp.active:
                target_group = grp
                break

        if target_group:
            if interaction.user.id in target_group.member_ids:
                await interaction.followup.send(f"You are already in study group **{target_group.name}**.", ephemeral=True)
                return
            if len(target_group.member_ids) >= target_group.max_members:
                await interaction.followup.send(f"Study group **{target_group.name}** is currently full ({len(target_group.member_ids)}/{target_group.max_members}).", ephemeral=True)
                return
            if isinstance(interaction.user, discord.Member):
                await target_group.add_member(interaction.user)
                await target_group.group_info_embed(update=True)
                await interaction.followup.send(f"Successfully joined study group **{target_group.name}**!", ephemeral=True)
                return

        # Fallback to DB
        db_grp = await self.bot.db.fetch_study_group_by_name(name, str(interaction.guild.id))
        if not db_grp or not db_grp.get('active'):
            await interaction.followup.send(f"No active study group named '{name}' found in this server.", ephemeral=True)
            return

        grp_id = db_grp.get('group_id') or str(db_grp.get('id'))
        members = await self.bot.db.fetch_members_of_group(grp_id)
        if interaction.user.id in members:
            await interaction.followup.send(f"You are already in study group **{db_grp['name']}**.", ephemeral=True)
            return
        if len(members) >= db_grp.get('max_members', 10):
            await interaction.followup.send(f"Study group **{db_grp['name']}** is full.", ephemeral=True)
            return

        await self.bot.db.add_member_to_study_group_db(grp_id, interaction.user.id)
        role = interaction.guild.get_role(db_grp.get('group_role_id', 0))
        if role and isinstance(interaction.user, discord.Member):
            try:
                await interaction.user.add_roles(role)
            except Exception:
                pass
        await interaction.followup.send(f"Successfully joined study group **{db_grp['name']}**!", ephemeral=True)

    @app_commands.command(name="leave_group", description="Leave a study group")
    @app_commands.describe(name="Name of the study group to leave (optional if inside group channel)")
    async def leave_group(self, interaction: discord.Interaction, name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        target_group: Optional[StudyGroup] = None
        if name:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.name.lower() == name.lower():
                    target_group = grp
                    break
        else:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.text_id == interaction.channel_id:
                    target_group = grp
                    break

        if target_group:
            if interaction.user.id not in target_group.member_ids:
                await interaction.followup.send(f"You are not a member of study group **{target_group.name}**.", ephemeral=True)
                return
            await target_group.remove_member(interaction, interaction.user.id)
            await target_group.group_info_embed(update=True)
            return

        # Fallback to DB
        db_grp = None
        if name:
            db_grp = await self.bot.db.fetch_study_group_by_name(name, str(interaction.guild.id))
        elif interaction.channel_id:
            db_grp = await self.bot.db.get_study_group_by_channel(interaction.channel_id)
        if not db_grp:
            db_grp = await self.bot.db.get_user_group(interaction.user.id, interaction.channel_id)

        if not db_grp:
            await interaction.followup.send("Could not find a study group to leave.", ephemeral=True)
            return

        grp_id = db_grp.get('group_id') or str(db_grp.get('id'))
        await self.bot.db.remove_member_from_study_group_db(grp_id, interaction.user.id)
        role = interaction.guild.get_role(db_grp.get('group_role_id', 0))
        if role and isinstance(interaction.user, discord.Member):
            try:
                await interaction.user.remove_roles(role)
            except Exception:
                pass
        await interaction.followup.send(f"You have left the study group **{db_grp['name']}**.", ephemeral=True)

    @app_commands.command(name="invite_to_group", description="Invite a user to your study group")
    @app_commands.describe(user="The member to invite", group_name="The name of your study group (optional if inside group channel)")
    async def invite_to_group(self, interaction: discord.Interaction, user: discord.Member, group_name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        target_group: Optional[StudyGroup] = None
        if group_name:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.name.lower() == group_name.lower():
                    target_group = grp
                    break
        else:
            for grp in self.active_study_groups.values():
                if grp.guild_id == interaction.guild.id and grp.text_id == interaction.channel_id:
                    target_group = grp
                    break

        if not target_group:
            user_grp = await self.bot.db.get_user_group(interaction.user.id, interaction.channel_id)
            if user_grp:
                target_group = self.active_study_groups.get(user_grp.get('group_id'))

        if not target_group:
            await interaction.followup.send("Could not locate your study group. Please specify `group_name` or run inside the group text channel.", ephemeral=True)
            return

        if interaction.user.id not in target_group.member_ids and not await target_group.can_control(interaction.user):
            await interaction.followup.send(f"You must be a member or manager of **{target_group.name}** to invite others.", ephemeral=True)
            return

        if user.id in target_group.member_ids:
            await interaction.followup.send(f"{user.display_name} is already a member of **{target_group.name}**.", ephemeral=True)
            return

        if len(target_group.member_ids) >= target_group.max_members:
            await interaction.followup.send(f"Study group **{target_group.name}** has reached its capacity limit.", ephemeral=True)
            return

        ch = interaction.guild.get_channel(target_group.text_id)
        if isinstance(ch, discord.TextChannel):
            await target_group.send_invite(interaction, user, ch)
        else:
            await target_group.add_member(user, interaction)

async def setup(bot):
    await bot.add_cog(StudyGroupCog(bot))
    logger.info("StudyGroupCog loaded")



