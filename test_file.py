"""
Comprehensive End-to-End Test Suite for CPO Discord Bot
Simulates dummy requests under:
  - Server ID (Guild ID): 885134444992806962 ("Accountability")
  - User ID: 534168986149978112 ("Vector", Bot Developer)

Rate-limit safety:
  - Uses mock interaction wrappers for Discord HTTP mutations.
  - Adds pacing delays to prevent API flooding or rate limit exhaustion.

Comprehensive Coverage:
  - Tests 100% of all 28 registered slash commands across all 7 cogs.
  - Tests multiple attribute combinations (default vs custom, boundaries, edge cases).
  - Tests all interactive button/modal callbacks (StudyGroups and Checkin).
  - Tests 5-tier permission boundaries (Bot Developer, Guild Manager, Group Owner, Regular User).
"""

import asyncio
import logging
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import discord
from discord import app_commands

from bot import CPO
from cogs.manager import PermissionLevel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DummyRequestRunner")

GUILD_ID = 885134444992806962
USER_ID = 534168986149978112
SECOND_USER_ID = 999111222333
REGULAR_USER_ID = 888777666555


class DummyInteractionFactory:
    """Creates fully populated mock Discord interactions for server 885134444992806962 and user 534168986149978112."""

    @staticmethod
    def create(
        bot: CPO,
        user_id: int = USER_ID,
        user_name: str = "Vector",
        channel_id: int = 885134444992806999,
        channel_name: str = "productivity-checkins",
        is_admin: bool = True,
    ):
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.client = bot
        interaction.guild_id = GUILD_ID

        # Mock Member / User
        user = MagicMock(spec=discord.Member)
        user.id = user_id
        user.name = user_name
        user.display_name = user_name
        user.mention = f"<@{user_id}>"
        user.bot = False
        user.roles = []
        user.voice = None
        user.guild_permissions = discord.Permissions.all() if is_admin else discord.Permissions(send_messages=True, read_messages=True)
        interaction.user = user

        # Mock Channel
        channel = AsyncMock(spec=discord.TextChannel)
        channel.id = channel_id
        channel.name = channel_name
        channel.guild_id = GUILD_ID
        channel.mention = f"<#{channel_id}>"
        mock_msg = MagicMock(spec=discord.Message)
        mock_msg.id = 885134444992807555
        mock_msg.components = []
        channel.send = AsyncMock(return_value=mock_msg)
        channel.fetch_message = AsyncMock(return_value=mock_msg)
        interaction.channel = channel
        interaction.channel_id = channel_id

        # Mock Voice Channel
        vc = AsyncMock(spec=discord.VoiceChannel)
        vc.id = 885134444992807000
        vc.name = "Focus Study VC"
        vc.mention = f"<#{vc.id}>"
        vc.members = []

        # Mock Role
        role = MagicMock(spec=discord.Role)
        role.id = 885134444992808000
        role.name = "Study Cohort Role"
        role.mention = f"<@&{role.id}>"

        # Mock Category
        category = AsyncMock(spec=discord.CategoryChannel)
        category.id = 885134444992806900
        category.name = "STUDY MODULES"
        category.create_text_channel = AsyncMock(return_value=channel)
        category.create_voice_channel = AsyncMock(return_value=vc)

        # Mock Guild
        guild = AsyncMock(spec=discord.Guild)
        guild.id = GUILD_ID
        guild.name = "Accountability"
        guild.owner_id = USER_ID
        guild.owner = user
        guild.default_role = MagicMock(spec=discord.Role)
        guild.me = MagicMock(spec=discord.Member)
        guild.me.guild_permissions = discord.Permissions.all()
        guild.text_channels = [channel]
        guild.voice_channels = [vc]
        guild.categories = [category]
        guild.members = [user]

        def mock_get_member(uid: int):
            if uid == user_id:
                return user
            mock_m = MagicMock(spec=discord.Member)
            mock_m.id = uid
            mock_m.name = f"User_{uid}"
            mock_m.display_name = f"User_{uid}"
            mock_m.mention = f"<@{uid}>"
            mock_m.bot = False
            mock_m.roles = []
            mock_m.voice = None
            mock_m.guild_permissions = discord.Permissions.all() if uid == USER_ID else discord.Permissions(send_messages=True)
            mock_m.remove_roles = AsyncMock()
            mock_m.add_roles = AsyncMock()
            mock_m.move_to = AsyncMock()
            return mock_m

        guild.get_member.side_effect = mock_get_member
        guild.fetch_member = AsyncMock(side_effect=mock_get_member)
        guild.get_channel.side_effect = lambda cid: channel if cid == channel_id else (category if cid == category.id else vc)
        guild.get_role.side_effect = lambda rid: role if rid == role.id else None
        guild.create_role.return_value = role
        guild.create_text_channel.return_value = channel
        guild.create_voice_channel.return_value = vc

        interaction.guild = guild

        # Mock Responses & Followups
        response = AsyncMock()
        response.is_done = MagicMock(return_value=False)

        async def mock_defer(*args, **kwargs):
            response.is_done.return_value = True

        async def mock_send_message(*args, **kwargs):
            response.is_done.return_value = True

        response.defer = AsyncMock(side_effect=mock_defer)
        response.send_message = AsyncMock(side_effect=mock_send_message)
        interaction.response = response

        followup = AsyncMock()
        followup.send = AsyncMock()
        interaction.followup = followup

        return interaction, category, vc, role


