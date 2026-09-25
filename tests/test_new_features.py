import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cogs.checkin import CheckinSession
from cogs.pomodoro import Pomodoro, calculate_pomodoro_ratio
from cogs.study_groups import StudyGroup, StudyGroupCog
from cogs.tasklist import TaskList


class TestPomodoroRatioAndFeatures(unittest.TestCase):
    def test_ratio_calculations(self):
        # Default (none provided) -> (25, 5, 15)
        self.assertEqual(calculate_pomodoro_ratio(None, None, None), (25, 5, 15))

        # Focus only provided
        self.assertEqual(calculate_pomodoro_ratio(50, None, None), (50, 10, 30))
        self.assertEqual(calculate_pomodoro_ratio(25, None, None), (25, 5, 15))

        # Short break only provided
        self.assertEqual(calculate_pomodoro_ratio(None, 10, None), (50, 10, 30))
        self.assertEqual(calculate_pomodoro_ratio(None, 5, None), (25, 5, 15))

        # Long break only provided
        self.assertEqual(calculate_pomodoro_ratio(None, None, 30), (50, 10, 30))
        self.assertEqual(calculate_pomodoro_ratio(None, None, 15), (25, 5, 15))

        # All provided
        self.assertEqual(calculate_pomodoro_ratio(45, 10, 20), (45, 10, 20))

    def test_start_pomodoro_require_vc_false(self):
        async def run_test():
            bot = MagicMock()
            bot.db = AsyncMock()
            bot.get_cog.return_value = None
            cog = Pomodoro(bot)

            interaction = AsyncMock()
            interaction.guild = MagicMock()
            interaction.guild_id = 999
            interaction.user.id = 12345
            interaction.channel_id = 555
            interaction.response.is_done = MagicMock(return_value=False)

            # Mock group
            mock_group = {
                'id': 1,
                'group_id': 'grp-uuid-1',
                'name': 'Test Group',
                'vc_id': 888,
                'text_id': 555,
                'creator_id': 12345,
                'owner_id': 12345
            }
            bot.db.get_user_group.return_value = mock_group

            # User is NOT in a voice channel
            interaction.user.voice = None

            # With require_vc=False, it should succeed without voice channel check
            await cog.start_pomodoro.callback(cog, interaction, focus=25, require_vc=False)

            self.assertIn(1, cog.sessions)
            session = cog.sessions[1]
            self.assertFalse(session.require_vc)
            self.assertEqual(session.focus, 25)
            self.assertEqual(session.short_break, 5)
            self.assertEqual(session.long_break, 15)
            send_mock = interaction.followup.send if interaction.followup.send.called else interaction.response.send_message
            send_mock.assert_called_once()
            call_arg = send_mock.call_args[0][0]
            self.assertIn("Pomodoro session started", call_arg)
            self.assertIn("Text-Only", call_arg)

        asyncio.run(run_test())

    def test_edit_pomodoro_command(self):
        async def run_test():
            bot = MagicMock()
            bot.db = AsyncMock()
            cog = Pomodoro(bot)

            interaction = AsyncMock()
            interaction.guild_id = 999
            interaction.user.id = 12345
            interaction.channel_id = 555
            interaction.response.is_done = MagicMock(return_value=False)

            mock_group = {
                'id': 1,
                'group_id': 'grp-uuid-1',
                'name': 'Test Group',
                'vc_id': 888,
                'text_id': 555,
                'creator_id': 12345,
                'owner_id': 12345
            }
            bot.db.get_user_group.return_value = mock_group

            # Start session
            await cog.start_pomodoro.callback(cog, interaction, focus=25, require_vc=False)
            interaction.response.send_message.reset_mock()
            interaction.followup.send.reset_mock()

            # Edit session with focus=50 (should auto-calc 50:10:30) and require_vc=True
            await cog.edit_pomodoro.callback(cog, interaction, focus=50, require_vc=True)

            session = cog.sessions[1]
            self.assertEqual(session.focus, 50)
            self.assertEqual(session.short_break, 10)
            self.assertEqual(session.long_break, 30)
            self.assertTrue(session.require_vc)
            edit_send_mock = interaction.followup.send if interaction.followup.send.called else interaction.response.send_message
            edit_send_mock.assert_called_once()

        asyncio.run(run_test())

    def test_strict_notification_routing(self):
        async def run_test():
            bot = MagicMock()
            bot.db = AsyncMock()
            cog = Pomodoro(bot)

            guild = MagicMock()
            guild.text_channels = [MagicMock()]
            bot.get_guild.return_value = guild

            text_ch = AsyncMock()
            vc_ch = AsyncMock()
            def get_channel_mock(cid):
                if cid == 555:
                    return text_ch
                if cid == 888:
                    return vc_ch
                return None
            guild.get_channel.side_effect = get_channel_mock
            bot.db.get_group_roles.return_value = (None, None)

            # Session with require_vc=False
            session = cog.sessions[1] = MagicMock()
            session.text_id = 555
            session.vc_id = 888
            session.require_vc = False

            await cog.send_notification(999, 1, "Test Message")

            # Must send to text channel 555, NOT fallback to guild.text_channels[0]
            text_ch.send.assert_called_once_with("Test Message")
            guild.text_channels[0].send.assert_not_called()

        asyncio.run(run_test())


