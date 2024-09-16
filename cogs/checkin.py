import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils import parse_duration, parse_mentions, parse_seconds_to_hms, generate_custom_id, parse_custom_id
import asyncio
import logging
import random
import uuid
import sys
from discord.ui import Button, View
from typing import List

# Setting up basic configuration for logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
current_namespace = sys.modules[__name__].__name__.split('.')[-1]


class CheckinSession:
    min_duration = 20  # 20 seconds as the minimum duration
    max_members = 10  # 10 members are allowed max
    max_absences = 3  # max absences are 3

    def __init__(self, interaction : discord.Interaction, members : List[discord.Member], duration : str, cog: 'CheckinCog'):
        self.session_id = self.generate_session_id()
        self.creator = interaction.user
        self.text_channel = interaction.channel  # Store the channel ID where the session was created
        self.members = members
        self.start_time = datetime.now()
        self.duration = duration
        self.absences = {member: 0 for member in members}
        self.present = members[:]  # All members are present by default at start
        self.exited = []
        self.last_reminder_message: discord.Message = None  # Track the last reminder message
        self.reminder_count = 0
        self.max_sessions_per_user = 5
        self.guild = interaction.guild
        self.cog : CheckinCog = cog
        self.prompt_messages = [
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
        logger.debug("Check-in session created with duration: %s seconds", duration)

    ## Helper Function - Generate Session ID
    def generate_session_id(self):
        return str(uuid.uuid4())  # Generates a random unique session ID
    
    
    """Attendance Functions"""

    ## Attendance Function - Increment Reminder Count
    def increment_reminder(self) -> None:
        self.reminder_count += 1
        logger.debug(f"Incremented reminder count to: {self.reminder_count}")
    
    
    ## Attendance Function - Move People to Absent
    def move_to_absent(self) -> List[discord.Member]:
        # Move all present members to absent at the start of each reminder. 
        self.present = []
        logger.debug("Moving members to absent.")
        return self.members  # Everyone is absent until marked present again


    ## Attendance Function - Update Absences List
    def update_absences(self) -> List[discord.Member]:
        # Increment absences for members in the Absent list. 
        removed_members : List[discord.Member] = []
        for member in self.members:
            if member not in self.present:
                self.absences[member] += 1
                logger.debug("Incrementing absence for member: %s", member.display_name)
            if self.absences[member] >= 3:
                removed_members.append(member)
        for member in removed_members:
            self.members.remove(member)
            del self.absences[member]
            self.exited.append(member)
            logger.info("Member removed due to absences: %s", member.display_name)
        return removed_members



    """Button Functions"""


    ## Button Function - Create Buttons
    def create_buttons(self, initial=False) -> discord.ui.View:
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
    


    """Button Functions"""

    ## Button Function - Mark Present
    async def mark_present_callback(self, interaction: discord.Interaction):
        user : discord.Member = interaction.user
        # Mark present and update absent list
        if user in self.exited or user not in self.members:
            await interaction.response.send_message(f"You are not part of this session.", ephemeral=True)
            return

        if user in self.present:
            await interaction.response.send_message("You are already marked as present.", ephemeral=True)
            return

        self.present.append(user)
        self.absences[user] = 0
        await interaction.response.send_message("You are marked as present.", ephemeral=True)
        await self.update_embed()


    ## Button Function - Join Session
    async def join_session_callback(self, interaction : discord.Interaction):
        user : discord.Member = interaction.user
        if user in self.members:
            await interaction.response.send_message("You are already in the session.", ephemeral=True)
            return

        if user in self.exited:
            self.exited.remove(user)

        self.members.append(user)
        self.present.append(user)
        self.absences[user] = 0

        await interaction.response.send_message("You have joined the session.", ephemeral=True)
        await self.update_embed()


    ## Button Function - Leave Session
    async def leave_session_callback(self, interaction : discord.Interaction):
        # Remove user from the session and update absent and members lists
        user : discord.Member = interaction.user
        if user in self.present:
            self.present.remove(user)
        if user in self.members:
            self.members.remove(user)
            self.exited.append(user)
            del self.absences[user]
            await interaction.response.send_message("You have left the session.", ephemeral=True)
            await self.update_embed()
            return
        await interaction.response.send_message("You are not in the session", ephemeral=True)
        

    ## Button Function - End Session
    async def end_session_callback(self, interaction: discord.Interaction):
        logger.info(f"End session initiated by {interaction.user.display_name} for session {self.session_id}.")

        if not self.can_end(interaction.user):
            await interaction.response.send_message("Only the session creator can end the session.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Check-in Session Ended",
            description=f"The session has been manually ended by {self.creator.display_name}.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Session created by {self.creator.display_name}")

        try:
            await interaction.channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error(f"Failed to send end session message for session {self.session_id}: {str(e)}")

        await self.clear_session_data()
        await self.disable_previous_buttons(interaction.channel)

        logger.info(f"Check-in session {self.session_id} successfully ended by {interaction.user.display_name}.")
        await interaction.response.send_message("Check-in session has been manually ended.", ephemeral=True)


    """Message Functions"""

    ## Embed Function - Create Embed
    def create_embed(self, initial=False):    
        # Create the embed for the session. 
        embed = discord.Embed(
            title="Let's get started!" if initial else random.choice(self.prompt_messages),
            color=discord.Color.blue()
        )
        embed.set_author(name=f"{self.creator.display_name}'s Check-in session")
        embed.add_field(name="Check-in Started", value=f"<t:{int(self.start_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Duration", value=f"{parse_seconds_to_hms(self.duration)}", inline=True)
        embed.add_field(name="Members", value=", ".join([member.mention for member in self.members]), inline=False)

        # Present
        embed.add_field(
            name="Present",
            value="\n".join([member.mention for member in self.present]) or "No one yet!",
            inline=True
        )
        # Absent
        absent_members = [
            f"{member.mention} ({self.absences[member]})" if self.absences[member] >= CheckinSession.max_absences - 1 else member.mention
            for member in self.members if member not in self.present
        ]
        embed.add_field(name="Absent", value="\n".join(absent_members) or "Everyone is Present!", inline=True)

        # Exited/Dropped
        embed.add_field(
            name="Exited/Dropped",
            value="\n".join([member.mention for member in self.exited]) or "None",
            inline=True
        )
        embed.set_footer(text=f"Created by {self.creator.display_name}")

        return embed


    ## Embed Function - Update Embed
    async def update_embed(self) -> None:
        # Update the message embed after any interaction. 
        if self.last_reminder_message:

            embed = self.create_embed()
            await self.last_reminder_message.edit(embed=embed)
    
    
    ## Message Function - Send Initial Message
    async def send_initial_message(self):
        embed = self.create_embed(initial=True)
        view = self.create_buttons(initial=True)
        initial_message = await self.text_channel.send(embed=embed, view=view)

        self.last_reminder_message = initial_message

        # Start the reminder loop
        self.cog.bot.loop.create_task(self.run_checkin_reminders())


    ## Message Function - Send Reminder Message
    async def run_checkin_reminders(self):
        while True:
            await asyncio.sleep(self.duration)

            self.increment_reminder()
            await self.disable_previous_buttons(self.text_channel)

            self.move_to_absent()
            removed_members = self.update_absences()

            if not self.members:
                embed = discord.Embed(
                    title="Check-in Session Ended",
                    description="No more members are left in the session.",
                    color=discord.Color.red()
                )
                logger.info("Session ended due to no remaining members.")
                await self.text_channel.send(embed=embed)
                return

            members_mention_msg = ", ".join([member.mention for member in self.members])
            embed = self.create_embed()
            view = self.create_buttons()
            reminder_message = await self.text_channel.send(content=members_mention_msg, embed=embed, view=view)

            self.last_reminder_message = reminder_message
            logger.info(f"Reminder {self.reminder_count} sent with updated members.")


    ## Message Function - Disable Previous Buttons    
    async def disable_previous_buttons(self, channel: discord.TextChannel):
        if self.last_reminder_message:
            try:
                last_message = await channel.fetch_message(self.last_reminder_message.id)
                new_view = View()

                for component in last_message.components:
                    for item in component.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True
                            new_view.add_item(item)

                await last_message.edit(view=new_view)
                logger.info("Disabled buttons in the previous reminder message.")

            except discord.NotFound:
                logger.warning(f"Previous reminder message not found (ID: {self.last_reminder_message.id}).")
            except discord.HTTPException as e:
                logger.error(f"Failed to disable buttons in previous reminder message: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error disabling buttons: {str(e)}")
    


    """End Session Helper Functions"""
    ## Helper Function - Can End
    def can_end(self, user):
        # Determine if the user can end the session.
        return user == self.creator

    ## Helper Function - Clear Session Data
    async def clear_session_data(self):
        # Clear all session data explicitly to avoid any future interaction
        self.members.clear()
        self.present.clear()
        self.exited.clear()
        self.absences.clear()
        self.last_reminder_message = None
        self.reminder_count = 0
        self.cog.active_sessions.pop(self.session_id)
        logger.debug(f"Session data for session {self.session_id} cleared successfully.")






class CheckinCog(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        logger.debug("Check-in Cog initialized.")



    """Cog Commands & Events"""
    
    ## Command - /checkin
    @app_commands.command(name='checkin', description='Starts a check-in session with specified duration and mentions.')
    async def start_checkin(self, interaction : discord.Interaction, duration: str, *, mentions: str):
        # Parse the duration
        duration_seconds = parse_duration(duration)
        # Parse mentions (users/roles)
        members = parse_mentions(interaction, mentions)
        
        # Check - Wrong format entered, hence function returned None
        if duration_seconds == None:
            logger.warning("Wrong duration format entered.")
            await interaction.response.send_message(f"Wrong duration format used. Use \'2d 14h 25m 30s\' or use day(s) hour(s)/hr(s) minute(s)/min(s) second(s)/sec(s)", ephemeral=True)
            return
        # Check - Duration entered is too short
        if duration_seconds < CheckinSession.min_duration:
            logger.warning("Attempted to start a session with insufficient duration.")
            await interaction.response.send_message(f"Duration must be at least {parse_seconds_to_hms(CheckinSession.min_duration)}", ephemeral=True)
            return

        # Check - Too many members
        if len(members) > CheckinSession.max_members:
            logger.warning("Attempted to start a session with too many members.")
            await interaction.response.send_message(f"A session can't have more than {CheckinSession.max_members} members.")
            return

        # Check - Valid members
        if not members:
            logger.error("No valid members found for check-in session.")
            await interaction.response.send_message("No valid members found in the mentions. Please mention valid users or roles.", ephemeral=True)
            return

        
        # Create a new session and save it
        session = CheckinSession(interaction = interaction, members=members, duration=duration_seconds, cog=self)
        self.active_sessions[session.session_id] = session  # Store session by its ID
        logger.info(f"Check-in session with ID {session.session_id} started by {interaction.user.display_name} in channel {interaction.channel.id}.")

        # Send the initial message with buttons
        await session.send_initial_message()


"""Setup Bot"""
async def setup(bot):
    await bot.add_cog(CheckinCog(bot))
    logger.info("CheckinCog loaded successfully.")