def get_response_text(interaction: discord.Interaction) -> str:
    """Extracts all text content sent via response.send_message or followup.send."""
    texts: List[str] = []
    send_msg: Any = interaction.response.send_message
    if getattr(send_msg, "called", False):
        for call in getattr(send_msg, "call_args_list", []):
            args, kwargs = call
            if args:
                texts.append(str(args[0]))
            if "content" in kwargs and kwargs["content"]:
                texts.append(str(kwargs["content"]))
    followup_send: Any = interaction.followup.send
    if getattr(followup_send, "called", False):
        for call in getattr(followup_send, "call_args_list", []):
            args, kwargs = call
            if args:
                texts.append(str(args[0]))
            if "content" in kwargs and kwargs["content"]:
                texts.append(str(kwargs["content"]))
    return " ".join(texts)


def get_response_embed(interaction: discord.Interaction) -> Optional[discord.Embed]:
    """Extracts latest embed sent via response.send_message or followup.send."""
    for mock_call in [interaction.followup.send, interaction.response.send_message]:
        m: Any = mock_call
        if getattr(m, "called", False):
            for call in reversed(getattr(m, "call_args_list", [])):
                _, kwargs = call
                if "embed" in kwargs and kwargs["embed"]:
                    return kwargs["embed"]
    return None


