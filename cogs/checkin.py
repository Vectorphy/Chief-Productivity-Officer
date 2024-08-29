import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils import parse_duration, parse_mentions, parse_seconds_to_hms, generate_custom_id, parse_custom_id
import asyncio
import logging
import random
import uuid

# Setting up basic configuration for logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CheckinSession:
    min_duration = 20  # 20 seconds as the minimum duration
    max_members = 10  # 10 members are allowed max
    max_absences = 3  # max absences are 3

    def __init__(self, session_id, creator, channel_id, members, duration):
        self.session_id = session_id  # Unique session ID
        self.creator = creator
        self.channel_id = channel_id  # Store the channel ID where the session was created
        self.members = members
        self.start_time = datetime.now()
        self.duration = duration
        self.absences = {member: 0 for member in members}
        self.present = members[:]  # All members are present by default at start
        self.exited = []
        self.last_reminder_message: discord.Message = None  # Track the last reminder message
        self.reminder_count = 0
        self.max_sessions_per_user = 5
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

    """Helper and Update Functions"""

    
    ## Helper Function - Increment Reminder Count
    def increment_reminder(self):
        self.reminder_count += 1
    
    
    ## Helper Function - Move People to Absent
    def move_to_absent(self):
        # Move all present members to absent at the start of each reminder. 
        self.present = []
        logger.debug("Moving members to absent.")
        return self.members  # Everyone is absent until marked present again


    ## Helper Function - Update Absences List
    def update_absences(self):
        # Increment absences for members in the Absent list. 
        removed_members = []
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

    ## Button Function - Mark Present
    def mark_present(self, user):
        # Mark present and update absent list
        if user in self.exited or user not in self.members:
            return "You are not part of this session."

        if user in self.present:
            return "You are already marked as present."

        self.present.append(user)
        self.absences[user] = 0
        return "You are marked as present."


    ## Button Function - Join Session
    def join_session(self, user):
        
        if user in self.members:
            return "You are already in the session."

        if user in self.exited:
            self.exited.remove(user)

        self.members.append(user)
        self.present.append(user)
        self.absences[user] = 0

        return "You have joined the session."


    ## Button Function - Leave Session
    def leave_session(self, user):
        # Remove user from the session and update absent and members lists

        if user in self.present:
            self.present.remove(user)
        if user in self.members:
            self.members.remove(user)
            self.exited.append(user)
            del self.absences[user]
            return "You have left the session."
        return "You are not in the session. based on members check"

    ## Button Function - End Session
    async def end_session(self, interaction: discord.Interaction, bot: commands.Bot, button_session_id: str, session):
        # End the session and send the final message
        logger.info(f"End session initiated by {interaction.user.display_name} for session {button_session_id}.")

        # Verify that the user is the creator
        if not session.can_end(interaction.user):
            return "Only the session creator can end the session."

        # Send a final message to the channel indicating the session has ended
        embed = discord.Embed(
            title="Check-in Session Ended",
            description=f"The session has been manually ended by {session.creator.display_name}.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Session created by {session.creator.display_name}")

        try:
            # Send the final message to the channel
            logger.debug(f"Sending final end session message in session {button_session_id}.")
            await interaction.channel.send(embed=embed)

        except discord.HTTPException as e:
            logger.error(f"Failed to send end session message for session {button_session_id}: {str(e)}")

        cog = bot.get_cog("CheckinCog")
        # Disable the buttons of the last reminder message
        if cog:
            if button_session_id in cog.active_sessions:
                logger.info(f"Deleting session for session ID {button_session_id} from active_sessions.")
                del cog.active_sessions[button_session_id]
                # Explicitly clear the session's data
                await self.clear_session_data()
            else:
                logger.warning(f"Tried to delete session for session ID {button_session_id} but it was already deleted.")

            # Disable buttons in the last reminder message using the method from the CheckinCog class
            try:
                # Disable buttons in the last reminder message using the method from the CheckinCog class
                await cog.disable_previous_buttons(session, interaction.channel)
                logger.info(f"End Session Function: Successfully disabled previous buttons in session {button_session_id}.")
            except discord.HTTPException as e:
                logger.error(f"End Session Function: Failed to disable previous buttons in session {button_session_id}: {str(e)}")
            except Exception as e:
                logger.error(f"End Session Function: An error occurred while disabling previous buttons in session {button_session_id}: {str(e)}")



        # Send a confirmation message to the creator (optional)
        logger.info(f"Check-in session {button_session_id} successfully ended by {interaction.user.display_name}.")

        # Return the response message for the user
        return f"Check-in session has been manually ended by {session.creator.mention}."
    
    

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
        logger.debug(f"Session data for session {self.session_id} cleared successfully.")