class TestCheckinPrompts(unittest.TestCase):
    def test_100_adhd_prompts(self):
        prompts = CheckinSession.prompt_messages
        self.assertEqual(len(prompts), 100, f"Expected 100 prompts, got {len(prompts)}")
        self.assertEqual(len(set(prompts)), 100, "All 100 prompts must be unique")
        # Verify examples
        self.assertTrue(any("How's it going?" in p for p in prompts))
        self.assertTrue(any("What's the progress?" in p for p in prompts))
        self.assertTrue(any("Hey, you there?" in p for p in prompts))


class TestEndGroupFallbackCleanup(unittest.TestCase):
    def test_end_group_fallback_deletes_channels_and_roles(self):
        async def run_test():
            bot = MagicMock()
            bot.db = AsyncMock()
            bot.get_cog.return_value = None
            cog = StudyGroupCog(bot)

            interaction = AsyncMock()
            guild = MagicMock()
            interaction.guild = guild
            interaction.guild.id = 999
            interaction.user.id = 12345
            interaction.channel_id = 777

            # Group is only in DB, not in memory
            cog.active_study_groups = {}

            mock_text_ch = AsyncMock()
            mock_vc_ch = AsyncMock()
            mock_role = AsyncMock()

            def get_channel_mock(cid):
                if cid == 777:
                    return mock_text_ch
                if cid == 888:
                    return mock_vc_ch
                return None

            guild.get_channel.side_effect = get_channel_mock
            guild.get_role.return_value = mock_role

            bot.db.get_study_group_by_channel.return_value = {
                'id': 42,
                'group_id': 'grp-42-uuid',
                'name': 'Orphan Group',
                'text_id': 777,
                'vc_id': 888,
                'group_role_id': 999,
                'creator_id': 12345,
                'owner_id': 12345
            }

            await cog.end_group.callback(cog, interaction)

            # Verify text channel, voice channel, and role deleted
            mock_text_ch.delete.assert_called_once()
            mock_vc_ch.delete.assert_called_once()
            mock_role.delete.assert_called_once()
            bot.db.delete_study_group.assert_called_once_with('grp-42-uuid')

        asyncio.run(run_test())


class TestTaskListGroupScoping(unittest.TestCase):
    def test_task_list_embed_limit_safety(self):
        async def run_test():
            bot = MagicMock()
            bot.db = AsyncMock()
            cog = TaskList(bot)

            interaction = AsyncMock()
            interaction.user.id = 12345
            interaction.user.display_name = "ADHDUser"
            interaction.channel_id = None

            # Simulate 50 tasks (> 25 Discord field limit)
            mock_tasks = [
                {'id': i, 'task_number': i, 'description': f"Task item {i}", 'completed': 0}
                for i in range(1, 51)
            ]
            bot.db.get_user_tasks.return_value = mock_tasks

            await cog.list_tasks.callback(cog, interaction)

            interaction.response.send_message.assert_called_once()
            embed = interaction.response.send_message.call_args[1].get('embed') or interaction.response.send_message.call_args[0][0]
            # Embed fields count should be 0 because we format into description to prevent the 400 Bad Request
            self.assertEqual(len(embed.fields), 0)
            self.assertIn("Task #1", embed.description)
            self.assertIn("more tasks", embed.description)

        asyncio.run(run_test())


