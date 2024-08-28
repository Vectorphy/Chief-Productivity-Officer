import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from utils import parse_seconds_to_hms, parse_duration, parse_mentions, is_manager, app_is_manager
import logging
import uuid
from typing import List
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StudyGroup:
    def __init__(self, guild: discord.Guild, name: str, creator_id: int, category_id: int, max_size: int = 10):
        # Initializes the StudyGroup class.
        self.guild : discord.Guild = guild                          # Store the guild object for future use
        self.guild_id : int = guild.id                              # Guild ID for reference
        self.group_id : str = self.generate_group_id()              # Unique Group ID using UUID v4
        self.name : str = name                                      # Group name
        self.category_id : int = category_id                        # Category ID for the group
        self.max_size : int = max_size                              # Maximum number of members in the group
        self.group_role_id: int = 0                                 # Role ID for the group's members
        self.vc_id: int = 0                                         # Voice channel ID
        self.text_id: int = 0                                       # Text channel ID
        self.start_time : datetime = datetime.now()                 # Start time of Group
        self.curernt_time : datetime = datetime.now()               # Sets the current time of the study group
        self.duration = 12*60*60                                    # Default duration is 12 hours
        self.active: bool = True                                    # Boolean to track if the group is active

        # Initialize the Membership management class
        self.membership = self.Membership(self, creator_id, max_size)

    def generate_group_id(self) -> str:
        # Generate a unique UUID v4 for the group
        return str(uuid.uuid4())
    
    def generate_custom_id(self, button_id : str) -> str:
        ### Generate custom IDs for buttons and selection menus
        return f"{button_id}_{self.group_id}"

    
    @classmethod
    async def create_group(cls, interaction: discord.Interaction, name: str, max_size: int, mentions: str, category: discord.CategoryChannel):
        """Create a new study group and return the instance, handling errors with ephemeral messages."""
        logger.info(f"Creating group '{name}' for creator {interaction.user.display_name} in guild {interaction.guild.name}")

        # Validate max_size
        if max_size <= 0:
            await interaction.response.send_message(f"Invalid max_size: {max_size}. It must be a positive number.", ephemeral=True)
            return None

        # Parse mentions
        try:
            mentioned_members = parse_mentions(interaction, mentions)
            if not mentioned_members:
                await interaction.response.send_message("No valid members found in the mentions. Please mention valid users or roles.", ephemeral=True)
                return None
            if len(mentioned_members) > max_size:
                await interaction.response.send_message(f"Too many members specified. Max allowed: {max_size}.", ephemeral=True)
                return None
            logger.info(f"Parsed mentions: {[member.display_name for member in mentioned_members]}")
        except Exception as e:
            logger.error(f"Error parsing mentions: {e}")
            await interaction.response.send_message(f"Error parsing mentions: {e}", ephemeral=True)
            return None

        # Check if a category is provided
        if category is None:
            await interaction.response.send_message("No category specified. Please provide a valid category.", ephemeral=True)
            return None

        # Create the group role
        try:
            group_role = await interaction.guild.create_role(name=f"{name} Group", reason="Role for study group")
            logger.info(f"Role '{group_role.name}' created for group '{name}'")
        except Exception as e:
            logger.error(f"Error creating role for group '{name}': {e}")
            await interaction.response.send_message(f"Error creating role for the group: {e}", ephemeral=True)
            return None

        # Create the text and voice channels under the specified category
        try:
            text_channel = await category.create_text_channel(name=f"{name}-text", reason="Text channel for study group")
            voice_channel = await category.create_voice_channel(name=f"{name}-voice", reason="Voice channel for study group")
            logger.info(f"Channels created for group '{name}': text - {text_channel.name}, voice - {voice_channel.name}")
        except Exception as e:
            logger.error(f"Error creating channels for group '{name}': {e}")
            await interaction.response.send_message(f"Error creating channels for the group: {e}", ephemeral=True)
            return None

        # Sync permissions for the group role
        try:
            await text_channel.set_permissions(group_role, read_messages=True, send_messages=True)
            await voice_channel.set_permissions(group_role, connect=True, speak=True)
            logger.info(f"Permissions set for role '{group_role.name}' in the text and voice channels.")
        except Exception as e:
            logger.error(f"Error setting permissions for group '{name}': {e}")
            await interaction.response.send_message(f"Error setting permissions: {e}", ephemeral=True)
            return None

        # Initialize the StudyGroup object
        study_group = cls(
            guild=interaction.guild, 
            name=name, 
            creator_id=interaction.user.id, 
            category_id=category.id,
            max_size=max_size
        )

        # Assign the role, text, and voice channels to the group
        study_group.group_role_id = group_role.id
        study_group.text_id = text_channel.id
        study_group.vc_id = voice_channel.id

        # Add the mentioned members to the group
        try:
            for member in mentioned_members:
                await study_group.membership.add_member(member)
            logger.info(f"Added {len(mentioned_members)} members to group '{name}'")
        except Exception as e:
            logger.error(f"Error adding members to group '{name}': {e}")
            await interaction.response.send_message(f"Error adding members: {e}", ephemeral=True)
            return None

        # Send a welcome message in the text channel
        try:
            study_group.MessageFunctions(study_group ).send_welcome_message(text_channel)
            logger.info(f"Welcome message sent for group '{name}'")
            study_group.MessageFunctions(study_group).send_button_interaction_message(text_channel)
            logger.info(f"Button Interaction message sent to group '{name}'")
        except Exception as e:
            logger.error(f"Error sending welcome message for group '{name}': {e}")
            await interaction.response.send_message(f"Error sending welcome message: {e}", ephemeral=True)

        return study_group
    

    
    class Membership:
        def __init__(self, study_group: 'StudyGroup', creator_id: int, max_size: int):
            self.study_group = study_group                          # Reference to the parent StudyGroup class
            self.owner_id: int = creator_id                         # Group owner ID
            self.members: List[int] = []                            # List of member IDs
            self.max_size: int = max_size                           # Maximum number of members


        def is_owner(self, user: discord.Member) -> bool:
            ### Check if the given user is the owner of the group
            return self.owner_id == user.id


        def is_member(self, user : discord.Member) -> bool:
            ### Check if the given user is a member of the group
            return user.id in self.members


        async def add_member(self, member: discord.Member) -> None:
            ### Add a member to the group
            try:
                if len(self.members) < self.max_size:
                    # Retrieve the member and add the group role
                    await member.add_roles(discord.Object(id=self.study_group.group_role_id))
                    logger.info(f"Member {member.display_name} added to the group {self.study_group.name}.")
                    self.members.append(member.id)
                else:
                    raise Exception(f"Group is full with No. of Members: {len(self.members)} and Max members: {self.max_size}.")
            except Exception as e:
                logger.error(f"Error adding member {member.id}: {e}")


        async def remove_member(self, member : discord.Member) -> None:
            ### Remove a member from group
            try:
                if member.id in self.members:
                    if member:
                        await member.remove_roles(discord.Object(id=self.study_group.group_role_id))  # Remove group role
                        self.members.append(member.id)
                        logger.info(f"Member {member.display_name} removed from the group {self.study_group.name}.")
                    else:
                        logger.warning(f"Member with ID {member.id} not found in the guild.")
                else:
                    raise Exception("Member not found in the group")
            except Exception as e:
                logger.error(f"Error removing member {member.id}: {e}")


        async def transfer_ownership(self, interaction, new_owner: discord.Member) -> None:
            ### Transfer ownership of the group to another member
            try:
                # Check if the user who did the interaction is the current owner
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message("You're not the owner of the group.", ephemeral=True)
                    return
                
                if new_owner.id in self.members:
                    await interaction.response.send_message(content=f"Ownership transferred to from {self.study_group.guild.get_member(self.owner_id).mention} to {new_owner.mention}.")
                    self.owner_id = new_owner.id
                    logger.info(f"Ownership of group {self.study_group.name} transferred to {new_owner.display_name}.")
                else:
                    await interaction.response.send_message("New owner must be a member of the group.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error transferring ownership: {e}")




    def sync_permissions(self):
        ### Sync permissions across the text and voice channels based on the group role
        # Pseudocode:
        # Sync permissions for VC and text channel, allowing only group members to access
        pass


    async def check_end_conditions(self):
        """Checks end conditions for a study group and ends it if necessary."""
        try:
            group_duration = 12 * 60 * 60  # 12 hours in seconds
            end_time = self.start_time + datetime.timedelta(seconds=group_duration)
            logger.info(f"End condition check started for group '{self.name}' with a duration of 12 hours.")

            while True:
                if not self.active:
                    logger.info(f"Group '{self.name}' is being ended by the owner or due to end conditions.")
                    await self.end_group(self.group_id, delete_text_channel=False)  # Example usage
                    return

                if len(self.membership.members) == 0:
                    logger.warning(f"Group '{self.name}' ended because no members are left.")
                    self.active = False  # Mark the group as inactive
                    await self.end_group(self.group_id, delete_text_channel=False)
                    return

                current_time = datetime.datetime.now()
                if current_time >= end_time:
                    logger.info(f"Group '{self.name}' has reached the end of its 12-hour duration.")
                    self.active = False
                    await self.end_group(self.group_id, delete_text_channel=True)
                    return

                await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error checking end conditions for group '{self.name}': {e}")



    async def end_condition_check(self):
        """Periodically checks the end conditions for a study group and triggers the end when conditions are met."""
        try:
            # Define group duration (12 hours by default)
            group_duration = 12 * 60 * 60  # 12 hours in seconds
            end_time = self.start_time + datetime.timedelta(seconds=group_duration)

            logger.info(f"Started end condition check for group '{self.name}' with a 12-hour duration.")

            # Continuously check the conditions
            while True:
                # 1. Check if the group is marked inactive (active = False)
                if not self.active:
                    logger.info(f"Group '{self.name}' is being ended by the owner or due to manual condition.")
                    await self.end_group(self.group_id, delete_text_channel=False)  # or True, based on your choice
                    return

                # 2. Check if there are no members left in the group
                if len(self.membership.members) == 0:
                    logger.warning(f"Group '{self.name}' has no members left and is being ended.")
                    self.active = False  # Mark as inactive
                    await self.end_group(self.group_id, delete_text_channel=False)
                    return

                # 3. Check if the group's duration has elapsed
                current_time = datetime.datetime.now()
                if current_time >= end_time:
                    logger.info(f"Group '{self.name}' duration of 12 hours has elapsed. Ending the group.")
                    self.active = False  # Mark as inactive
                    await self.end_group(self.group_id, delete_text_channel=True)
                    return

                # Wait for 1 minute before checking the conditions again
                await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info(f"End condition check for group '{self.name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in checking end conditions for group '{self.name}': {e}")



    async def end_group(self, group_id: str, delete_text_channel: bool = False):
        """End the study group by clearing data, deleting channels, removing roles, and clearing permissions."""
        try:
            # Fetch the study group from the dictionary using the group_id
            study_group = self.study_groups.get(group_id)

            if not study_group:
                logger.warning(f"Group with ID {group_id} not found.")
                return

            guild = study_group.guild
            role_id = study_group.group_role_id
            text_channel_id = study_group.text_id
            voice_channel_id = study_group.vc_id

            # Fetch the role, text channel, and voice channel by their IDs
            role = guild.get_role(role_id)
            text_channel = guild.get_channel(text_channel_id)
            voice_channel = guild.get_channel(voice_channel_id)

            # 1. Handle text channel deletion or permission revoking
            if text_channel:
                if delete_text_channel:
                    try:
                        await text_channel.delete(reason="Study group ended, deleting text channel.")
                        logger.info(f"Text channel '{text_channel.name}' deleted for group '{study_group.name}'.")
                    except Exception as e:
                        logger.error(f"Error deleting text channel '{text_channel.name}': {e}")
                else:
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
                    logger.info(f"Voice channel '{voice_channel.name}' deleted for group '{study_group.name}'.")
                except Exception as e:
                    logger.error(f"Error deleting voice channel '{voice_channel.name}': {e}")

            # 3. De-assign the role from all members
            if role:
                try:
                    for member in guild.members:
                        if role in member.roles:
                            await member.remove_roles(role, reason="Study group ended, removing group role.")
                    logger.info(f"Role '{role.name}' removed from all members of group '{study_group.name}'.")
                except Exception as e:
                    logger.error(f"Error de-assigning role '{role.name}' from members: {e}")

                # 4. Delete the role
                try:
                    await role.delete(reason="Study group ended, deleting group role.")
                    logger.info(f"Role '{role.name}' deleted for group '{study_group.name}'.")
                except Exception as e:
                    logger.error(f"Error deleting role '{role.name}': {e}")

            # 5. Clear group data
            self.clear_group_data(study_group)
            logger.info(f"Data cleared for group '{study_group.name}'.")

            # 6. Remove the group from the dictionary
            del self.study_groups[group_id]
            logger.info(f"Group '{study_group.name}' with ID {group_id} successfully ended and removed.")

        except Exception as e:
            logger.critical(f"Unexpected error while ending group {group_id}: {e}")

    def clear_group_data(self, study_group):
        """Clear all data associated with the study group."""
        try:
            study_group.membership.members.clear()  # Clear member list
            study_group.group_role_id = None
            study_group.text_id = None
            study_group.vc_id = None
            study_group.active = False
            logger.info(f"Group data cleared for group '{study_group.name}'.")
        except Exception as e:
            logger.error(f"Error clearing data for group '{study_group.name}': {e}")





    # Helper Classes for Text, VC, and Messaging Functions

    class TextFunctions:
        def __init__(self, study_group):
            self.study_group = study_group

        def create_text_channel(self, guild):
            """Create a text channel for the group and return its ID."""
            # Pseudocode to create a text channel
            text_channel_id = 12345  # Placeholder for the created text channel ID
            return text_channel_id

        def delete_text_channel(self, guild):
            """Delete the text channel when the group ends."""
            # Pseudocode to delete the text channel
            pass

        def update_text_permissions(self, guild):
            """Update permissions for the group's text channel."""
            # Pseudocode to update text channel permissions
            pass

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

    class MessageFunctions:
        def __init__(self, study_group):
            self.study_group = study_group

        def send_welcome_message(self, channel):
            """Send a welcome message when the group is created."""
            # Pseudocode for sending a welcome message
            pass

        def send_group_info_embed(self, channel):
            """Send an embedded message with group information."""
            # Pseudocode to send an embedded message
            pass


        
        ## Disable buttons of a given message
        async def disable_buttons(self, message: discord.Message) -> None:
            ### Disable all buttons in the given message
            view = discord.ui.View()
            for item in message.components:
                item.disabled = True
            await message.edit(view=view)

        ## Send Button Interaction Message
        
    
    # Button Interactions (part of MessageFunctions or handled by the bot)
    async def send_button_interaction_message(self, send_channel : discord.TextChannel) -> None:
        # Get the group data
        group = self.study_group

        # Create the embed
        embed = discord.Embed(title=group.name)
        embed.description = f"This group is for studying and people are gonna study hard in this!!!\nThere are buttons below to help members and owner deal with stuff."
        embed.add_field(name="Text Channel", value=group.text_channel.mention)
        embed.add_field(name="Voice Channel", value=group.voice_channel.mention)
        embed.add_field(name="Creator", value=group.creator.display_name, inline=True)
        embed.add_field(name="Owner", value=group.owner.display_name, inline=True)
        embed.add_field(name="Group Role", value=group.role.mention)
        embed.add_field(name="No of. Members", value=len(group.members), inline=True)
        embed.add_field(name="Max Size", value=group.max_size, inline=True)
        embed.add_field(name="Group Duration", value=group.duration, inline=True)
        

        # Create the buttons and selection menus
        view = discord.ui.View()
        
        # First line: Leave, Votekick, and End Group
        view.add_item(discord.ui.Button(label="Leave Group", custom_id=group.generate_custom_id("leave_group")))
        view.add_item(discord.ui.Button(label="Votekick", custom_id=group.generate_custom_id("votekick")))
        view.add_item(discord.ui.Button(label="End Group", custom_id=group.generate_custom_id("end_group")))

        # Second line: Speak and Video
        speak_view = discord.ui.View()
        speak_view.add_item(discord.ui.Button(label="Speak On/Off", custom_id=group.generate_custom_id("speak_toggle")))
        video_view = discord.ui.View()
        video_view.add_item(discord.ui.Button(label="Video On/Off/Force", custom_id=group.generate_custom_id("video_toggle")))

        # Third line: Select menus
        # select_view = discord.ui.View()
        # select_view.add_item(discord.ui.Select(placeholder="Invite members", custom_id=group.generate_custom_id("invite_members")))
        # select_view.add_item(discord.ui.Select(placeholder="Kick members", custom_id=group.generate_custom_id("kick_members")))

        # Add the views to the parent view
        view.add_item(speak_view)
        view.add_item(video_view)
        # view.add_item(select_view)

        # Send the message
        await send_channel.send(content=f"Embed for Button Interactions",embed=embed, view=view)

        ## Send invite message to a member
        async def send_invite(self, interaction, invited_member: discord.Member, send_channel: discord.TextChannel) -> None:
            ### Invite a user to the group
            try:
                def check(interaction):
                    check_counter = interaction.message == invite_message and interaction.user == invited_member

                    if check_counter:
                        logger.info(f"Interaction clicked by invited member: {interaction.user.display_name}.")
                    else:
                        logger.info(f"Not correct interaction or interaction not clicked by invited member: {interaction.user.display_name}.")

                    return check_counter

                await interaction.response.send_message(
                    f"{invited_member.display_name} has been invited to the group {self.study_group.name}.",
                    ephemeral=True
                )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.green, emoji="✅", custom_id=self.study_group.generate_custom_id("accept")))
                view.add_item(discord.ui.Button(label="Decline", style=discord.ButtonStyle.red, emoji="❌", custom_id=self.study_group.generate_custom_id("decline")))

                invite_message = await send_channel.send(
                    f"{invited_member.mention}, you have been invited to the group {self.study_group.name}.",
                    view=view
                )

                interaction = await self.bot.wait_for("interaction", check=check)
                if interaction.data.custom_id == "accept":
                    # handle accept logic
                    await self.study_group.add_member(invited_member)
                    await invite_message.edit(content=f"{invited_member.mention}, you have been invited to the group {self.study_group.name}.\n You have accepted the invitation to the group {self.study_group.name} and have been added!", view=None)
                    logger.info(f"Member {invited_member.display_name} accepted the invitation to the group and has been added.")
                elif interaction.data.custom_id == "decline":
                    # handle decline logic
                    self.disable_buttons(invite_message)
                    await invite_message.edit(content=f"{invited_member.mention}, you have been invited to the group {self.study_group.name}.\nYou have declined the invitation to the group {self.study_group.name}.", view=view)
                    logger.info(f"Member {invited_member.display_name} declined the invitation to the group.")

            except Exception as e:
                logger.error(f"Error inviting member {invited_member.display_name} to the group: {e}")

        async def send_votekick_message(self, interaction):
            await interaction.response.send_message("Votekick is not implemented yet.", ephemeral=True)

        async def send_speak_toggle_message(self, interaction):
            await interaction.response.send_message("Speak On/Off is not implemented yet.", ephemeral=True)

        async def send_video_toggle_message(self, interaction):
            await interaction.response.send_message("Video On/Off/Force is not implemented yet.", ephemeral=True)

        async def send_show_hide_group_message(self, interaction):
            await interaction.response.send_message("Show/Hide Group is not implemented yet.", ephemeral=True)

    def rename_group(self, new_name):
        """Rename the group."""
        self.name = new_name

    def extend_duration(self, additional_time):
        """Extend the duration of the group's activity."""
        pass






class StudyGroupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.study_groups = {}
        logger.info("Study Group cog initialized")



    @app_commands.command(name="create_group", description="Create a new study group")
    @app_commands.describe(name="Set a name for your study group", max_size="Set the Max number of members", mentions="Mention roles or users to add", category="Category where the group channels will be created")
    async def create_group(self, interaction: discord.Interaction, name: str, max_size: int = 10, mentions: str = None, category: discord.CategoryChannel = None):
        try:
            # Attempt to create the study group using the StudyGroup class
            study_group = await StudyGroup.create_group(
                interaction,      # Pass interaction, no need for guild or creator explicitly
                name=name,
                max_size=max_size,
                mentions=mentions,
                category=category
            )

            # Store the created group
            self.study_groups[study_group.group_id] = study_group

            # Start the end_condition_check task for this group
            self.bot.loop.create_task(study_group.end_condition_check())

            # Send confirmation to the user
            await interaction.response.send_message(f"Study group '{name}' has been created.", ephemeral=True)

        except ValueError as ve:
            logger.error(f"Validation error during group creation: {ve}")
            await interaction.response.send_message(str(ve), ephemeral=True)
        except Exception as e:
            logger.critical(f"Unexpected error during group creation: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    
    @commands.Cog.listener()
    async def on_component(self, interaction: discord.Interaction):
        try:
            # Extract action and group ID from the interaction's custom ID
            action, group_id = interaction.custom_id.split("_")
            logger.info(f"Action: {action}")
            logger.info(f"GroupID: {group_id}")
            
            # Fetch the study group from the study_groups dictionary
            group = self.study_groups.get(group_id)

            # Check if the group exists
            if not group:
                logger.warning(f"Group with ID {group_id} does not exist.")
                await interaction.response.send_message("This group does not exist.", ephemeral=True)
                return

            # Check if the user is a member of the group
            if interaction.user.id not in group.membership.members:
                logger.warning(f"{interaction.user.display_name} tried to perform an action in a group they are not a member of: Group {group.name}")
                await interaction.response.send_message("You are not a member of this group.", ephemeral=True)
                return

            # Handle the actions based on the button or interaction clicked
            if action == "leave_group":
                await self.leave_group(interaction, group)
            elif action == "end_group":
                await self.end_group(interaction, group)
            elif action == "transfer_owner":
                await self.transfer_owner(interaction, group)
            elif action == "invite_members":
                await self.invite_members(interaction, group)
            elif action == "kick_member":
                await self.kick_member(interaction, group)
            else:
                logger.warning(f"Unknown action '{action}' received for group {group_id}.")
                await interaction.response.send_message("Unknown action. Please try again.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error processing component interaction: {e}")
            await interaction.response.send_message(f"An error occurred while processing your request: {e}", ephemeral=True)

 

async def setup(bot):
    await bot.add_cog(StudyGroupCog(bot))
    logger.info("StudyGroups cog loaded")
