import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import uuid
import logging
from utils import parse_duration, parse_mentions, parse_seconds_to_hms, validate_parameters
from datetime import datetime, timedelta
from discord.ui import Button, View
from typing import List, Dict
from enum import Enum

logger = logging.getLogger(__name__)

class MemberStatus(Enum):
    PRESENT = "present"  # Member is currently present
    ABSENT = "absent"
    EXITED = "exited"
    BREAK = "break"


class CheckinSession:
    min_duration = 20  # 20 seconds as the minimum duration
    max_members = 10  # 10 members are allowed max
    max_absences = 3  # max absences are 3
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

    def __init__(self, db, cog: 'CheckinCog', interaction: discord.Interaction, name: str, member_ids: List[int], duration: int):
        """Initializes a new check-in session.

        Args:
            db: The database handler instance.
            cog (CheckinCog): The CheckinCog instance this session belongs to.
            interaction (discord.Interaction): The interaction that triggered the session.
            name (str): The name of the check-in session.
            member_ids (List[int]): A list of member IDs participating in the session.
            duration (int): The duration of the check-in session in seconds.

        Attributes:
            guild_id (int): The ID of the guild where the session is running.
            name (str): The name of the check-in session.
            session_id (str): A unique ID for the session.
            creator_id (int): The ID of the user who created the session.
            owner_id (int): The ID of the session owner (initially the creator).
            text_id (int): The ID of the text channel where the session is managed.
        """
        self.guild_id : int = interaction.guild.id
        self.name : str = name
        self.session_id : str = self.generate_session_id()
        self.creator_id : int = interaction.user.id
        self.owner_id : int = self.creator_id
        self.text_id : int = interaction.channel.id
        self.member_ids : List[int] = member_ids
        self.duration : int = duration
        self.start_time : float = datetime.now().timestamp()
        self.last_reminder_time: float = datetime.now().timestamp()
        self.next_reminder_time : float = (datetime.now() + timedelta(seconds=duration)).timestamp()
        self.last_reminder_message_id : int = None
        self.reminder_count : int = 0

        self.max_sessions_per_user = 5

        self.member_statuses = {member_id : {"status" : MemberStatus.PRESENT, "absences" : 0} for member_id in self.member_ids}

        # Other stuff, not stored in Database
        self.cog : CheckinCog = cog
        self.db = db
        self.guild : discord.Guild = interaction.guild
        logger.info(f"Check-in session '{self.name}' created with ID: {self.session_id}, duration: {self.duration} seconds, "
                    f"members: {self.member_ids}, created by: {self.creator_id} in guild: {self.guild_id}")

    def generate_session_id(self) -> str:
        """Generates a unique session ID using UUID.

        Returns:
            str: A unique session ID.
        """
        return str(uuid.uuid4())

    async def setup_checkin_resources(self):
        """Sets up the check-in session by saving session details and member statuses to the database.

        Raises:
            Exception: If any error occurs during the database operations.
        """
        try:
            session_data = {
                "session_id": self.session_id,
                "guild_id": self.guild_id,
                "name": self.name,
                "creator_id": self.creator_id,
                "owner_id": self.owner_id,
                "text_channel_id": self.text_id,
                "duration": self.duration,
                "start_time": self.start_time,
                "last_reminder_time": self.last_reminder_time,
                "next_reminder_time": self.next_reminder_time,
                "reminder_count": self.reminder_count,
                "last_reminder_message_id": self.last_reminder_message_id,
                "active": 1  # Active sessions are marked as 1 (True)
            }

            await self.db.add_checkin_session(session_data)
            logger.info(f"Session '{self.name}' (ID: {self.session_id}) details saved to the database.")

            for member_id, data in self.member_statuses.items():
                await self.db.add_or_update_checkin_member(
                    self.session_id, member_id, data["status"].value, data["absences"]
                )
            logger.debug(f"Members' statuses for session '{self.name}' (ID: {self.session_id}) saved to the database.")

        except Exception as e:
            logger.error(f"Failed to setup check-in resources for session '{self.name}' (ID: {self.session_id}): {e}")
            raise  # Re-raise the exception to be handled by the caller

    def increment_reminder(self) -> None:
        """Increments the reminder count for the session and updates the database.

        Raises:
            Exception: If there is an error updating the session in the database.
        """
        try:
            self.reminder_count += 1
            asyncio.create_task(self.db.update_checkin_session({
                "session_id": self.session_id,
                "reminder_count": self.reminder_count,
                "last_reminder_message_id": self.last_reminder_message_id,
                "active": 1
            }))
            logger.info(f"Incremented reminder count for session '{self.name}' (ID: {self.session_id}) to {self.reminder_count}.")
        except Exception as e:
            logger.error(f"Failed to increment reminder count for session '{self.name}' (ID: {self.session_id}): {e}")
            raise

    async def update_member_statuses(self):
        """Updates the statuses of members in the check-in session.

        Moves members from 'PRESENT' to 'ABSENT', increments absences for 'ABSENT' members,
        and marks members as 'EXITED' if they exceed the maximum allowed absences.

        Raises:
            Exception: If there is an error updating member statuses in the database.
        """
        try:
            for member_id, data in self.member_statuses.items():
                if data["status"] == MemberStatus.PRESENT:
                    self.member_statuses[member_id]["status"] = MemberStatus.ABSENT  # Move to absent
                    self.member_statuses[member_id]["absences"] = 0  # Reset absences
                    logger.info(f"Member {member_id} moved to ABSENT in session '{self.name}' (ID: {self.session_id}).")

                elif data["status"] == MemberStatus.ABSENT:
                    self.member_statuses[member_id]["absences"] += 1  # Increment absences
                    logger.info(
                        f"Incremented absences for member {member_id} in session '{self.name}' (ID: {self.session_id}) to "
                        f"{self.member_statuses[member_id]['absences']}."
                    )

                    if self.member_statuses[member_id]["absences"] >= CheckinSession.max_absences:
                        self.member_statuses[member_id]["status"] = MemberStatus.EXITED  # Mark as exited
                        self.member_statuses[member_id]["absences"] = 0  # Reset absences
                        if member_id in self.member_ids:
                            self.member_ids.remove(member_id)  # Remove from active members
                        logger.info(
                            f"Member {member_id} EXITED session '{self.name}' (ID: {self.session_id}) due to exceeding max absences."
                        )

            await self._bulk_update_member_statuses()  # Update statuses in the database
            logger.debug(f"Member statuses updated for session '{self.name}' (ID: {self.session_id}).")

        except Exception as e:
            logger.error(f"Failed to update member statuses for session '{self.name}' (ID: {self.session_id}): {e}")

    async def _bulk_update_member_statuses(self):
        """Helper function to bulk update member statuses in the database.

        Raises:
            Exception: If there is an issue with the database update.
        """
        try:
            updates = []
            for member_id, data in self.member_statuses.items():
                updates.append({
                    "session_id": self.session_id,
                    "member_id": member_id,
                    "status": data["status"].value,
                    "absences": data["absences"]
                })
            await self.db.bulk_update_checkin_members(updates)
            logger.debug(f"Bulk updated member statuses in database for session '{self.name}' (ID: {self.session_id}).")
        except Exception as e:
            logger.error(f"Failed to bulk update member statuses in database for session '{self.name}' (ID: {self.session_id}): {e}")
            raise

    async def add_or_update_member(self, member_id: int, status: MemberStatus, absences: int = 0):
        """Adds or updates a member's status in the check-in session.

        Args:
            member_id (int): The ID of the member.
            status (MemberStatus): The new status of the member.
            absences (int): The number of absences for the member (default: 0).

        Raises:
            Exception: If there is an error updating the member in the database.
        """
        try:
            self.member_statuses[member_id] = {"status": status, "absences": absences}
            if status != MemberStatus.EXITED and member_id not in self.member_ids:
                self.member_ids.append(member_id)
            await self.db.add_or_update_checkin_member(self.session_id, member_id, status.value, absences)
            logger.info(
                f"Updated status for member {member_id} in session '{self.name}' (ID: {self.session_id}) to {status.name} "
                f"with {absences} absences."
            )
        except Exception as e:
            logger.error(f"Failed to update member {member_id} in session '{self.name}' (ID: {self.session_id}): {e}")
            raise

    def create_embed(self, initial: bool = False) -> discord.Embed:
        """Creates an embed for the check-in session."""

        try:
            member_objs = [self.guild.get_member(member_id) for member_id in self.member_ids]
            present_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status["status"] == MemberStatus.PRESENT]
            absent_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status["status"] == MemberStatus.ABSENT]
            exited_objs = [self.guild.get_member(member_id) for member_id, status in self.member_statuses.items() if status["status"] == MemberStatus.EXITED]
            creator = self.guild.get_member(self.creator_id)

            # Create the embed for the session
            embed = discord.Embed(
                title="Let's get started!" if initial else random.choice(self.prompt_messages),
                color=discord.Color.blue(),
                description=f"Reminder No: {self.reminder_count}"
            )
            embed.set_author(name=f"{self.name}")
            embed.add_field(name="Check-in Started", value=f"<t:{int(self.start_time.timestamp())}:R>", inline=True)
            embed.add_field(name="Duration", value=f"{parse_seconds_to_hms(self.duration)}", inline=True)
            embed.add_field(name="Members", value=", ".join([member_obj.mention for member_obj in member_objs]), inline=False)

            # Present
            embed.add_field(
                name="Present",
                value="\n".join([present_obj.mention for present_obj in present_objs]) or "No one yet!",
                inline=True
            )

            # Absent
            absent_members = [
                f"{absent_obj.mention} ({self.member_statuses.get(absent_obj.id, {}).get('absences', 0)} Absences)" if self.member_statuses[absent_obj.id]['absences'] >= CheckinSession.max_absences - 1 else absent_obj.mention
                for absent_obj in absent_objs
            ]
            embed.add_field(name="Absent", value="\n".join(absent_members) or "Everyone is Present!", inline=True)

            # Exited/Dropped
            embed.add_field(
                name="Exited/Dropped",
                value="\n".join([exited_obj.mention for exited_obj in exited_objs]) or "None",
                inline=True
            )

            embed.set_footer(text=f"Created by {creator.display_name}")

            return embed
        except Exception as e:
            logger.error(f"Failed to create embed: {e}")
            return discord.Embed(title="Error", description="An error occurred while creating the embed.", color=discord.Color.red())  # Return an error embed

    # Embed Function - Update Embed
    async def update_embed(self) -> None:
        # Update the message embed after any interaction. 
        try:
            if self.last_reminder_message_id:
                text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
                reminder_message : discord.Message = await text_channel.fetch_message(self.last_reminder_message_id)
                embed = self.create_embed()
                await reminder_message.edit(embed=embed)
        except Exception as e:  # Broad exception handling
            logger.error(f"Failed to update embed: {e}")


    # Message Function - Disable Previous Buttons
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
                logger.debug("Disabled buttons in the previous reminder message.")
        except discord.NotFound:
            logger.warning(f"Previous reminder message not found (ID: {self.last_reminder_message_id})")
        except discord.HTTPException as e:
            logger.error(f"Failed to disable buttons in previous reminder message: {e}")
        except Exception as e:  # Catch other exceptions
            logger.error(f"Unexpected error disabling buttons: {e}")

    # Message Function - Send Reminder Message
    async def send_reminder_message(self):
        """Sends a reminder message with the current session status."""
        try:
            text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
            members : List[discord.Member] = [self.guild.get_member(member_id) for member_id in self.member_ids if member_id in self.member_statuses]
            members_mention_msg = ", ".join([member.mention for member in members])

            embed = self.create_embed()  # Create embed
            button_view = self.create_buttons()  # Create buttons
            message = await text_channel.send(content=members_mention_msg, embed=embed, view=button_view)  # Send message with embed and buttons

            self.last_reminder_message_id = message.id  # Store message ID
            logger.info(f"Reminder message sent for session: {self.name} (ID: {self.session_id})")

        except Exception as e:
            logger.error(f"Failed to send reminder message: {e}")


    async def run_checkin_reminders(self):
        """Manages the reminder loop for the check-in session."""
        try:
            while self.session_id in self.cog.active_sessions:
                
                # Calculate how much time to sleep until the next reminder
                now = datetime.now().timestamp()
                time_until_next_reminder = self.next_reminder_time - now
                
                if time_until_next_reminder > 0:
                    await asyncio.sleep(time_until_next_reminder)

                # 1. Disable buttons of previous message
                if self.last_reminder_message_id:
                    await self.disable_previous_buttons()
                
                # 2. Update Member statuses
                await self.update_member_statuses()  # Update member statuses before sending reminders
                
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
                await self.send_reminder_message()  # Send next reminder

                # 5. Update reminder times
                self.last_reminder_time = datetime.now().timestamp()
                self.next_reminder_time = self.last_reminder_time + self.duration

                # 6. Increment reminder count
                self.increment_reminder()  # Increment reminder count

                # Update session in the db
                await self.db.update_checkin_session({
                    "session_id": self.session_id,
                    "last_reminder_time": self.last_reminder_time,
                    "next_reminder_time": self.next_reminder_time,
                    "reminder_count": self.reminder_count
                })

                logger.debug(f"Reminder {self.reminder_count} sent with updated members.")
        except Exception as e:
            logger.error(f"Failed in run_checkin_reminders: {e}")  # More specific error message


    """Button Functions"""

    def create_buttons(self, initial=False) -> discord.ui.View:
        try:    
            # Create the buttons    
            present_button : discord.Button = Button(label='Present', style=discord.ButtonStyle.success)
            join_button : discord.Button = Button(label='Join', style=discord.ButtonStyle.primary)
            leave_button : discord.Button = Button(label='Leave', style=discord.ButtonStyle.danger)
            end_button : discord.Button = Button(label='End', style=discord.ButtonStyle.secondary)

            # Assign callbacks
            present_button.callback = self.mark_present_callback
            join_button.callback = self.join_session_callback
            leave_button.callback = self.leave_session_callback
            end_button.callback = self.end_session_callback

            # Create View
            view = discord.ui.View()
            if not initial:
                view.add_item(present_button)
            view.add_item(join_button)
            view.add_item(leave_button)
            view.add_item(end_button)

            return view
        except Exception as e:
            logger.error(f"Failed to create buttons: {str(e)}")
            return discord.ui.View()

    ## Button Function - Mark Present
    async def mark_present_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            logger.info(f"Mark present initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id
            # Mark present and update absent list
            if (user_id not in self.member_ids) or (user_id not in self.member_statuses) or (self.member_statuses.get(user_id, {}).get("status") == MemberStatus.EXITED):
                await interaction.response.send_message(f"You are not part of this session.", ephemeral=True)
                return

            if self.member_statuses.get(user_id, {}).get("status") == MemberStatus.PRESENT:
                await interaction.response.send_message("You are already marked as present.", ephemeral=True)
                return

            self.member_statuses[user_id]["status"] = MemberStatus.PRESENT
            self.member_statuses[user_id]["absences"] = 0

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, MemberStatus.PRESENT.value, 0)

            await interaction.followup.send("You are marked as present.", ephemeral=True)
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
            
            if (user_id in self.member_ids) or (user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get("status")!= MemberStatus.EXITED):
                await interaction.followup.send("You are already in the session.", ephemeral=True)
                return

            if user_id in self.member_statuses and self.member_statuses.get(user_id, {}).get("status") == MemberStatus.EXITED:
                self.member_statuses[user_id]["status"] = MemberStatus.PRESENT
                self.member_statuses[user_id]["absences"] = 0
            else:
                self.member_statuses[user_id] = {"status" : MemberStatus.PRESENT, "absences" : 0}
                self.member_ids.append(user_id)

            # Save to DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, MemberStatus.PRESENT.value, 0)
            
            await interaction.followup.send("You have joined the session.", ephemeral=True)
            await self.update_embed()
        
        except Exception as e:
            logger.error(f"Failed to join session for user: {interaction.user.display_name}: {str(e)}")
            await interaction.followup.send(f"Failed to join session. {str(e)}", ephemeral=True)


    ## Button Function - Leave Session
    async def leave_session_callback(self, interaction : discord.Interaction):
        # Remove user from the session and update absent and members lists
        try:
            await interaction.response.defer()
            logger.info(f"Leave session initiated by {interaction.user.display_name} for session {self.session_id}.")

            user_id : int = interaction.user.id
            
            if user_id not in self.member_statuses or self.member_statuses.get(user_id, {}).get("status") == MemberStatus.EXITED:
                await interaction.followup.send("You are not in the session.", ephemeral=True)
                return

            # Mark the user as exited and remove them from active members
            self.member_statuses[user_id]["status"] = MemberStatus.EXITED
            self.member_statuses[user_id]["absences"] = 0
            self.member_ids.remove(user_id)

            # Update DB
            await self.db.add_or_update_checkin_member(self.session_id, user_id, MemberStatus.EXITED.value, 0)
            
            await interaction.followup.send("You have left the session.", ephemeral=True)
            await self.update_embed()

        except Exception as e:
            logger.error(f"Failed to leave session for user: {interaction.user.display_name}: {str(e)}")
            await interaction.followup.send(f"Failed to leave session. {str(e)}", ephemeral=True)
        

    ## Button Function - End Session
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

            await self.clear_session_data()  # Call clear_session_data

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
            # Delete session data from the database
            await self.db.delete_checkin_session(self.session_id)
            
            logger.info(f"Deleted session data from the database for session: {self.name} (ID: {self.session_id})")

            # Clear in-memory data
            self.member_ids.clear()
            self.member_statuses.clear()
            self.last_reminder_message_id = 0
            self.reminder_count = 0
            
            # Remove session from the active sessions list
            self.cog.active_sessions.pop(self.session_id)
            
            logger.debug(f"Session data for session name {self.name} and Session ID: {self.session_id} cleared successfully.")
        except Exception as e:  # Catch-all for exceptions
            logger.error(f"Failed to clear session data: {e}")
            raise  # Re-raise the exception


class CheckinCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db):  # Add db parameter
        """Initializes the CheckinCog with the bot instance and database handler."""
        self.bot : commands.Bot = bot
        self.db = db  # Store the database handler
        self.active_sessions = {}  # Use a dictionary to store active sessions by session_id
        asyncio.create_task(self.load_active_sessions_from_db())  # Start loading sessions asynchronously
        logger.debug("Check-in Cog initialized.")

    async def load_active_sessions_from_db(self):
        """Loads active sessions from the database and starts their reminder loops."""

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
                        "status": MemberStatus(member['status']),
                        "absences": member['absences']
                    }
                    for member in member_statuses
                }
                
                # Create a new CheckinSession object
                session = CheckinSession(
                    db=self.db,
                    cog=self,
                    interaction=None,  # Interaction is not available during bot restart
                    name=session_data["name"],
                    member_ids=[m["member_id"] for m in member_statuses],
                    duration=session_data["duration"]
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
                delay = random.uniform(30, 150)
                await asyncio.sleep(delay)
                asyncio.create_task(session.run_checkin_reminders())  # Start the reminder loop

                logger.info(f"Loaded check-in session from DB and started reminder loop: {session.name} (ID: {session.session_id})")

            logger.info(f"Loaded {len(active_sessions)} active sessions from the database.")

        except Exception as e:
            logger.error(f"Failed to load active sessions: {e}")

    @app_commands.command(name='checkin', description='Starts a check-in session with specified duration and mentions.')
    @app_commands.describe(name= 'Name of the Checkin Session', duration='The duration of the check-in session in format \'2d 14h 25m 30s\'', mentions='The users/roles to be included in the check-in session.')
    async def start_checkin(self, interaction: discord.Interaction, name: str, mentions: str, duration: str):
        """Starts a new check-in session."""
        await interaction.response.defer()
        logger.info(f"Starting check-in session: {name}")

        duration_seconds = parse_duration(duration)  # Convert duration string to seconds
        member_ids = parse_mentions(interaction, mentions)  # Extract member IDs from mentions

        # Input validation
        if not await validate_parameters(interaction, name, member_ids, duration, CheckinSession.max_members):
            logger.warning(f"Validation failed for check-in session: {name}")
            return

        try:
            session = CheckinSession(
                db=self.db,
                cog=self,
                interaction=interaction,
                name=name,
                member_ids=member_ids,
                duration=duration_seconds)
            await session.setup_checkin_resources()  # Save session and member data to the database
            self.active_sessions[session.session_id] = session  # Track active session
            logger.info(f"Check-in session with ID {session.session_id} started by {interaction.user.display_name} in channel {interaction.channel.id}.")

            await session.send_reminder_message()  # Send initial reminder
        except Exception as e:
            logger.error(f"Failed to start check-in session: {e}")
            await interaction.followup.send(f"Failed to start check-in session: {e}", ephemeral=True)  # Provide feedback to the user

