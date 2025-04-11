import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Assuming your StudyGroup class is in study_groups.py
import discord
from cogs.study_groups import StudyGroup, StudyGroupCog
from cogs.voice_channels import VoiceChannelCog
from cogs.pomodoro import PomodoroCog, PomodoroSession
from utils import validate_group_parameters, parse_mentions, parse_seconds_to_hms
from main import MyBot


class TestStudyGroup(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Mock the necessary dependencies for the StudyGroup class
        self.bot = AsyncMock()
        self.db = AsyncMock()
        self.cog = MagicMock()
        self.guild = MagicMock()
        self.interaction = AsyncMock()
        self.interaction.guild = self.guild
        self.interaction.user = MagicMock()
        self.interaction.followup.send = AsyncMock()
        self.interaction.response.send_message = AsyncMock()


        # Initialize a StudyGroup instance with some dummy data
        self.study_group = StudyGroup(
            db=self.db,
            cog=self.cog,
            guild_id=12345,
            name="Test Group",
            creator_id=11111,
            category_id=67890,
            max_members=5,
            member_ids=[11111],
        )
        self.study_group.guild = self.guild
        self.study_group.group_role_id = 54321
        self.study_group.text_id = 98765

        # Initialize pomodoro cog
        self.bot_instance = MyBot()  # Create an instance of your bot class
        self.pomodoro_cog = PomodoroCog(self.bot_instance)

        # Initialize some of the Pomodoro cog instances
        self.channel = AsyncMock()
        self.member = AsyncMock()
        self.user = AsyncMock()
        self.ctx = AsyncMock()



        # Initialize Voice Channel Cog
        self.voice_channel_cog = VoiceChannelCog(self.bot_instance)


        # Mocks for members and roles
        self.member1 = MagicMock(id=11111, display_name="Creator")
        self.member2 = MagicMock(id=22222, display_name="New Member")
        self.member2.add_roles = AsyncMock()
        self.member3 = MagicMock(id=33333, display_name="Other Member")

        self.members_dict = {
            11111: self.member1,
            22222: self.member2
        }
        self.guild.get_member.side_effect = lambda id: {
            11111: self.member1,
            22222: self.member2,
            33333: self.member3,
        }.get(id)
        self.role = MagicMock(name="Test Group Role")
        self.guild.get_role.return_value = self.role

    def test_generate_group_id(self):
        group_id = self.study_group.generate_group_id()
        self.assertIsInstance(group_id, str)
        self.assertNotEqual(group_id, "")  # Check it's not an empty string

    def test_from_timestamp_to_datetime(self):
        # Test case 1: Valid timestamp conversion
        timestamp1 = 1678886400  # March 15, 2023, 00:00:00 UTC
        expected_datetime1 = datetime(2023, 3, 15, 0, 0, 0)
        self.assertEqual(self.study_group.from_timestamp_to_datetime(timestamp1), expected_datetime1)

        # Test case 2: Another valid timestamp
        timestamp2 = 1609459200  # January 1, 2021, 00:00:00 UTC
        expected_datetime2 = datetime(2021, 1, 1, 0, 0, 0)
        self.assertEqual(self.study_group.from_timestamp_to_datetime(timestamp2), expected_datetime2)

        # Test case 3: Timestamp for a different time of day
        timestamp3 = 1678922400  # March 15, 2023, 10:00:00 UTC
        expected_datetime3 = datetime(2023, 3, 15, 10, 0, 0)
        self.assertEqual(self.study_group.from_timestamp_to_datetime(timestamp3), expected_datetime3)

        # Test case 4: Future timestamp
        timestamp4 = 1700000000  # November 14, 2023, 22:13:20 UTC
        expected_datetime4 = datetime(2023, 11, 14, 22, 13, 20)
        self.assertEqual(self.study_group.from_timestamp_to_datetime(timestamp4), expected_datetime4)

    def test_is_owner(self):
        self.assertTrue(self.study_group.is_owner(11111))
        self.assertFalse(self.study_group.is_owner(22222))

    def test_is_member(self):
        self.assertTrue(self.study_group.is_member(11111))
        self.assertFalse(self.study_group.is_member(22222))

    async def test_send_welcome_message(self):
        text_channel = AsyncMock()
        self.guild.get_channel.return_value = text_channel

        await self.study_group.send_welcome_message()

        text_channel.send.assert_called_once()

    async def test_disable_buttons(self):
        message = MagicMock()
        message.components = [MagicMock(), MagicMock()]  # Mock some button components

        await self.study_group.disable_buttons(message)

        for component in message.components:
            self.assertTrue(component.disabled)
        message.edit.assert_called_once()

    async def test_group_info_embed_new_message(self):
        # Mock text and voice channels
        text_channel = AsyncMock()
        voice_channel = MagicMock()
        self.guild.get_channel.side_effect = lambda id: {
            self.study_group.text_id: text_channel,
            self.study_group.vc_id: voice_channel
        }.get(id)

        # Mock a new message being sent
        new_message = AsyncMock(id=12345)
        text_channel.send = AsyncMock(return_value=new_message)

        # Call the method
        await self.study_group.group_info_embed()

        # Assert that a new message was sent and the ID is stored
        text_channel.send.assert_called_once()
        self.assertEqual(self.study_group.info_embed_id, new_message.id)


    async def test_group_info_embed_update_existing_message(self):
        # Mock text and voice channels
        text_channel = AsyncMock()
        voice_channel = MagicMock()
        self.guild.get_channel.side_effect = lambda id: {
            self.study_group.text_id: text_channel,
            self.study_group.vc_id: voice_channel
        }.get(id)

        # Mock an existing message and its retrieval
        existing_message = AsyncMock(id=12345)
        self.study_group.info_embed_id = existing_message.id
        text_channel.fetch_message = AsyncMock(return_value=existing_message)

        # Call the method with update=True
        await self.study_group.group_info_embed(update=True)

        # Assert that the existing message was fetched and edited
        text_channel.fetch_message.assert_called_once_with(existing_message.id)
        existing_message.edit.assert_called_once()


    async def test_group_info_embed_update_message_not_found(self):
        # Mock text and voice channels
        text_channel = AsyncMock()
        voice_channel = MagicMock()
        self.guild.get_channel.side_effect = lambda id: {
            self.study_group.text_id: text_channel,
            self.study_group.vc_id: voice_channel
        }.get(id)

        # Mock message not found scenario and a new message being sent
        self.study_group.info_embed_id = 12345
        text_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(response=MagicMock(), message="Not Found"))
        new_message = AsyncMock(id=67890)
        text_channel.send = AsyncMock(return_value=new_message)

        # Call the method with update=True
        await self.study_group.group_info_embed(update=True)

        # Assert that a new message was sent because the old one was not found
        text_channel.fetch_message.assert_called_once_with(12345)
        text_channel.send.assert_called_once()
        self.assertEqual(self.study_group.info_embed_id, new_message.id)

    async def test_add_member_success(self):
        self.study_group.member_ids = [11111]
        await self.study_group.add_member(self.interaction, 22222)
        self.assertIn(22222, self.study_group.member_ids)
        self.member2.add_roles.assert_called_once_with(self.role)
        self.db.add_member_to_study_group_db.assert_called_once_with(
            self.study_group.group_id, 22222
        )
        self.interaction.followup.send.assert_called_once_with(
            "Member New Member added to the group.", ephemeral=True
        )

    async def test_add_member_already_in_group(self):
        self.study_group.member_ids = [11111, 22222]
        await self.study_group.add_member(self.interaction, 11111)
        self.assertEqual(len(self.study_group.member_ids), 2)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 11111 already in the group.", ephemeral=True
        )

    async def test_add_member_full_group(self):
        self.study_group.max_members = 1
        self.study_group.member_ids = [11111]
        await self.study_group.add_member(self.interaction, 22222)
        self.interaction.followup.send.assert_called_once_with(
            "This group is full with No. of Members: 1", ephemeral=True
        )

    async def test_add_member_not_found(self):
        self.guild.get_member.return_value = None  # Simulate member not found
        await self.study_group.add_member(self.interaction, 99999)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 99999 not found.", ephemeral=True
        )

    async def test_remove_member_success(self):
        self.study_group.member_ids = [11111, 22222]
        await self.study_group.remove_member(self.interaction, 22222)
        self.assertNotIn(22222, self.study_group.member_ids)
        self.member2.remove_roles.assert_called_once_with(self.role)
        self.db.remove_member_from_study_group_db.assert_called_once_with(
            self.study_group.group_id, 22222
        )
        self.interaction.followup.send.assert_called_once_with(
            "Member New Member successfully removed from the group.", ephemeral=True
        )

    async def test_remove_member_not_in_group(self):
        await self.study_group.remove_member(self.interaction, 22222)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 22222 is not part of the group.", ephemeral=True
        )

    async def test_remove_member_owner(self):
        await self.study_group.remove_member(self.interaction, 11111)
        self.interaction.followup.send.assert_called_once_with(
            "You cannot remove the owner from the group.", ephemeral=True
        )

    async def test_remove_member_from_empty_group(self):
        self.study_group.member_ids = []
        await self.study_group.remove_member(self.interaction, 11111)
        self.interaction.followup.send.assert_called_once_with(
            "There are no members in this group. No. of Members: 0.", ephemeral=True
        )

    async def test_remove_member_not_found(self):
        self.study_group.member_ids = [11111, 22222]
        self.guild.get_member.return_value = None
        await self.study_group.remove_member(self.interaction, 22222)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 22222 not found.", ephemeral=True
        )

    async def test_transfer_ownership_success(self):
        self.study_group.member_ids = [11111, 22222]
        self.interaction.user.id = 11111  # Current owner
        await self.study_group.transfer_ownership(self.interaction, 22222)
        self.assertEqual(self.study_group.owner_id, 22222)
        self.db.transfer_ownership_study_group_db.assert_called_once_with(
            self.study_group.group_id, 22222
        )
        self.interaction.followup.send.assert_called_once_with(
            content="Ownership transferred to from <@11111> to <@22222>."
        )

    async def test_transfer_ownership_not_owner(self):
        self.study_group.member_ids = [11111, 22222]
        self.interaction.user.id = 22222  # Not the owner
        await self.study_group.transfer_ownership(self.interaction, 11111)
        self.interaction.followup.send.assert_called_once_with(
            "You're not the owner of the group.", ephemeral=True
        )

    async def test_transfer_ownership_to_non_member(self):
        self.interaction.user.id = 11111  # Current owner
        await self.study_group.transfer_ownership(self.interaction, 33333)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 33333 is not part of the group.", ephemeral=True
        )

    async def test_transfer_ownership_to_same_owner(self):
        self.study_group.member_ids = [11111]
        self.interaction.user.id = 11111  # Current owner
        await self.study_group.transfer_ownership(self.interaction, 11111)
        self.interaction.followup.send.assert_called_once_with(
            "You're already the owner of the group.", ephemeral=True
        )

    async def test_transfer_ownership_member_not_found(self):
        self.study_group.member_ids = [11111, 22222]
        self.interaction.user.id = 11111
        self.guild.get_member.return_value = None
        await self.study_group.transfer_ownership(self.interaction, 22222)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 22222 not found.", ephemeral=True
        )

    async def test_transfer_ownership_member_not_found(self):
        self.study_group.member_ids = [11111, 22222]
        self.interaction.user.id = 11111
        self.guild.get_member.return_value = None
        await self.study_group.transfer_ownership(self.interaction, 22222)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 22222 not found.", ephemeral=True
        )

    async def test_transfer_ownership_to_non_member(self):
        self.study_group.member_ids = [11111]
        self.interaction.user.id = 11111  # Current owner
        self.guild.get_member.return_value = self.member3
        await self.study_group.transfer_ownership(self.interaction, 33333)
        self.interaction.followup.send.assert_called_once_with(
            "Member with ID 33333 is not part of the group.", ephemeral=True
        )

    async def test_transfer_ownership_same_owner(self):
        self.study_group.member_ids = [11111]
        self.interaction.user.id = 11111  # Current owner
        await self.study_group.transfer_ownership(self.interaction, 11111)
        self.interaction.followup.send.assert_called_once_with(
            "You're already the owner of the group.", ephemeral=True
        )

    async def test_leave_group_callback_success(self):
        self.study_group.member_ids = [11111, 22222]
        self.interaction.user.id = 22222
        await self.study_group.leave_group_callback(self.interaction)
        self.assertNotIn(22222, self.study_group.member_ids)
        self.member2.remove_roles.assert_called_once_with(self.role)
        self.db.remove_member_from_study_group_db.assert_called_once_with(
            self.study_group.group_id, 22222
        )
        self.interaction.response.send_message.assert_called_once()
        self.interaction.followup.send.assert_called_once_with(
            "You've left the group.", ephemeral=True
        )

    async def test_leave_group_callback_owner(self):
        self.interaction.user.id = 11111
        await self.study_group.leave_group_callback(self.interaction)
        self.interaction.response.send_message.assert_called_once()
        self.interaction.followup.send.assert_called_once_with(
            "You cannot leave the group as you are the owner.", ephemeral=True
        )

    async def test_leave_group_callback_not_member(self):
        self.study_group.member_ids = [11111]
        self.interaction.user.id = 33333
        await self.study_group.leave_group_callback(self.interaction)
        self.interaction.response.send_message.assert_called_once()
        self.interaction.followup.send.assert_called_once_with(
            "You're not a member of this group.", ephemeral=True
        )

    async def test_votekick_callback_start_vote(self):
        self.study_group.member_ids = [11111, 22222, 33333]
        self.interaction.user.id = 11111  # Initiator
        self.interaction.custom_id = "votekick_22222"  # Voting to kick member2
        self.interaction.message = AsyncMock()
        await self.study_group.votekick_callback(self.interaction)
        self.assertIn(22222, self.study_group.active_votes)
        self.interaction.response.send_message.assert_called_once()
        self.interaction.message.edit.assert_called_once()

    async def test_votekick_callback_vote_yes(self):
        self.study_group.member_ids = [11111, 22222, 33333]
        self.study_group.active_votes[22222] = VoteKick(target_id=22222, votes={11111: True})
        self.interaction.user.id = 33333  # Another member voting
        self.interaction.custom_id = "vote_yes"
        self.interaction.message = AsyncMock()

        with patch.object(self.study_group, "remove_member", new_callable=AsyncMock) as mock_remove:
            await self.study_group.votekick_callback(self.interaction)
            self.interaction.response.send_message.assert_called_once()
            self.interaction.message.edit.assert_called_once()
            if len(self.study_group.active_votes[22222].votes) >= len(self.study_group.member_ids) / 2:
                mock_remove.assert_called_once_with(self.interaction, 22222)
                self.assertNotIn(22222, self.study_group.active_votes)
            else:
                mock_remove.assert_not_called()

    async def test_votekick_callback_vote_no(self):
        self.study_group.member_ids = [11111, 22222, 33333]
        self.study_group.active_votes[22222] = VoteKick(target_id=22222, votes={11111: True})
        self.interaction.user.id = 33333  # Another member voting
        self.interaction.custom_id = "vote_no"
        self.interaction.message = AsyncMock()

        with patch.object(self.study_group, "remove_member", new_callable=AsyncMock) as mock_remove:
            await self.study_group.votekick_callback(self.interaction)
            self.interaction.response.send_message.assert_called_once()
            self.interaction.message.edit.assert_called_once()
            mock_remove.assert_not_called()

    async def test_votekick_callback_vote_ended(self):
        self.study_group.member_ids = [11111, 22222, 33333]
        self.study_group.active_votes[22222] = VoteKick(target_id=22222, votes={11111: True, 33333: False})
        self.interaction.user.id = 44444  # A member who has already voted
        self.interaction.custom_id = "vote_yes"
        self.interaction.message = AsyncMock()

        with patch.object(self.study_group, "remove_member", new_callable=AsyncMock) as mock_remove:
            await self.study_group.votekick_callback(self.interaction)
            self.interaction.response.send_message.assert_called_once_with("Voting has ended.")
            self.interaction.message.edit.assert_called_once()
            mock_remove.assert_not_called()

    async def test_button_view(self):
        text_channel = AsyncMock()
        self.guild.get_channel.return_value = text_channel

        await self.study_group.button_view()

        text_channel.send.assert_called_once()

    async def test_send_group_ping(self):
        text_channel = AsyncMock()
        self.guild.get_channel.return_value = text_channel

        await self.study_group.send_ping_message()

        text_channel.send.assert_called()

    async def test_end_group_callback(self):
        await self.study_group.end_group_callback(self.interaction)

        self.interaction.response.send_message.assert_called_once()
        self.interaction.followup.send.assert_called_once()

    async def test_rename_group_callback(self):
        await self.study_group.rename_group_callback(self.interaction)

        self.interaction.response.send_modal.assert_called_once()

    async def test_extend_duration_callback(self):
        await self.study_group.extend_duration_callback(self.interaction)

        self.db.update_study_group_by_id.assert_called_once()
        self.interaction.response.send_message.assert_called_once()

    async def test_clear_group_data(self):
        self.study_group.clear_group_data()

        self.assertIsNone(self.study_group.guild_id)

    async def test_end_group_success(self):
        self.study_group.active = True
        self.study_group.text_id = 123
        self.study_group.vc_id = 456
        text_channel = AsyncMock()
        voice_channel = AsyncMock()
        role = MagicMock()
        self.guild.get_channel.side_effect = lambda id: text_channel if id == 123 else voice_channel if id == 456 else None
        self.guild.get_role.return_value = role
        self.study_group.member_ids = [11111, 22222]
        members = [self.member1, self.member2]
        with patch.object(self.study_group, "send_group_ping", new_callable=AsyncMock) as mock_ping:
            await self.study_group.end_group()
            self.assertFalse(self.study_group.active)
            mock_ping.assert_called_once()
            for member in members:
                member.remove_roles.assert_called_with(
                    self.role, reason="Study group ended, removing group role."
                )
            self.role.delete.assert_called_once()

        # Check that group data is cleared
        self.assertIsNone(self.study_group.name)
        self.assertFalse(self.study_group.active)

    async def test_check_end_condition(self):
        # Mock active state, time, and members
        self.study_group.active = True
        self.study_group.duration = 3600  # 1 hour
        self.study_group.end_time = datetime.now() + timedelta(seconds=3600)

        # Test condition: Group is active, duration not elapsed, members present
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            check_task = asyncio.create_task(self.study_group.check_end_condition())
            await asyncio.sleep(0.1)  # Let the task run for a short time
            check_task.cancel()
            mock_sleep.assert_called()

        # Test condition: Group is inactive
        self.study_group.active = False
        with patch.object(self.study_group, "end_group", new_callable=AsyncMock) as mock_end_group:
            await self.study_group.check_end_condition()
            mock_end_group.assert_called_once()

        # Test condition: No members left
        self.study_group.active = True
        self.study_group.member_ids = []
        with patch.object(self.study_group, "end_group", new_callable=AsyncMock) as mock_end_group:
            await self.study_group.check_end_condition()
            mock_end_group.assert_called_once()

        # Test condition: Duration elapsed
        self.study_group.active = True
        self.study_group.member_ids = [11111]
        self.study_group.end_time = datetime.now() - timedelta(seconds=1)
        with patch.object(self.study_group, "end_group", new_callable=AsyncMock) as mock_end_group:
            await self.study_group.check_end_condition()
            mock_end_group.assert_called_once()

    async def test_setup_group_resources(self):
        # Mock necessary methods and objects
        self.guild.create_role = AsyncMock(return_value=self.role)
        category = MagicMock()
        self.guild.get_channel.return_value = category
        text_channel = AsyncMock(id=98765, name="Test Group-text")
        voice_channel = AsyncMock(id=56789, name="Test Group-voice")
        category.create_text_channel = AsyncMock(return_value=text_channel)
        category.create_voice_channel = AsyncMock(return_value=voice_channel)
        self.guild.get_member.return_value = self.member1
        self.db.save_study_group = AsyncMock()

        self.study_group.setup_group_resources = AsyncMock(return_value="StudyGroup 'Test Group' created successfully")

        # Patch methods within StudyGroup used in setup_group_resources
        """with patch.object(
            self.study_group, "send_welcome_message", new_callable=AsyncMock
        ) as mock_welcome, patch.object(
            self.study_group, "group_info_embed", new_callable=AsyncMock
        ) as mock_info, patch.object(
            self.study_group, "button_view", new_callable=AsyncMock
        ) as mock_buttons, patch.object(
            self.study_group, "send_ping_message", new_callable=AsyncMock
        ) as mock_ping:
            # Call the method to test
            result = await self.study_group.setup_group_resources(self.interaction)

            # Assertions to check correct behavior
            self.guild.create_role.assert_called_once_with(
                name="Test Group Group", reason="Role for study group"
            )
            category.create_text_channel.assert_called_once_with(
                name="Test Group-text", reason="Text channel for study group"
            )
            category.create_voice_channel.assert_called_once_with(
                name="Test Group-voice", reason="Voice channel for study group"
            )
            self.member1.add_roles.assert_called_once_with(self.role)
            mock_welcome.assert_called_once()
            mock_info.assert_called_once()
            mock_buttons.assert_called_once()
            mock_ping.assert_called_once()
            self.db.save_study_group.assert_called_once()
            self.assertTrue(self.study_group.active)
            self.assertIn("StudyGroup 'Test Group' created successfully", result)

            # Check channel permissions were set correctly
            text_channel.set_permissions.assert_called_once_with(
                self.role, read_messages=True, send_messages=True
        )

            voice_channel.set_permissions.assert_called_once_with(
                self.role, connect=True, speak=True
            )
            voice_channel.set_permissions.assert_called_once_with(self.role, connect=True, speak=True)"""

    def test_pomodoro_cog_init(self):
        self.assertIsInstance(self.pomodoro_cog, PomodoroCog)
        self.assertEqual(self.pomodoro_cog.active_sessions, {})


    async def test_start_pomodoro(self):
        # Mock objects
        ctx = AsyncMock()
        member = MagicMock(id=123)
        user = MagicMock()
        voice_channel = AsyncMock()
        self.db.create_pomodoro_session = AsyncMock(return_value=1)

        # Patch methods
        with patch.object(self.pomodoro_cog, 'create_voice_channel', return_value=voice_channel) as mock_create_vc, \
             patch.object(PomodoroSession, 'run_timer', new_callable=AsyncMock) as mock_run_timer:
            # Call the method
            await self.pomodoro_cog.start_pomodoro(ctx, member, user, 25, 5, 15, 4)

            # Assertions
            mock_create_vc.assert_called_once_with(ctx, member)
            mock_run_timer.assert_called_once()
            self.db.create_pomodoro_session.assert_called_once()
            ctx.send.assert_called_once()
            session_data = self.pomodoro_cog.active_sessions[member.id]
            self.assertIsNotNone(session_data)
            self.assertEqual(session_data['current_stage'], 'focus')
            self.assertEqual(session_data['cycles_completed'], 0)
            self.assertEqual(session_data['focus_duration'], 25)
            self.assertEqual(session_data['member'], member)



    async def test_end_pomodoro(self):
        self.pomodoro_cog.active_sessions[self.member.id] = {
            "timer_task": AsyncMock(),
            "voice_channel": self.channel,
        }

        await self.pomodoro_cog.end_pomodoro(self.ctx, self.member)

        self.pomodoro_cog.active_sessions[self.member.id]["timer_task"].cancel.assert_called_once()
        self.channel.delete.assert_called_once()
        self.ctx.send.assert_called_once()
        self.assertNotIn(self.member.id, self.pomodoro_cog.active_sessions)
        self.db.update_pomodoro_session.assert_called_once()


    async def test_pause_resume_pomodoro(self):
        self.pomodoro_cog.active_sessions[self.member.id] = {"is_paused": False}

        await self.pomodoro_cog.pause_pomodoro(self.ctx, self.member)
        self.assertTrue(self.pomodoro_cog.active_sessions[self.member.id]["is_paused"])
        self.ctx.send.assert_called_once_with(
            f"{self.member.mention}, your Pomodoro session is now paused."
        )

        self.ctx.reset_mock()

        await self.pomodoro_cog.resume_pomodoro(self.ctx, self.member)
        self.assertFalse(self.pomodoro_cog.active_sessions[self.member.id]["is_paused"])
        self.ctx.send.assert_called_once_with(
            f"{self.member.mention}, your Pomodoro session has resumed!"
        )


    async def test_pomodoro_status(self):
        self.pomodoro_cog.active_sessions[self.member.id] = {
            "is_paused": False,
            "current_stage": "focus",
            "stage_end_time": datetime.now() + timedelta(minutes=10),
            "focus_duration": 25,
            "short_break_duration": 5,
            "long_break_duration": 15,
        }
        with patch(  # Mock the time parsing function to return a predefined value for testing
            "cogs.pomodoro.parse_seconds_to_hms", return_value="10m 0s"
        ) as mock_parse:

            await self.pomodoro_cog.pomodoro_status(self.ctx, self.member)


            mock_parse.assert_called_once()

            self.ctx.send.assert_called_once()

    async def test_run_timer_focus_stage(self):
        session_data = {
            "current_stage": "focus",
            "cycles_completed": 0,
            "voice_channel": self.channel,
            "member": self.member1,
            "focus_duration": 0.01,  # use a small value to make the test quicker
            "short_break_duration": 0.01,
            "long_break_duration": 0.01,
            "num_cycles": 1,

            "is_paused": False,
        }

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
                patch.object(self.pomodoro_cog, "send_stage_notification", new_callable=AsyncMock) as mock_notification:
            # Run the timer for a short duration
            session = PomodoroSession(**session_data)
            timer_task = asyncio.create_task(session.run_timer(self.ctx, session_data))


            await asyncio.sleep(0.1)  # Let the timer run for a bit
            timer_task.cancel()

            try:
                await timer_task
            except asyncio.CancelledError:
                pass

            # Assertions to ensure that the timer progressed and notifications were sent

            self.assertTrue(mock_sleep.await_count > 0)
            self.assertTrue(mock_notification.await_count > 0)

    def test_validate_group_parameters_valid(self):
        # Mock data for a valid scenario
        name = "Valid Group Name"
        mentions = [12345, 67890]  # Example member IDs
        max_members = 10
        category = MagicMock()  # Mock a Discord category
        study_groups = {}  # Simulate no existing groups with the same name
        interaction = AsyncMock()
        interaction.guild.categories = [category]
        interaction.guild.get_member.return_value = MagicMock()
        # Call the function with the mocked data
        result = asyncio.run(validate_group_parameters(
            interaction=MagicMock(),  # Mock interaction as it's not directly used in validation
            name=name,
            mentions=mentions,
            max_members=max_members,
            category=category,
            study_groups=study_groups
        ))

        # Assert that the validation passes (returns True)
        self.assertTrue(result)


    def test_validate_group_parameters_duplicate_name(self):
        # Mock data with a duplicate group name
        name = "Duplicate Name"
        mentions = [12345]
        max_members = 5
        category = MagicMock()
        study_groups = {"existing_id": MagicMock(name="Duplicate Name")}  # Simulate an existing group

        # Call the function and expect it to fail validation
        result = asyncio.run(validate_group_parameters(
            interaction=MagicMock(),
            name=name,
            mentions=mentions,
            max_members=max_members,
            category=category,
            study_groups=study_groups
        ))

        # Assert that validation fails (returns False) due to duplicate name
        self.assertFalse(result)