class TestStudyGroupEmbedIntegration(unittest.TestCase):
    def test_group_info_embed_with_pomodoro_and_checkin(self):
        async def run_test():
            bot = MagicMock()
            db = AsyncMock()
            cog = MagicMock()
            cog.bot = bot

            group = StudyGroup(
                db=db,
                cog=cog,
                guild_id=999,
                name="Deep Work Club",
                creator_id=123,
                category_id=456,
                max_members=10,
                member_ids=[123, 456, 789]
            )
            group.text_id = 777
            group.vc_id = 888
            group.group_role_id = 999

            guild = MagicMock()
            group.guild = guild

            mock_text_ch = AsyncMock(spec=discord.TextChannel)
            mock_vc_ch = AsyncMock(spec=discord.VoiceChannel)
            mock_role = MagicMock(spec=discord.Role)
            mock_member = MagicMock(spec=discord.Member)

            def get_channel_mock(cid):
                if cid == 777:
                    return mock_text_ch
                if cid == 888:
                    return mock_vc_ch
                return None

            guild.get_channel.side_effect = get_channel_mock
            guild.get_role.return_value = mock_role
            guild.get_member.return_value = mock_member

            # Mock Pomodoro Cog with active session
            mock_pomo_cog = MagicMock()
            mock_pomo_session = MagicMock()
            mock_pomo_session.current_stage = "focus"
            mock_pomo_session.is_paused = False
            mock_pomo_session.timer = 1200
            mock_pomo_session.cycles = 3
            mock_pomo_session.require_vc = False
            mock_pomo_cog.sessions = {group.group_id: mock_pomo_session}

            # Mock Checkin Cog with active session
            mock_checkin_cog = MagicMock()
            mock_checkin_session = MagicMock()
            mock_checkin_session.text_id = 777
            mock_checkin_session.name = "Daily Sprint Standup"
            mock_checkin_session.next_reminder_time = 1788570000
            mock_checkin_session.member_statuses = {
                123: {'status': 'present'},
                456: {'status': 'break'},
                789: {'status': 'absent'}
            }
            mock_checkin_cog.active_sessions = {"checkin-1": mock_checkin_session}

            def get_cog_mock(name):
                if name == "Pomodoro":
                    return mock_pomo_cog
                if name == "CheckinCog":
                    return mock_checkin_cog
                return None

            bot.get_cog.side_effect = get_cog_mock

            # Send group info embed
            await group.group_info_embed(update=False)

            mock_text_ch.send.assert_called_once()
            embed = mock_text_ch.send.call_args[1].get('embed') or mock_text_ch.send.call_args[0][0]
            field_names = [f.name for f in embed.fields]

            self.assertIn("⏱️ Pomodoro Session", field_names)
            self.assertIn("📋 Check-in Status", field_names)

            pomo_field = next(f for f in embed.fields if f.name == "⏱️ Pomodoro Session")
            self.assertIn("Running", pomo_field.value)
            self.assertIn("Focus", pomo_field.value)
            self.assertIn("Cycles**: 3", pomo_field.value)
            self.assertIn("Text-Only", pomo_field.value)

            checkin_field = next(f for f in embed.fields if f.name == "📋 Check-in Status")
            self.assertIn("Daily Sprint Standup", checkin_field.value)
            self.assertIn("Present** (1)", checkin_field.value)
            self.assertIn("On Break** (1)", checkin_field.value)
            self.assertIn("Absent** (1)", checkin_field.value)

            # Test integrated callbacks
            interaction = AsyncMock()
            interaction.user.id = 123
            interaction.user.mention = "<@123>"

            # 1. Refresh GUI callback
            await group.refresh_gui_callback(interaction)
            interaction.response.send_message.assert_called_with("🔄 Study group dashboard refreshed!", ephemeral=True)

            # 2. Checkin Present callback
            interaction.response.send_message.reset_mock()
            await group.checkin_present_callback(interaction)
            interaction.response.send_message.assert_called_once()
            self.assertIn("Present", interaction.response.send_message.call_args[0][0])
            self.assertEqual(mock_checkin_session.member_statuses[123]['status'], 'present')

            # 3. Checkin Break callback
            interaction.response.send_message.reset_mock()
            await group.checkin_break_callback(interaction)
            interaction.response.send_message.assert_called_once()
            self.assertIn("Break", interaction.response.send_message.call_args[0][0])
            self.assertEqual(mock_checkin_session.member_statuses[123]['status'], 'break')

            # 4. Pomodoro Toggle callback
            interaction.response.send_message.reset_mock()
            await group.pomo_toggle_callback(interaction)
            interaction.response.send_message.assert_called_once()
            self.assertTrue(mock_pomo_session.is_paused)

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()