class CheckinCog(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        logger.debug("Check-in Cog initialized.")

    

    """Helper Functions"""

    ## Helper Function - Generate Session ID
    def generate_session_id(self):
        return str(uuid.uuid4())  # Generates a random unique session ID
    
    ## Helpper Function - Check if the user is in ANY session
    async def check_session_exists(self, session_id: str, interaction: discord.Interaction) -> CheckinSession:
        # Check if a session exists by session ID
        session: CheckinSession = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session with ID {session_id} does not exist.")
            await interaction.response.send_message("The session you're interacting with no longer exists.", ephemeral=True)
            return None
        return session

    ## Helper Function - Check if user is in session (Optional)
    async def check_user_in_session(self, session: CheckinSession, user: discord.User, interaction: discord.Interaction) -> bool:
        # Check if the user is part of the session
        if user not in session.members:
            logger.info(f"User {user.display_name} tried to interact with a session they're not part of.")
            await interaction.response.send_message("You are not part of this session.", ephemeral=True)
            return False
        return True



    """Embed & Button Functions"""

    ## Embed Function - Create Embed
    def create_embed(self, session : CheckinSession, initial=False):    
        # Create the embed for the session. 
        embed = discord.Embed(
            title="Let's get started!" if initial else random.choice(session.prompt_messages),
            color=discord.Color.blue()
        )
        embed.set_author(name=f"{session.creator.display_name}'s Check-in session #{len(self.active_sessions)}")
        embed.add_field(name="Check-in Started", value=f"<t:{int(session.start_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Duration", value=f"{parse_seconds_to_hms(session.duration)}", inline=True)
        embed.add_field(name="Members", value=", ".join([member.mention for member in session.members]), inline=False)

        # Present
        embed.add_field(
            name="Present",
            value="\n".join([member.mention for member in session.present]) or "No one yet!",
            inline=True
        )
        # Absent
        absent_members = [
            f"{member.mention} ({session.absences[member]})" if session.absences[member] >= CheckinSession.max_absences - 1 else member.mention
            for member in session.members if member not in session.present
        ]
        embed.add_field(name="Absent", value="\n".join(absent_members) or "Everyone is Present!", inline=True)

        # Exited/Dropped
        embed.add_field(
            name="Exited/Dropped",
            value="\n".join([member.mention for member in session.exited]) or "None",
            inline=True
        )
        embed.set_footer(text=f"Created by {session.creator.display_name}")

        return embed


    ## Embed Function - Update Embed
    async def update_embed(self, message, session : CheckinSession):
        # Update the message embed after any interaction. 
        embed = self.create_embed(session)
        await message.edit(embed=embed)
    

    ## Button Function - Create Buttons
    def create_buttons(self, session : CheckinSession, initial=False):
        # Create the button view for the session. 
        view = discord.ui.View()

        if not initial:
            view.add_item(discord.ui.Button(label='Present', style=discord.ButtonStyle.success, custom_id=f'present_{session.session_id}'))

        view.add_item(discord.ui.Button(label='Join', style=discord.ButtonStyle.primary, custom_id=f'{generate_custom_id("join",session.session_id)}'))
        view.add_item(discord.ui.Button(label='Leave', style=discord.ButtonStyle.danger, custom_id=f'generate_custom_id("leave",session.session_id)'))
        view.add_item(discord.ui.Button(label='End', style=discord.ButtonStyle.secondary, custom_id=f'{generate_custom_id("end",session.session_id)}'))

        return view
    


    """Message Functions"""

    ## Message Function - Send Initial Message
    async def send_initial_message(self, channel, session : CheckinSession):
        # Create and send the initial message
        embed = self.create_embed(session, initial=True)
        view = self.create_buttons(session, initial=True)
        initial_message = await channel.send(embed=embed, view=view)

        session.last_reminder_message = initial_message

        # Start the reminder loop
        self.bot.loop.create_task(self.run_checkin_reminders(channel, session))


    ## Message Function - Send Reminder Message
    async def run_checkin_reminders(self, channel, session : CheckinSession):    

        while session.session_id in self.active_sessions:
            await asyncio.sleep(session.duration)

            # Check if session still exists in active_sessions
            if session.session_id not in self.active_sessions:
                logger.info(f"Session {session.session_id} has ended and was removed. Stopping reminder loop.")
                return  # Break out of the reminder loop since the session has ended.
            
            logger.info(f"Session {session.session_id} exists and it continues.")
            
            # Increment reminder_count
            session.increment_reminder()

            # First, disable the buttons of the previous reminder message
            await self.disable_previous_buttons(session, channel)

            # Move present members to absent, update absences, and handle removals
            session.move_to_absent()
            removed_members = session.update_absences()

            # If no members left, end the session
            if not session.members:
                embed = discord.Embed(
                    title="Check-in Session Ended",
                    description="No more members are left in the session.",
                    color=discord.Color.red()
                )
                logger.info("Session ended due to no remaining members.")
                await channel.send(embed=embed)
                return

            members_mention_msg = ", ".join([member.mention for member in session.members])
            # Send the reminder message
            embed = self.create_embed(session)
            view = self.create_buttons(session)
            reminder_message = await channel.send(content = members_mention_msg, embed=embed, view=view)

            session.last_reminder_message = reminder_message

            logger.info(f"Reminder {session.reminder_count} sent with updated members.")


    ## Message Function - Disable Previous Buttons    
    async def disable_previous_buttons(self, session: CheckinSession, channel: discord.TextChannel):
        
        # Disable the buttons in the last reminder message, if it exists
        if session.last_reminder_message:
            try:
                # Fetch the last reminder message from the channel
                last_message = await channel.fetch_message(session.last_reminder_message.id)

                # Create a new view
                new_view = discord.ui.View()

                # Loop through the components and disable the buttons
                for component in last_message.components:
                    for item in component.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True  # Disable each button
                            new_view.add_item(item)  # Add the disabled button to the new view

                # Edit the last reminder message to disable the buttons
                await last_message.edit(view=new_view)
                logger.info("Disabled buttons in the previous reminder message.")

            except discord.NotFound:
                logger.warning(f"Previous reminder message not found (ID: {session.last_reminder_message.id}).")
            except discord.HTTPException as e:
                logger.error(f"Failed to disable buttons in previous reminder message: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error disabling buttons: {str(e)}")




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

        # Check - User exceeded max sessions
        user_sessions = [sid for sid, s in self.active_sessions.items() if s.creator == interaction.user and s.channel_id == interaction.channel.id]
        if len(user_sessions) >= 5:  # Arbitrary limit, change as needed
            await interaction.response.send_message(f"{interaction.user.display_name}, you already have the maximum number of active sessions in this channel.")
            return
        
        # Add - Add creator in the members list
        if interaction.user not in members:
            members.append(interaction.user)
        
        # Generate a unique session ID for the new session
        session_id = self.generate_session_id()
        
        # Create a new session and save it
        session = CheckinSession(session_id=session_id, creator=interaction.user, channel_id=interaction.channel.id, members=members, duration=duration_seconds)
        self.active_sessions[session_id] = session  # Store session by its ID
        logger.info(f"Check-in session with ID {session_id} started by {interaction.user.display_name} in channel {interaction.channel.id}.")

        # Send the initial message with buttons
        await self.send_initial_message(interaction.channel, session)


    
    ## Listener - Button Clicks
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        result = ""
        button_session_id = ""
        session: CheckinSession = None

        if interaction.type != discord.InteractionType.component:
            return  # Ignore non-button interactions

        custom_id = interaction.custom_id
        namespace, action, button_session_id = parse_custom_id(custom_id)

        # Ensure the custom_id belongs to this module
        current_namespace = __name__.split('.')[-1]
        if namespace != current_namespace:
            logger.warning(f"Interaction doesn't belong to: {current_namespace}. Interaction belongs to another namespace: {namespace}")
            return

        session = await self.check_session_exists(button_session_id, interaction)
        if not session:
            return  # Session does not exist, message already sent

        if namespace != "checkin":
            logger.info(f"Button interacted was not from 'checkin' module, it was from {namespace} module ")
            return

        if session:
            # Handle Present Button
            if action == 'present':
                result = session.mark_present(interaction.user)

            # Handle Join Button
            elif action == 'join':
                result = session.join_session(interaction.user)

            # Handle Leave Button
            elif action == 'leave':
                result = session.leave_session(interaction.user)

            # Handle End Button
            elif action == 'end':
                logger.debug(f"User {interaction.user.display_name} clicked the 'End' button for session {button_session_id}.")

                # Retrieve the session using session_id
                session =  self.active_sessions.get(button_session_id)

                # Check if the user has permission to end the session (must be the creator)
                if session and session.can_end(interaction.user):
                    
                    try:
                        # Disable buttons in the last reminder message using the method from the CheckinCog class
                        await self.disable_previous_buttons(session, interaction.channel)
                        logger.info(f"Cog Event Listener: Successfully disabled previous buttons in session {button_session_id}.")
                    except discord.HTTPException as e:
                        logger.error(f"Cog Event Listener: Failed to disable previous buttons in session {button_session_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Cog Event Listener: An error occurred while disabling previous buttons in session {button_session_id}: {str(e)}")
                    
                    logger.info(f"User {interaction.user.display_name} is the creator and has permission to end the session.")
                    response = await session.end_session(interaction, self.bot, button_session_id, session)
                    
                    logger.debug("Sending response message to the user indicating the session was ended.")
                    await interaction.response.send_message(response)
                    
                    logger.info("Session ended successfully. No further interaction will be processed.")
                    return
                
                else:
                    # If the user is not the creator or session is not found, log the denial
                    logger.warning(f"User {interaction.user.display_name} tried to end the session but is not the creator or session does not exist.")
                    result = "Only the session creator can end the session."

        # If there's a result, send it as a follow-up
        if result:
            await interaction.response.defer()
            await interaction.followup.send(result, ephemeral=True)

        # Update the embed after the interaction
        await self.update_embed(interaction.message, session)




"""Setup Bot"""
async def setup(bot):
    await bot.add_cog(CheckinCog(bot))
    logger.info("CheckinCog loaded successfully.")