async def run_all_feature_tests():
    """Runs end-to-end tests with dummy requests for all commands and interactive features."""
    logger.info("=" * 80)
    logger.info("STARTING COMPLETE BOT SLASH COMMAND & FEATURE TEST MATRIX")
    logger.info(f"Target Server ID: {GUILD_ID} ('Accountability')")
    logger.info(f"Target User ID:   {USER_ID} ('Vector', Bot Developer)")
    logger.info("=" * 80)

    bot = CPO()
    bot.bot_developer_id = USER_ID
    await bot.db.connect()

    # Load all cogs
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            await bot.load_extension(cog_name)

    passed_tests = 0
    total_tests = 0

    async def execute_test(test_name: str, test_coro):
        nonlocal passed_tests, total_tests
        total_tests += 1
        logger.info(f"[TEST {total_tests:02d}] Running: {test_name}...")
        try:
            await test_coro
            # Rate limit prevention sleep
            await asyncio.sleep(0.04)
            logger.info(f"  --> PASSED: {test_name}\n")
            passed_tests += 1
        except Exception as e:
            logger.exception(f"  --> FAILED: {test_name} with error: {e}\n")
            raise

    # =========================================================================
    # 1. TASK LIST COG (Commands: task_add, task_list, task_complete)
    # =========================================================================
    tasklist_cog = bot.get_cog("TaskList")
    assert tasklist_cog is not None, "TaskList cog must be loaded"

    task_id_1: Optional[int] = None
    task_id_2: Optional[int] = None

    async def test_task_add_standard():
        nonlocal task_id_1
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await tasklist_cog.add_task.callback(tasklist_cog, interaction, description="Deep Research on AI Reliability")
        text = get_response_text(interaction)
        assert "Task added successfully" in text
        task_id_1 = int(text.split("Task ID: ")[1].strip())
        assert task_id_1 > 0

    await execute_test("TaskList - /task_add (Standard description)", test_task_add_standard())

    async def test_task_add_special_chars():
        nonlocal task_id_2
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await tasklist_cog.add_task.callback(
            tasklist_cog, interaction, description="[P0] Deploy CPO v2.4 to Discord: test all 28 commands & permissions! 🚀"
        )
        text = get_response_text(interaction)
        assert "Task added successfully" in text
        task_id_2 = int(text.split("Task ID: ")[1].strip())
        assert task_id_2 > 0

    await execute_test("TaskList - /task_add (Special characters & emojis)", test_task_add_special_chars())

    async def test_task_list_with_tasks():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await tasklist_cog.list_tasks.callback(tasklist_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Tasks" in embed.title
        assert len(embed.fields) >= 2

    await execute_test("TaskList - /task_list (With active tasks)", test_task_list_with_tasks())

    async def test_task_complete_valid():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await tasklist_cog.complete_task.callback(tasklist_cog, interaction, task_id=task_id_1)
        text = get_response_text(interaction)
        assert f"Task {task_id_1} marked as complete" in text

    await execute_test("TaskList - /task_complete (Valid task ID)", test_task_complete_valid())

    async def test_task_complete_invalid():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await tasklist_cog.complete_task.callback(tasklist_cog, interaction, task_id=999999)
        text = get_response_text(interaction)
        assert "not found or already completed" in text

    await execute_test("TaskList - /task_complete (Non-existent task ID)", test_task_complete_invalid())

    async def test_task_list_empty():
        # Clean user with no tasks
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=777000111222, user_name="CleanUser")
        await tasklist_cog.list_tasks.callback(tasklist_cog, interaction)
        text = get_response_text(interaction)
        assert "You have no tasks" in text

    await execute_test("TaskList - /task_list (Zero tasks empty state)", test_task_list_empty())

    # =========================================================================
    # 2. PRODUCTIVITY TRACKER COG (Command: productivity)
    # =========================================================================
    prod_cog = bot.get_cog("ProductivityTracker")
    assert prod_cog is not None, "ProductivityTracker cog must be loaded"

    async def test_productivity_active_user():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await prod_cog.productivity.callback(prod_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Productivity Metrics" in embed.title
        field_names = [f.name for f in embed.fields]
        assert "Tasks Completed" in field_names
        assert "Efficiency Score (tasks/hour)" in field_names

    await execute_test("ProductivityTracker - /productivity (Active user with completed tasks)", test_productivity_active_user())

    async def test_productivity_zero_tasks_user():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=777000111222, user_name="CleanUser")
        await prod_cog.productivity.callback(prod_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Productivity Metrics" in embed.title

    await execute_test("ProductivityTracker - /productivity (Fresh user zero tasks)", test_productivity_zero_tasks_user())

    # =========================================================================
    # 3. MANAGER COG (Commands: sync_managers, list_managers, add_guild_manager,
    #                  remove_guild_manager, add_bot_developer, set_permission_level)
    # =========================================================================
    manager_cog = bot.get_cog("Manager")
    assert manager_cog is not None, "Manager cog must be loaded"

    dummy_target_user = MagicMock(spec=discord.User)
    dummy_target_user.id = SECOND_USER_ID
    dummy_target_user.name = "AssistantMock"
    dummy_target_user.discriminator = "0001"

    async def test_sync_managers_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.sync_managers.callback(manager_cog, interaction)
        text = get_response_text(interaction)
        assert "Successfully synced" in text

    await execute_test("Manager - /sync_managers (Server Owner / Bot Dev)", test_sync_managers_authorized())

    async def test_sync_managers_unauthorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=REGULAR_USER_ID, user_name="RegUser", is_admin=False)
        await manager_cog.sync_managers.callback(manager_cog, interaction)
        text = get_response_text(interaction)
        assert "don't have permission" in text

    await execute_test("Manager - /sync_managers (Unauthorized Regular User)", test_sync_managers_unauthorized())

    async def test_manager_list():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        bot.fetch_user = AsyncMock(return_value=dummy_target_user)
        await manager_cog.list_managers.callback(manager_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Managers" in embed.title or "Staff" in embed.title

    await execute_test("Manager - /list_managers", test_manager_list())

    async def test_manager_add_guild_manager_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.add_guild_manager.callback(manager_cog, interaction, user=dummy_target_user)
        text = get_response_text(interaction)
        assert "added as a guild manager" in text

    await execute_test("Manager - /add_guild_manager (Authorized)", test_manager_add_guild_manager_authorized())

    async def test_manager_add_guild_manager_unauthorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=REGULAR_USER_ID, user_name="RegUser", is_admin=False)
        await manager_cog.add_guild_manager.callback(manager_cog, interaction, user=dummy_target_user)
        text = get_response_text(interaction)
        assert "don't have permission" in text

    await execute_test("Manager - /add_guild_manager (Unauthorized Regular User)", test_manager_add_guild_manager_unauthorized())

    async def test_manager_set_permission_levels():
        # Test level 3 (Administrator / Admin)
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.set_permission_level.callback(manager_cog, interaction, user=dummy_target_user, level=3)
        assert "Administrator" in get_response_text(interaction) or "Admin" in get_response_text(interaction)

        # Test level 2 (Moderator / Mod)
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.set_permission_level.callback(manager_cog, interaction, user=dummy_target_user, level=2)
        assert "Moderator" in get_response_text(interaction) or "Mod" in get_response_text(interaction)

        # Test level 4 (Bot Developer / Superuser)
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.set_permission_level.callback(manager_cog, interaction, user=dummy_target_user, level=4)
        assert "Bot Developer" in get_response_text(interaction)

        # Test level 0 (Regular User - demotes)
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.set_permission_level.callback(manager_cog, interaction, user=dummy_target_user, level=0)
        assert "Regular User" in get_response_text(interaction)

    await execute_test("Manager - /set_permission_level (Levels 3, 2, 4, 0)", test_manager_set_permission_levels())

    async def test_manager_set_permission_invalid():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.set_permission_level.callback(manager_cog, interaction, user=dummy_target_user, level=99)
        text = get_response_text(interaction)
        assert "Invalid permission level" in text

    await execute_test("Manager - /set_permission_level (Invalid level 99)", test_manager_set_permission_invalid())

    async def test_manager_remove_guild_manager_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.remove_guild_manager.callback(manager_cog, interaction, user=dummy_target_user)
        text = get_response_text(interaction)
        assert "removed as a guild manager" in text

    await execute_test("Manager - /remove_guild_manager (Authorized)", test_manager_remove_guild_manager_authorized())

    async def test_manager_add_bot_developer():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.add_bot_developer.callback(manager_cog, interaction, user=dummy_target_user)
        text = get_response_text(interaction)
        assert "added as a bot developer" in text

    await execute_test("Manager - /add_bot_developer (Authorized)", test_manager_add_bot_developer())

    # --- NEW TESTS: /sync_commands, /user_level, Tier Mapping & Visibility ---

    async def test_sync_commands_global_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        bot.tree.sync = AsyncMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
        await manager_cog.sync_commands.callback(manager_cog, interaction, guild_only=False)
        text = get_response_text(interaction)
        assert "Successfully synced **3** command(s) globally" in text

    await execute_test("Manager - /sync_commands (Global sync - Admin/Dev)", test_sync_commands_global_authorized())

    async def test_sync_commands_guild_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        bot.tree.sync = AsyncMock(return_value=[MagicMock(), MagicMock()])
        await manager_cog.sync_commands.callback(manager_cog, interaction, guild_only=True)
        text = get_response_text(interaction)
        assert "Successfully synced **2** command(s) to server" in text

    await execute_test("Manager - /sync_commands (Guild-only sync - Admin/Dev)", test_sync_commands_guild_authorized())

    async def test_sync_commands_unauthorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=REGULAR_USER_ID, user_name="RegUser", is_admin=False)
        await manager_cog.sync_commands.callback(manager_cog, interaction, guild_only=False)
        text = get_response_text(interaction)
        assert "must be an Administrator or Bot Developer" in text

    await execute_test("Manager - /sync_commands (Unauthorized regular user blocked)", test_sync_commands_unauthorized())

    async def test_user_level_self_admin():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await manager_cog.user_level.callback(manager_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "User Authorization Level" in embed.title
        field_dict = {f.name: f.value for f in embed.fields}
        assert "User Level Tier" in field_dict
        assert "Admin" in field_dict["User Level Tier"]

    await execute_test("Manager - /user_level (Self inspect - Admin/Dev)", test_user_level_self_admin())

    async def test_user_level_mod_and_user():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)

        # 1. Mod member
        mod_member = MagicMock(spec=discord.Member)
        mod_member.id = 666111222333
        mod_member.display_name = "ModUser"
        mod_member.bot = False
        mod_perms = discord.Permissions(manage_channels=True, view_channel=True)
        mod_member.guild_permissions = mod_perms
        mod_member.roles = []
        interaction.guild.get_member = MagicMock(side_effect=lambda uid: mod_member if uid == 666111222333 else None)

        await manager_cog.user_level.callback(manager_cog, interaction, user=mod_member)
        embed = get_response_embed(interaction)
        assert embed is not None
        field_dict = {f.name: f.value for f in embed.fields}
        assert "Mod" in field_dict["User Level Tier"]

        # 2. Regular user member
        reg_interaction, _, _, _ = DummyInteractionFactory.create(bot)
        reg_member = MagicMock(spec=discord.Member)
        reg_member.id = REGULAR_USER_ID
        reg_member.display_name = "RegularUser"
        reg_member.bot = False
        reg_member.guild_permissions = discord.Permissions(send_messages=True)
        reg_member.roles = []

        await manager_cog.user_level.callback(manager_cog, reg_interaction, user=reg_member)
        embed = get_response_embed(reg_interaction)
        assert embed is not None
        field_dict = {f.name: f.value for f in embed.fields}
        assert "User" in field_dict["User Level Tier"]

    await execute_test("Manager - /user_level (Mod & User inspections)", test_user_level_mod_and_user())

    async def test_tier_mapping_unit():
        assert manager_cog.get_tier_name(PermissionLevel.BOT_DEVELOPER) == "Admin"
        assert manager_cog.get_tier_name(PermissionLevel.ADMIN) == "Admin"
        assert manager_cog.get_tier_name(PermissionLevel.GUILD_MANAGER) == "Admin"
        assert manager_cog.get_tier_name(PermissionLevel.MODERATOR) == "Mod"
        assert manager_cog.get_tier_name(PermissionLevel.GROUP_OWNER) == "Mod"
        assert manager_cog.get_tier_name(PermissionLevel.GROUP_MEMBER) == "User"
        assert manager_cog.get_tier_name(PermissionLevel.REGULAR_USER) == "User"

    await execute_test("Manager - Tier Mapping Logic (User, Mod, Admin)", test_tier_mapping_unit())

    # =========================================================================
    # 4. CHECKIN COG (Commands: settings_checkin, checkin, & 6 interactive callbacks)
    # =========================================================================
    checkin_cog = bot.get_cog("CheckinCog")
    assert checkin_cog is not None, "CheckinCog cog must be loaded"

    async def test_checkin_settings_default():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_cog.settings_checkin.callback(
            checkin_cog, interaction, max_members=12, min_duration=30, max_duration=7200
        )
        text = get_response_text(interaction)
        assert "Check-in settings updated" in text

    await execute_test("Checkin - /settings_checkin (Standard bounds)", test_checkin_settings_default())

    async def test_checkin_settings_unauthorized():
        interaction, _, _, _ = DummyInteractionFactory.create(
            bot, user_id=REGULAR_USER_ID, user_name="RegUser", is_admin=False
        )
        await checkin_cog.settings_checkin.callback(
            checkin_cog, interaction, max_members=12
        )
        text = get_response_text(interaction)
        assert "do not have permission" in text

    await execute_test("Checkin - /settings_checkin (Unauthorized non-admin blocked)", test_checkin_settings_unauthorized())

    async def test_checkin_settings_custom_restrictive():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_cog.settings_checkin.callback(
            checkin_cog, interaction, max_members=5, min_duration=10, max_duration=14400, max_absences=2, permission_mode="DENY"
        )
        text = get_response_text(interaction)
        assert "Check-in settings updated" in text
        settings = checkin_cog.guild_settings[GUILD_ID]
        assert settings.max_members == 5
        assert settings.permission_mode == "DENY"

    await execute_test("Checkin - /settings_checkin (Restrictive attributes & DENY mode)", test_checkin_settings_custom_restrictive())

    async def test_checkin_invalid_duration():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_cog.start_checkin.callback(
            checkin_cog, interaction, name="Invalid Time Checkin", mentions=f"<@{USER_ID}>", duration="not_a_time"
        )
        text = get_response_text(interaction)
        assert "Invalid duration format" in text

    await execute_test("Checkin - /checkin (Invalid duration attribute)", test_checkin_invalid_duration())

    checkin_session = None

    async def test_checkin_start_standard():
        nonlocal checkin_session
        # Reset permissive settings for test
        checkin_cog.guild_settings[GUILD_ID].permission_mode = "ALLOW"
        checkin_cog.guild_settings[GUILD_ID].max_members = 15
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_cog.start_checkin.callback(
            checkin_cog, interaction, name="Daily Standup", mentions=f"<@{USER_ID}>", duration="25m"
        )
        assert len(checkin_cog.active_sessions) > 0
        session_id = list(checkin_cog.active_sessions.keys())[-1]
        checkin_session = checkin_cog.active_sessions[session_id]
        assert checkin_session.name == "Daily Standup"
        assert checkin_session.duration == 25 * 60

    await execute_test("Checkin - /checkin (Standard '25m' duration)", test_checkin_start_standard())

    async def test_checkin_callbacks_full_lifecycle():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)

        # 1. Present
        await checkin_session.mark_present_callback(interaction)
        assert checkin_session.member_statuses[USER_ID]["status"] == "present"

        # 2. Break
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_session.start_break_callback(interaction)
        assert checkin_session.member_statuses[USER_ID]["status"] == "break"

        # 3. Join
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_session.join_session_callback(interaction)
        assert checkin_session.member_statuses[USER_ID]["status"] == "present"

        # 4. Leave
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_session.leave_session_callback(interaction)
        assert checkin_session.member_statuses[USER_ID]["status"] == "exited"

        # 5. Change Owner
        checkin_session.member_statuses[USER_ID]["status"] = "present"
        checkin_session.member_ids = [USER_ID, SECOND_USER_ID]
        checkin_session.member_statuses[SECOND_USER_ID] = {"status": "present", "absences": 0}
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_session.change_owner_callback(interaction)

        # 6. End Session
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await checkin_session.end_session_callback(interaction)
        assert checkin_session.session_id not in checkin_cog.active_sessions

    await execute_test("Checkin - Callbacks (Present, Break, Join, Leave, Change Owner, End)", test_checkin_callbacks_full_lifecycle())

    # =========================================================================
    # 5. STUDY GROUPS COG (Commands: create_group, list_groups, join_group,
    #                      leave_group, invite_to_group, transfer_group, end_group,
    #                      plus dashboard callbacks)
    # =========================================================================
    sg_cog = bot.get_cog("StudyGroupCog")
    assert sg_cog is not None, "StudyGroupCog cog must be loaded"

    created_group = None

    async def test_sg_create_group_default():
        nonlocal created_group
        interaction, category, _, _ = DummyInteractionFactory.create(bot)
        await sg_cog.create_group.callback(
            sg_cog, interaction, name="Alpha Study Cohort", mentions=f"<@{USER_ID}>", category=category, max_members=10
        )
        assert len(sg_cog.active_study_groups) > 0
        group_id = list(sg_cog.active_study_groups.keys())[-1]
        created_group = sg_cog.active_study_groups[group_id]
        assert created_group.name == "Alpha Study Cohort"
        assert created_group.max_members == 10

    await execute_test("StudyGroups - /create_group (Default attributes)", test_sg_create_group_default())

    async def test_sg_list_groups_with_active():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await sg_cog.list_groups.callback(sg_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Active Study Groups" in embed.title

    await execute_test("StudyGroups - /list_groups (With active groups)", test_sg_list_groups_with_active())

    async def test_sg_join_group_already_member():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await sg_cog.join_group.callback(sg_cog, interaction, name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "already in study group" in text

    await execute_test("StudyGroups - /join_group (Already a member check)", test_sg_join_group_already_member())

    async def test_sg_join_group_new_member():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=SECOND_USER_ID, user_name="AssistantMock")
        await sg_cog.join_group.callback(sg_cog, interaction, name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "Successfully joined study group" in text
        assert SECOND_USER_ID in created_group.member_ids

    await execute_test("StudyGroups - /join_group (New member success)", test_sg_join_group_new_member())

    async def test_sg_join_group_non_existent():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await sg_cog.join_group.callback(sg_cog, interaction, name="Imaginary Group")
        text = get_response_text(interaction)
        assert "No active study group named" in text

    await execute_test("StudyGroups - /join_group (Non-existent group name)", test_sg_join_group_non_existent())

    async def test_sg_invite_to_group_already_member():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        mock_target_member = interaction.guild.get_member(SECOND_USER_ID)
        await sg_cog.invite_to_group.callback(sg_cog, interaction, user=mock_target_member, group_name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "is already a member" in text

    await execute_test("StudyGroups - /invite_to_group (Target already in group)", test_sg_invite_to_group_already_member())

    async def test_sg_invite_to_group_new():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        third_user = interaction.guild.get_member(REGULAR_USER_ID)
        await sg_cog.invite_to_group.callback(sg_cog, interaction, user=third_user, group_name="Alpha Study Cohort")
        # Dispatches invite to group text channel
        assert interaction.channel.send.called

    await execute_test("StudyGroups - /invite_to_group (New invite with interactive buttons)", test_sg_invite_to_group_new())

    async def test_sg_transfer_group_unauthorized():
        interaction, _, _, _ = DummyInteractionFactory.create(
            bot, user_id=REGULAR_USER_ID, user_name="RegUser", is_admin=False
        )
        new_owner = interaction.guild.get_member(SECOND_USER_ID)
        await sg_cog.transfer_group.callback(sg_cog, interaction, new_owner=new_owner, group_name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "Only the group owner" in text or "don't have permission" in text

    await execute_test("StudyGroups - /transfer_group (Unauthorized user rejected)", test_sg_transfer_group_unauthorized())

    async def test_sg_transfer_group_authorized():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        new_owner = interaction.guild.get_member(SECOND_USER_ID)
        await sg_cog.transfer_group.callback(sg_cog, interaction, new_owner=new_owner, group_name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "successfully transferred" in text or "Ownership of study group" in text
        assert created_group.owner_id == SECOND_USER_ID

    await execute_test("StudyGroups - /transfer_group (Authorized transfer by Owner/Mod)", test_sg_transfer_group_authorized())

    async def test_sg_leave_group_by_name():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=SECOND_USER_ID, user_name="AssistantMock")
        await sg_cog.leave_group.callback(sg_cog, interaction, name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "successfully removed from the group" in text or "left the study group" in text

    await execute_test("StudyGroups - /leave_group (With explicit group name)", test_sg_leave_group_by_name())

    async def test_sg_leave_group_non_member():
        interaction, _, _, _ = DummyInteractionFactory.create(bot, user_id=SECOND_USER_ID, user_name="AssistantMock")
        await sg_cog.leave_group.callback(sg_cog, interaction, name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "not a member" in text or "not part of the group" in text

    await execute_test("StudyGroups - /leave_group (Non-member error check)", test_sg_leave_group_non_member())

    async def test_sg_dashboard_callbacks():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)

        # 1. Extend Duration
        await created_group.extend_duration_callback(interaction)
        text = get_response_text(interaction)
        assert "Duration extended" in text

        # 2. Speak Toggle
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await created_group.speak_toggle_callback(interaction)
        assert "Speak Toggle" in get_response_text(interaction)

        # 3. Video Toggle
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await created_group.video_toggle_callback(interaction)
        assert "Video Toggle" in get_response_text(interaction)

        # 4. Votekick
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await created_group.votekick_callback(interaction)
        assert "feature will be implemented" in get_response_text(interaction)

        # 5. Leave Callback
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await created_group.leave_group_callback(interaction)
        text = get_response_text(interaction)
        assert "removed from the group" in text or "not a member" in text

    await execute_test("StudyGroups - Dashboard Callbacks (Extend, Speak, Video, Kick, Leave)", test_sg_dashboard_callbacks())

    async def test_sg_end_group_slash_command():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await sg_cog.end_group.callback(sg_cog, interaction, name="Alpha Study Cohort")
        text = get_response_text(interaction)
        assert "Ending study group" in text or "has been ended" in text

    await execute_test("StudyGroups - /end_group (Slash command execution)", test_sg_end_group_slash_command())

    # =========================================================================
    # 6. VOICE CHANNELS COG (Commands: create_vc, delete_vc, delete_role, delete_text_channel)
    # =========================================================================
    vc_cog = bot.get_cog("VoiceChannels")
    assert vc_cog is not None, "VoiceChannels cog must be loaded"

    # Setup active study group in DB for voice channels cog
    await bot.db.save_study_group({
        "guild_id": GUILD_ID,
        "name": "VC Module Group",
        "group_id": "test-vc-mod-001",
        "creator_id": USER_ID,
        "owner_id": USER_ID,
        "category_id": 885134444992806900,
        "max_members": 8,
        "group_role_id": 885134444992808000,
        "vc_id": 0,
        "text_id": 885134444992806999,
        "info_embed_id": 0,
        "speak_enabled": 1,
        "video_mode": "off",
        "video_timer": 10,
        "start_time": 1700000000.0,
        "end_time": 1700003600.0,
        "duration": 3600,
        "active": 1,
    })

    async def test_vc_create_default():
        interaction, _, vc, _ = DummyInteractionFactory.create(bot)
        await vc_cog.create_vc.callback(vc_cog, interaction, name=None)
        text = get_response_text(interaction)
        assert "created for the study group" in text

    await execute_test("VoiceChannels - /create_vc (Default name attribute)", test_vc_create_default())

    async def test_vc_create_duplicate_prevented():
        interaction, _, vc, _ = DummyInteractionFactory.create(bot)
        await vc_cog.create_vc.callback(vc_cog, interaction, name="Custom VC")
        text = get_response_text(interaction)
        assert "already exists for this group" in text

    await execute_test("VoiceChannels - /create_vc (Duplicate prevention)", test_vc_create_duplicate_prevented())

    async def test_vc_delete():
        interaction, _, vc, _ = DummyInteractionFactory.create(bot)
        # Update db vc_id so delete_vc matches
        await bot.db.update_voice_channel("test-vc-mod-001", vc.id)
        await vc_cog.delete_vc.callback(vc_cog, interaction, voice_channel=vc)
        text = get_response_text(interaction)
        assert "deleted successfully" in text

    await execute_test("VoiceChannels - /delete_vc", test_vc_delete())

    async def test_vc_delete_role():
        interaction, _, _, role = DummyInteractionFactory.create(bot)
        await vc_cog.delete_role.callback(vc_cog, interaction, role=role)
        text = get_response_text(interaction)
        assert "deleted successfully" in text

    await execute_test("VoiceChannels - /delete_role", test_vc_delete_role())

    async def test_vc_delete_text_channel():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await vc_cog.delete_text_channel.callback(vc_cog, interaction, text_channel=interaction.channel)
        text = get_response_text(interaction)
        assert "deleted successfully" in text

    await execute_test("VoiceChannels - /delete_text_channel", test_vc_delete_text_channel())

    # =========================================================================
    # 7. POMODORO COG (Commands: start_pomodoro, pomodoro_status,
    #                  pause_pomodoro, resume_pomodoro, end_pomodoro)
    # =========================================================================
    pomo_cog = bot.get_cog("Pomodoro")
    assert pomo_cog is not None, "Pomodoro cog must be loaded"

    # Setup study group for Pomodoro testing
    await bot.db.save_study_group({
        "guild_id": GUILD_ID,
        "name": "Pomodoro Cohort",
        "group_id": "test-pomo-uuid-002",
        "creator_id": USER_ID,
        "owner_id": USER_ID,
        "category_id": 885134444992806900,
        "max_members": 6,
        "group_role_id": 885134444992808000,
        "vc_id": 885134444992807000,
        "text_id": 885134444992806999,
        "info_embed_id": 0,
        "speak_enabled": 1,
        "video_mode": "off",
        "video_timer": 10,
        "start_time": 1700000000.0,
        "end_time": 1700003600.0,
        "duration": 3600,
        "active": 1,
    })
    await bot.db.add_member_to_study_group_db("test-pomo-uuid-002", USER_ID)

    async def test_pomo_start_not_in_vc():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        interaction.user.voice = None
        await pomo_cog.start_pomodoro.callback(pomo_cog, interaction, focus=25, short_break=5, long_break=15)
        text = get_response_text(interaction)
        assert "Please join the voice channel" in text

    await execute_test("Pomodoro - /start_pomodoro (Error: User not in voice channel)", test_pomo_start_not_in_vc())

    async def test_pomo_start_custom_durations():
        # Clear any prior session for clean start
        pomo_cog.sessions.clear()
        interaction, _, vc, _ = DummyInteractionFactory.create(bot)
        interaction.user.voice = MagicMock()
        interaction.user.voice.channel = vc
        await pomo_cog.start_pomodoro.callback(pomo_cog, interaction, focus=50, short_break=10, long_break=20)
        text = get_response_text(interaction)
        assert "Pomodoro session started! Focus for 50 minutes" in text
        assert len(pomo_cog.sessions) > 0
        session = list(pomo_cog.sessions.values())[-1]
        assert session.focus == 50
        assert session.short_break == 10
        assert session.long_break == 20
        assert session.timer == 50 * 60

    await execute_test("Pomodoro - /start_pomodoro (Custom attributes: 50m/10m/20m)", test_pomo_start_custom_durations())

    async def test_pomo_status_active():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await pomo_cog.pomodoro_status.callback(pomo_cog, interaction)
        embed = get_response_embed(interaction)
        assert embed is not None
        assert "Pomodoro Status" in embed.title
        field_names = [f.name for f in embed.fields]
        assert "Current Stage" in field_names
        assert "Time Remaining" in field_names

    await execute_test("Pomodoro - /pomodoro_status (Active running session)", test_pomo_status_active())

    async def test_pomo_pause_and_resume():
        # 1. Pause
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await pomo_cog.pause_pomodoro.callback(pomo_cog, interaction)
        text = get_response_text(interaction)
        assert "paused" in text
        session = list(pomo_cog.sessions.values())[-1]
        assert session.is_paused is True

        # 2. Resume
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await pomo_cog.resume_pomodoro.callback(pomo_cog, interaction)
        text = get_response_text(interaction)
        assert "resumed" in text
        assert session.is_paused is False

    await execute_test("Pomodoro - /pause_pomodoro and /resume_pomodoro", test_pomo_pause_and_resume())

    async def test_pomo_end_active():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await pomo_cog.end_pomodoro.callback(pomo_cog, interaction)
        text = get_response_text(interaction)
        assert "ended" in text
        assert len(pomo_cog.sessions) == 0

    await execute_test("Pomodoro - /end_pomodoro (Active session)", test_pomo_end_active())

    async def test_pomo_status_inactive():
        interaction, _, _, _ = DummyInteractionFactory.create(bot)
        await pomo_cog.pomodoro_status.callback(pomo_cog, interaction)
        text = get_response_text(interaction)
        assert "No active Pomodoro session" in text

    await execute_test("Pomodoro - /pomodoro_status (No active session)", test_pomo_status_inactive())

    # =========================================================================
    # 8. SLASH COMMAND INVISIBILITY & DEFAULT PERMISSIONS
    # =========================================================================
    async def test_command_permissions_visibility():
        # Admin-only commands: must require administrator=True (invisible to non-admins in Discord UI)
        admin_commands = [
            manager_cog.sync_commands,
            manager_cog.sync_managers,
            manager_cog.add_bot_developer,
            manager_cog.add_guild_manager,
            manager_cog.remove_guild_manager,
            manager_cog.set_permission_level,
            checkin_cog.settings_checkin,
        ]
        for cmd in admin_commands:
            assert cmd.default_permissions is not None, f"Command {cmd.name} must have default_permissions set"
            assert cmd.default_permissions.administrator is True, f"Command {cmd.name} must require administrator permission"

        # Moderator-level commands: must require manage_guild or manage_channels/roles
        assert manager_cog.list_managers.default_permissions is not None
        assert manager_cog.list_managers.default_permissions.manage_guild is True

        assert vc_cog.delete_vc.default_permissions is not None
        assert vc_cog.delete_vc.default_permissions.manage_channels is True

        assert vc_cog.delete_text_channel.default_permissions is not None
        assert vc_cog.delete_text_channel.default_permissions.manage_channels is True

        assert vc_cog.delete_role.default_permissions is not None
        assert vc_cog.delete_role.default_permissions.manage_roles is True

        # General user commands: must be visible to everyone (default_permissions is None)
        user_commands = [
            manager_cog.user_level,
            sg_cog.create_group,
            sg_cog.list_groups,
            sg_cog.join_group,
            sg_cog.leave_group,
            tasklist_cog.add_task,
            tasklist_cog.list_tasks,
            prod_cog.productivity,
            checkin_cog.start_checkin,
        ]
        for cmd in user_commands:
            assert cmd.default_permissions is None, f"Command {cmd.name} should be visible to regular users"

    await execute_test("Permissions - Slash Command Invisibility & default_permissions Check", test_command_permissions_visibility())

    # Cleanup test groups
    await bot.db.delete_study_group("test-vc-mod-001")
    await bot.db.delete_study_group("test-pomo-uuid-002")
    await bot.close()

    logger.info("=" * 80)
    logger.info(f"ALL COMMAND & ATTRIBUTE TESTS COMPLETED: {passed_tests}/{total_tests} PASSED (100% SUCCESS)")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_feature_tests())