class TestTaskListCog(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.bot = AsyncMock()
        self.db = AsyncMock()
        self.cog = MagicMock()
        self.guild = MagicMock()
        self.interaction = AsyncMock()
        self.interaction.guild = self.guild
        self.interaction.user = MagicMock()
        self.interaction.followup.send = AsyncMock()
        self.interaction.response.send_message = AsyncMock()

        self.tasklist_cog = StudyGroupCog(self.bot)
        self.tasklist_cog.db = self.db
        self.tasklist_cog.bot = self.bot

        self.member1 = MagicMock(id=12345, mention="<@12345>")
        self.member2 = MagicMock(id=67890, mention="<@67890>")

        self.members_dict = {
            12345: self.member1,
            67890: self.member2,
        }

        self.guild.get_member.side_effect = lambda id: self.members_dict.get(id)

        self.channel = AsyncMock()
        self.interaction.channel = self.channel

    async def test_add_task_with_due_date(self):
        # Mock data for the command
        task_name = "Finish report"

        due_date_str = "2024-01-15 14:00"
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")


        self.interaction.user.id = 12345
        self.interaction.user.mention = "<@12345>"
        self.db.add_task.return_value = None

        # Call the command
        await self.tasklist_cog.add_task(self.interaction, task_name, due_date_str)

        # Assertions
        self.db.add_task.assert_called_once_with(
            task_name=task_name,
            user_id=self.interaction.user.id,
            due_date=due_date,
            reminders_sent=False
        )

        expected_message = f"Task '{task_name}' added successfully with due date: {due_date_str}."
        self.interaction.followup.send.assert_called_once_with(expected_message, ephemeral=True)

    async def test_send_reminder(self):
        # Mock a task
        task = {
            "task_id": 1,
            "task_name": "Submit project",
            "user_id": 12345,
            "due_date": datetime.now() + timedelta(hours=1),
            "reminders_sent": False,
        }
        # Mock the user and their DM channel
        user = AsyncMock()
        dm_channel = AsyncMock()
        user.create_dm = AsyncMock(return_value=dm_channel)
        self.bot.get_user = AsyncMock(return_value=user)
        # Call the function to send a reminder
        await self.tasklist_cog.send_reminder(task)
        # Assertions
        self.bot.get_user.assert_called_once_with(task["user_id"])
        user.create_dm.assert_called_once()
        dm_channel.send.assert_called_once()
        self.db.update_task_reminder_status.assert_called_once_with(task["task_id"])

    async def test_list_tasks(self):
        # Mock tasks data from the database
        tasks = [
            {"task_id": 1, "task_name": "Task 1", "user_id": 12345, "due_date": datetime.now() + timedelta(days=1), "reminders_sent": False},
            {"task_id": 2, "task_name": "Task 2", "user_id": 12345, "due_date": datetime.now() + timedelta(hours=5), "reminders_sent": False}
        ]
        self.db.get_tasks_by_user.return_value = tasks

        # Mock user and interaction
        self.interaction.user.id = 12345
        self.interaction.user.mention = "<@12345>"

        # Call the command
        await self.tasklist_cog.list_tasks(self.interaction)

        # Assertions
        self.db.get_tasks_by_user.assert_called_once_with(12345)
        self.interaction.response.send_message.assert_called_once()

        # Check if the embed was created with task information
        call_args = self.interaction.response.send_message.call_args
        embed = call_args[1]["embed"]
        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(len(embed.fields), len(tasks))

    async def test_delete_task(self):
        # Mock task ID and user
        task_id = 1
        self.interaction.user.id = 12345
        self.interaction.user.mention = "<@12345>"
        # Mock the database response
        self.db.delete_task.return_value = 1
        # Call the command
        await self.tasklist_cog.delete_task(self.interaction, task_id)
        # Assertions
        self.db.delete_task.assert_called_once_with(task_id, 12345)
        self.interaction.response.send_message.assert_called_once_with(
            f"Task with ID {task_id} deleted successfully.", ephemeral=True
        )
        # Test case for task not found
        self.db.delete_task.return_value = 0
        await self.tasklist_cog.delete_task(self.interaction, 2)
        self.interaction.response.send_message.assert_called_with(
            "Task not found or you do not have permission to delete it.", ephemeral=True
        )

    async def test_complete_task(self):
        # Mock task ID and user
        task_id = 1
        self.interaction.user.id = 12345
        self.interaction.user.mention = "<@12345>"
        # Mock the database response
        self.db.complete_task.return_value = 1
        # Call the command
        await self.tasklist_cog.complete_task(self.interaction, task_id)
        # Assertions
        self.db.complete_task.assert_called_once_with(task_id, 12345)
        self.interaction.response.send_message.assert_called_once_with(
            f"Task with ID {task_id} marked as complete.", ephemeral=True
        )
        # Test case for task not found
        self.db.complete_task.return_value = 0
        await self.tasklist_cog.complete_task(self.interaction, 2)
        self.interaction.response.send_message.assert_called_with(
            "Task not found or you do not have permission to complete it.", ephemeral=True
        )'''







if __name__ == "__main__":
    unittest.main()
