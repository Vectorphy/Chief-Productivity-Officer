import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from utils import parse_seconds_to_hms, parse_mentions, validate_parameters
import logging
import uuid
from typing import List
from datetime import datetime, timedelta
import sys
from database import DBHandler
from discord.ui import View, Button, Select, Modal, TextInput
import time

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
        self.db : DBHandler = db
        self.guild : discord.Guild = None
        self.view : View = None




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
            await text_channel.set_permissions(self.guild.get_role(self.group_role_id), read_messages=True, send_messages=True)
            await voice_channel.set_permissions(self.guild.get_role(self.group_role_id), connect=True, speak=True)

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
                    await member.add_roles(self.guild.get_role(self.group_role_id))
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
                ###  "member_ids": self.member_ids,  # List of Member ID, not used in this table anymore, it's store in study_groups_members
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
    async def add_member(self, interaction: discord.Interaction, user_id: int) -> None:
        ### Add a member to the group
        try:
            if len(self.member_ids) >= self.max_members:
                logger.warning(f"Group is full with No. of Members: {len(self.member_ids)} and Max members: {self.max_members}.")
                await interaction.followup.send(f"This group is full with No. of Members: {len(self.member_ids)}", ephemeral=True)
                return

            if user_id in self.member_ids:
                logger.warning(f"Member with ID {user_id} already in the group.")
                await interaction.followup.send(f"Member with ID {user_id} already in the group.", ephemeral=True)
                return

            member : discord.Member = self.get_member(user_id)
            if not member:
                logger.warning(f"Member with ID {user_id} not found in the guild.")
                await interaction.followup.send(f"Member with ID {user_id} not found.", ephemeral=True)
                return

            group_role : discord.Role = self.guild.get_role(self.group_role_id)
            # Retrieve the member and add the group role
            await member.add_roles(group_role)
            self.member_ids.append(user_id)

            # Update the database after adding the member
            await self.db.add_member_to_study_group_db(self.group_id, user_id)

            logger.info(f"Member {member.display_name} added to the group {self.name}.")
            await interaction.followup.send(f"Member {member.display_name} added to the group.", ephemeral=True)
            return

        except Exception as e:
            logger.error(f"Error adding member {member.id}: {e}")
            await interaction.followup.send(f"Error adding member {user_id} to group {self.name}.", ephemeral=True)
            return 


    ## Membership - Remove Member from Group
    async def remove_member(self, interaction: discord.Interaction, user_id : int) -> None:
        ### Remove a member from group
        try:
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


    ## Membership - Transfer Ownership
    async def transfer_ownership(self, interaction : discord.Interaction, new_owner_id : int) -> None:
        ### Transfer ownership of the group to another member
        try:
            # Check - user who did the interaction is current owner
            if interaction.user.id != self.owner_id:
                logger.warning(f"User {interaction.user.display_name} is not the owner of the group '{self.name}'.")
                await interaction.followup.send("You're not the owner of the group.", ephemeral=True)
                return
            # Check - if new owner is the current owner
            if new_owner_id == self.owner_id:
                logger.warning(f"User {interaction.user.display_name} is already the owner of the group '{self.name}'.")
                await interaction.followup.send("You're already the owner of the group.", ephemeral=True)
                return
            
            new_owner : discord.Member = interaction.guild.get_member(new_owner_id)
            # Check - if new owner is in the guild
            if not new_owner:
                logger.warning(f"Member with ID {new_owner_id} not found in the guild.")
                await interaction.followup.send(f"Member with ID {new_owner_id} not found.", ephemeral=True)
                return

            # Check - if new owner is part of the study group
            if new_owner_id not in self.member_ids:
                logger.warning(f"Member with ID {new_owner_id} and usern is not part of the group '{self.name}'.")
                await interaction.followup.send(f"Member with ID {new_owner_id} is not part of the group.", ephemeral=True)
                return

            # Transfer ownership
            await interaction.followup.send(content=f"Ownership transferred to from {interaction.user.mention} to {new_owner.mention}.")
            self.owner_id = new_owner_id
            
            # Update the database after transferring ownership
            await self.db.transfer_ownership_study_group_db(self.group_id, new_owner_id)
            await self.group_info_embed(update=True)

            logger.info(f"Ownership of group {self.study_group.name} transferred to from {interaction.user.display_name} to {new_owner.display_name}.", ephemeral=True)
            return
            
        except Exception as e:
            logger.error(f"Error transferring ownership: {e}")


    

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
            text_channel: discord.TextChannel = self.guild.get_channel(self.text_id)

            if not text_channel:
                logger.error(f"Text channel with ID {self.text_id} not found for group '{self.name}'.")
                return
            
            # Create Buttons
            leave_button = Button(label="Leave Group", style=discord.ButtonStyle.danger)
            end_button = Button(label="End Group", style=discord.ButtonStyle.danger)
            votekick_button = Button(label="Votekick", style=discord.ButtonStyle.secondary)
            speak_toggle_button = Button(label="Speak On/Off", style=discord.ButtonStyle.secondary)
            video_toggle_button = Button(label="Video On/Off", style=discord.ButtonStyle.secondary)
            extend_button = Button(label="Extend Duration", style=discord.ButtonStyle.secondary)
            rename_button = Button(label="Rename Group", style=discord.ButtonStyle.success)


            # Assign Callbacks
            leave_button.callback = self.leave_group_callback
            end_button.callback = self.end_group_callback
            votekick_button.callback = self.votekick_callback
            speak_toggle_button.callback = self.speak_toggle_callback
            video_toggle_button.callback = self.video_toggle_callback
            extend_button.callback = self.extend_duration_callback
            rename_button.callback = self.rename_group_callback

            # Add Select Menu after this
            
            # Create View and add all components
            self.view = View()
            self.view.add_item(leave_button)
            self.view.add_item(end_button)
            self.view.add_item(votekick_button)
            self.view.add_item(speak_toggle_button)
            self.view.add_item(video_toggle_button)
            self.view.add_item(extend_button)
            self.view.add_item(rename_button)

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
            view = discord.ui.View()
            for item in message.components:
                item.disabled = True
            await message.edit(view=view)
            logger.info(f"Buttons disabled in message '{message.content}' in the channel '{message.channel.name}' for group '{self.name}'.")

        except Exception as e:
            logger.error(f"Error disabling buttons in message '{message.content}' in channel '{message.channel.name}' for group '{self.name}': {e}")


    ## Message - Send Group Info in EMBED
    async def group_info_embed(self, update : bool = False) -> None:
        try:
            text_channel: discord.TextChannel = self.guild.get_channel(self.text_id)
            voice_channel: discord.VoiceChannel = self.guild.get_channel(self.vc_id)
            role: discord.Role = self.guild.get_role(self.group_role_id)
            creator: discord.User = self.guild.get_member(self.creator_id)
            owner: discord.User = self.guild.get_member(self.owner_id)

            # Create the embed
            embed = discord.Embed(title=self.name)
            embed.description = f"This group is for studying, and people are going to study hard in this!!!"
            embed.add_field(name = "Text Channel", value = text_channel.mention)
            embed.add_field(name = "Voice Channel", value = voice_channel.mention)
            embed.add_field(name = "Creator", value = creator.mention, inline=True)
            embed.add_field(name = "Owner", value = owner.mention, inline=True)
            embed.add_field(name = "Group Role", value = role.mention)
            embed.add_field(name = "Number of Members", value = len(self.member_ids), inline=True)
            embed.add_field(name = "Max Size", value = self.max_members, inline=True)
            embed.add_field(name = "Group Duration", value = parse_seconds_to_hms(self.duration), inline=True)
            embed.add_field(name="Video", value=f"Video Mode: {self.video_mode.capitalize()}", inline=True)
            embed.add_field(name="Video Timer", value=f"{self.video_timer} seconds", inline=True)
            embed.add_field(name="Speak", value="On" if self.speak_enabled else "Off", inline=True)

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
            logger.error(f"Error sending group info embed in channel '{text_channel.name}' for group '{self.name}': {e}")


    ## Message - Send Ping Message in MESSAGE
    async def send_ping_message(self, send_channel: discord.TextChannel = None) -> None:

        if send_channel is None:
            send_channel = self.guild.get_channel(self.text_id)

        role : discord.Role = self.guild.get_role(self.group_role_id)
        members : List[discord.Member] = []

        for member_id in self.member_ids:
            member : discord.Member = self.guild.get_member(member_id)
            members.append(member)

        message = ", ".join([member.mention for member in members])
        await send_channel.send(content=f"Hello group! {role.mention}")
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
        
        role : discord.Role = self.guild.get_role(self.group_role_id)

        await interaction.response.send_message(f"❗❗Attention❗❗\n{role.mention}\nThe group will be destroyed in 60 seconds.\nPlease disconnect from the VCs and wrap up your activities.")
        asyncio.create_task(self.end_group())
        await interaction.followup.send("End Group function has started. The group will end shortly.")
        logger.info(f"User: {interaction.user.name} has called for the closure of Group'{self.name}', End Group function has started. The group will end shortly.")


    ## Callback - Rename Group
    async def rename_group_callback(self, interaction: discord.Interaction):
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
                    role : discord.Role = interaction.guild.get_role(self.study_group.group_role_id)
                    if role:
                        await role.edit(name=f"{new_name} Group")
                        logger.info(f"Role '{old_name} Group' renamed to '{new_name} Group'")
                    
                    text_channel : discord.TextChannel = interaction.guild.get_channel(self.study_group.text_id)
                    if text_channel:
                        await text_channel.edit(name=f"{new_name}-text")
                        logger.info(f"Text Channel '{old_name}-text' renamed to '{new_name}-text'")
                    
                    voice_channel : discord.VoiceChannel = interaction.guild.get_channel(self.study_group.vc_id)
                    if voice_channel:
                        await voice_channel.edit(name=f"{new_name}-voice")
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
                    await interaction.followup.send(f"Error renaming group", ephemeral=True)

        try:
            old_name = self.name
            # Create an instance of the modal
            rename_group_modal = RenameGroupModal(self, title=f"Rename Study Group: {old_name}")
            
            # Show the modal to the user
            await interaction.response.send_modal(rename_group_modal)

        except Exception as e:
            logger.error(f"Error renaming group '{self.name}': {e}")
            await interaction.followup.send(f"Error renaming group", ephemeral=True)


    ## Callback - Extend Duration
    async def extend_duration_callback(self, interaction: discord.Interaction):
        try:
            extra_time : int = 3600  # Example: Extend by 1 hour
            self.duration += extra_time
            self.end_time = (datetime.fromtimestamp(self.end_time) + timedelta(seconds=extra_time)).timestamp()
            # Update in the database (DBHandler function)
            await self.db.update_study_group_by_id({
                "group_id": self.group_id,
                "duration": self.duration,
                "end_time": self.end_time
            })
            
            await self.group_info_embed(update=True)
            await interaction.response.send_message(f"Duration extended by 1 hour. New end time: {self.end_time}", ephemeral=True)
            logger.info(f"Duration extended by 1 hour. New end time: {self.end_time}. Database updated.")
        except Exception as e:
            logger.error(f"Error extending duration: {e}")


    ## Callback (Not Implemented)- Speak on/off
    async def speak_toggle_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Speak Toggle feature will be implemented later.", ephemeral=True)


    ## Callback (Not Implemented)- Video on/off/force
    async def video_toggle_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Video Toggle feature will be implemented later.", ephemeral=True)
    

    ## Callback (Not Implemented)- Votekick
    async def votekick_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This feature will be implemented later.", ephemeral=True)
    

    ## Callback (Not Implemented)- Leave Group
    async def leave_group_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"This feature hasn't been added yet for '{self.name}'.", ephemeral=True)
        # Placeholder for actual logic to remove the user from the group
        # Example: await self.remove_member(interaction.user.id)




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

                # Wait for 5 minutes before checking the conditions again
                await asyncio.sleep(300)

        except asyncio.CancelledError:
            logger.info(f"End condition check for group '{self.name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in checking end conditions for group '{self.name}': {e}")

 
    ## End - End Group Function
    async def end_group(self, delete_text_channel: bool = True):
        """End the study group by clearing data, deleting channels, removing roles, and clearing permissions."""
        try:
            # Fetch the role, text channel, and voice channel by their IDs
            role : discord.Role = self.guild.get_role(self.group_role_id)
            text_channel : discord.TextChannel = self.guild.get_channel(self.text_id)
            voice_channel : discord.VoiceChannel = self.guild.get_channel(self.vc_id)

            # Calculate end timestamp
            end_timestamp = int((datetime.now() + timedelta(seconds=60)).timestamp())
            countdown_text = f"<t:{end_timestamp}:R>"

            await text_channel.send(content=f"Hey people of {role.mention}\nThe End Function will start in 60 seconds.")
            logger.info(f"The End condition has been triggered. from this namespae: {__name__}")
            await text_channel.send(content=countdown_text)

            await asyncio.sleep(60)

            # 1. Handle text channel deletion or permission revoking
            if text_channel:
                if delete_text_channel:
                    try:
                        await text_channel.delete(reason="Study group ended, deleting text channel.")
                        logger.info(f"Text channel '{text_channel.name}' deleted for group '{self.name}'.")
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

            # 5. Clear group data
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



    
    # class VCFunctions:
    #     def __init__(self, study_group):
    #         self.study_group = study_group
    #         self.speak_enabled = True  # Track whether speaking is enabled in the VC
    #         self.video_mode = "on"  # "on", "off", or "force"
    #         self.video_timer = 10  # Timer for forcing video to be on, default to 10 seconds

    #     def create_vc(self, guild):
    #         """Create a voice channel for the group and return its ID."""
    #         # Pseudocode to create a voice channel
    #         vc_id = 67890  # Placeholder for the created voice channel ID
    #         return vc_id

    #     def delete_vc(self, guild):
    #         """Delete the voice channel when the group ends."""
    #         # Pseudocode to delete the voice channel
    #         pass

    #     def update_vc_permissions(self, guild):
    #         """Update permissions for the group's voice channel."""
    #         # Pseudocode to update VC permissions for the group role
    #         pass

    #     def set_speak(self, enable):
    #         """Enable or disable speaking in the VC."""
    #         self.speak_enabled = enable
    #         # Update the permissions in the VC to enable/disable speaking
    #         pass

    #     def set_video(self, mode):
    #         """Set video mode in the VC ('on', 'off', or 'force')."""
    #         if mode in ["on", "off", "force"]:
    #             self.video_mode = mode
    #             # Apply video permissions in the VC based on this mode
    #         else:
    #             raise ValueError("Invalid video mode")

    #     def force_video_timer(self, user_id):
    #         """Warn user to turn on video, and kick them out if they fail to do so in time."""
    #         # Pseudocode for tracking time and kicking user if video is not turned on
    #         pass



    ## Send invite message to a member
    async def send_invite(self, interaction, invited_member: discord.Member, send_channel: discord.TextChannel) -> None:
        ### Invite a user to the group
        try:
            def check(interaction : discord.Interaction):
                check_counter = interaction.message == invite_message and interaction.user == invited_member

                if check_counter:
                    logger.info(f"Interaction clicked by invited member: {interaction.user.display_name}.")
                else:
                    logger.info(f"Not correct interaction or interaction not clicked by invited member: {interaction.user.display_name}.")

                return check_counter

            await interaction.followup.send(
                f"{invited_member.display_name} has been invited to the group {self.study_group.name}.",
                ephemeral=True
            )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.green, emoji="✅"))
            view.add_item(discord.ui.Button(label="Decline", style=discord.ButtonStyle.red, emoji="❌"))

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
            self.bot.loop.create_task(study_group.check_end_condition())
        
        # Add the study group to the dictionary
        self.active_study_groups[study_group.group_id] = study_group
        
        # Send a single message to the user with the result of the operation
        await interaction.followup.send(result, ephemeral=True)
 


async def setup(bot):
    await bot.add_cog(StudyGroupCog(bot))
    logger.info("StudyGroupCog loaded")



