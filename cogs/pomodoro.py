import logging
import random
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import check_manager

# Set up logging
logger = logging.getLogger(__name__)

FOCUS_END_SHORT_BREAK_MESSAGES = [
    "🎉 Focus block conquered! Step away, stretch your limbs, and take a well-deserved {m}-minute breather.",
    "🔔 Ding ding ding! Focus sprint complete. Give your brain a break for {m} minutes!",
    "🧠 Brain recharge initiated! Step away from the screen, grab some water, and relax for {m} minutes.",
    "⚡ Incredible momentum! Hit pause, uncurl your spine, and enjoy a {m}-minute rest.",
    "🚀 Sprint done! Shake out the fidgets, look at something far away, and chill for {m} minutes.",
    "🌟 Dopamine checkpoint reached! Time to pause and bask in your accomplishment for {m} minutes.",
    "☕ Kettle time! Step away from your workspace and enjoy a nice {m}-minute pause.",
    "🧘 Deep breath in... and out. You're doing amazing! Enjoy your {m}-minute breather.",
    "🎯 Focus time checked off! No work allowed for the next {m} minutes. You've earned this!",
    "✨ Sprint complete! Stand up, stretch those shoulders, and enjoy {m} minutes of freedom.",
    "🌈 Pause button pressed! Give those eyes a rest and vibe for {m} minutes.",
    "🛋️ Step back and unwind! Your brain just worked hard, let it coast for {m} minutes.",
    "💧 Hydration alert & break time! Drink some water, stroll around, and relax for {m} minutes.",
    "🌱 Unplug for {m} minutes! Reset your mental tabs before the next round.",
    "🎮 Quick intermission! Step away, stretch, and let your mind wander for {m} minutes."
]

FOCUS_END_LONG_BREAK_MESSAGES = [
    "🏆 4 full focus cycles completed! That is legendary stamina. Enjoy a glorious {m}-minute long break!",
    "🎉 Major milestone unlocked: 4 rounds done! Time to disconnect completely and recharge for {m} minutes.",
    "🥳 Huge win! You powered through 4 cycles! Go grab a snack, take a walk, or vibe for {m} minutes.",
    "🌟 You're unstoppable today! 4 Pomodoro cycles in the bag. Enjoy your well-earned {m}-minute retreat.",
    "🍕 Legendary focus unlocked! Four sprints conquered. Step completely away from your desk for {m} minutes.",
    "👑 Peak productivity achieved! Treat yourself to a proper {m}-minute break. Hydrate, snack, relax!",
    "🚀 Incredible endurance! You just finished a full 4-cycle loop. Rest and rejuvenate for {m} minutes.",
    "🎈 4 cycles down! That's a massive achievement. Relax your mind and recharge for {m} minutes."
]

BREAK_END_FOCUS_MESSAGES = [
    "🎯 Break's over! Let's lock in and tackle the next {m} minutes of focus together.",
    "⚡ Back in the zone! Clear those open tabs, take a deep breath, and let's conquer the next {m} minutes.",
    "🚀 Time to build momentum! Pick your next micro-task and let's dive into {m} minutes of focus.",
    "🔥 Ready to roll? Reset your focus, hydrate, and let's crush the next {m} minutes!",
    "🧠 Dopamine aligned! Pick one small step to start with and let's knock out this {m}-minute sprint.",
    "🌟 Fresh sprint starting! Jump back in and let's make progress for the next {m} minutes.",
    "🛠️ Back to the craft! Settle into your workspace and let's focus for {m} minutes.",
    "📚 Time to lock in! Set your goal for this block and let's crush {m} minutes.",
    "✨ Ready, set, focus! Put on your favorite focus tracks and let's work for {m} minutes.",
    "🦾 Powering up the focus engine! Take a deep breath and let's do this for {m} minutes."
]


def calculate_pomodoro_ratio(
    focus: Optional[int] = None,
    short_break: Optional[int] = None,
    long_break: Optional[int] = None
) -> Tuple[int, int, int]:
    """
    Auto-calculate Pomodoro timings using a 5:1:3 ratio (Focus : Short Break : Long Break).
    Default is 25:5:15 if none are specified.
    """
    provided = [x is not None for x in (focus, short_break, long_break)]

    if all(provided):
        return (max(1, focus), max(1, short_break), max(1, long_break))  # type: ignore

    if not any(provided):
        return (25, 5, 15)

    if focus is not None and short_break is None and long_break is None:
        f = max(1, focus)
        sb = max(1, round(f * 1 / 5))
        lb = max(1, round(f * 3 / 5))
        return (f, sb, lb)

    if short_break is not None and focus is None and long_break is None:
        sb = max(1, short_break)
        f = max(1, round(sb * 5 / 1))
        lb = max(1, round(sb * 3 / 1))
        return (f, sb, lb)

    if long_break is not None and focus is None and short_break is None:
        lb = max(1, long_break)
        f = max(1, round(lb * 5 / 3))
        sb = max(1, round(lb * 1 / 3))
        return (f, sb, lb)

    if focus is not None and short_break is not None and long_break is None:
        f = max(1, focus)
        sb = max(1, short_break)
        lb = max(1, round(f * 3 / 5))
        return (f, sb, lb)

    if focus is not None and long_break is not None and short_break is None:
        f = max(1, focus)
        lb = max(1, long_break)
        sb = max(1, round(f * 1 / 5))
        return (f, sb, lb)

    if short_break is not None and long_break is not None and focus is None:
        sb = max(1, short_break)
        lb = max(1, long_break)
        f = max(1, round(sb * 5 / 1))
        return (f, sb, lb)

    return (25, 5, 15)


class PomodoroSession:
    def __init__(
        self,
        group_id: Any,
        focus: int,
        short_break: int,
        long_break: int,
        guild_id: Optional[int] = None,
        text_id: Optional[int] = None,
        vc_id: Optional[int] = None,
        require_vc: bool = True
    ):
        self.group_id = group_id
        self.guild_id = guild_id
        self.text_id = text_id
        self.vc_id = vc_id
        self.require_vc = require_vc
        self.focus = focus
        self.short_break = short_break
        self.long_break = long_break
        self.current_stage = "focus"
        self.cycles = 0
        self.is_paused = False
        self.timer = focus * 60
        logger.info(
            f"Pomodoro session created for group {group_id} with focus: {focus}m, "
            f"short break: {short_break}m, long break: {long_break}m, require_vc={require_vc}"
        )


class Pomodoro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions: Dict[Any, PomodoroSession] = {}
        logger.info("Pomodoro cog initialized")

    async def _resolve_group(self, interaction: discord.Interaction) -> Optional[Dict[str, Any]]:
        """Resolve target study group for the interaction."""
        # 1. Check if user is a member of an active group in this channel or anywhere
        group = await self.bot.db.get_user_group(interaction.user.id, interaction.channel_id)
        if group:
            return group

        # 2. If in a text channel or voice channel, check if this channel belongs to a study group
        if interaction.channel_id:
            channel_group = await self.bot.db.get_study_group_by_channel(interaction.channel_id)
            if channel_group:
                is_mgr = await check_manager(interaction)
                members = await self.bot.db.fetch_members_of_group(channel_group.get('group_id') or str(channel_group.get('id')))
                if interaction.user.id in members or interaction.user.id in (channel_group.get('creator_id'), channel_group.get('owner_id')) or is_mgr:
                    return channel_group

        # 3. If user is a server manager or server owner, fallback to the guild's active group
        if interaction.guild_id and await check_manager(interaction):
            guild_group = await self.bot.db.get_study_group(interaction.guild_id)
            if guild_group:
                return guild_group

        return None

    def _get_session(self, group: Dict[str, Any]) -> Optional[PomodoroSession]:
        """Retrieve active Pomodoro session by group id or UUID."""
        if not group:
            return None
        gid = group.get('id')
        uuid_str = group.get('group_id')
        return self.sessions.get(gid) or (self.sessions.get(uuid_str) if uuid_str else None)

    async def _update_group_gui(self, group_id: Any):
        """Helper to trigger embed update on the study group cog if active."""
        try:
            sg_cog = self.bot.get_cog("StudyGroupCog")
            if sg_cog:
                target = sg_cog.active_study_groups.get(str(group_id))
                if not target:
                    for g in sg_cog.active_study_groups.values():
                        if str(g.group_id) == str(group_id):
                            target = g
                            break
                if target:
                    await target.group_info_embed(update=True)
        except Exception as e:
            logger.debug(f"Could not refresh study group GUI: {e}")

    @app_commands.command(name="start_pomodoro", description="Start a Pomodoro session for the study group")
    @app_commands.describe(
        focus="Focus duration in minutes (auto-calculates breaks if omitted, default 25)",
        short_break="Short break duration in minutes (auto-calculates other timings if omitted)",
        long_break="Long break duration in minutes (auto-calculates other timings if omitted)",
        require_vc="Require members to join Voice Channel (default True, set False for text-only)"
    )
    async def start_pomodoro(
        self,
        interaction: discord.Interaction,
        focus: Optional[int] = None,
        short_break: Optional[int] = None,
        long_break: Optional[int] = None,
        require_vc: bool = True
    ):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        logger.info(f"Attempt to start Pomodoro session by user {interaction.user.id}")

        group = await self._resolve_group(interaction)
        if not group:
            logger.warning(f"User {interaction.user.id} tried to start Pomodoro without being in a group")
            msg = "You're not in any study group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        existing_session = self._get_session(group)
        if existing_session:
            logger.info(f"Pomodoro session already exists for group {group['id']}")
            msg = "A Pomodoro session is already in progress for this group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        # Auto-calculate timings using 5:1:3 ratio
        focus_calc, short_calc, long_calc = calculate_pomodoro_ratio(focus, short_break, long_break)

        if not interaction.guild:
            msg = "This command can only be used in a server."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        voice_channel: Optional[discord.VoiceChannel] = None
        if require_vc:
            voice_channel_id = group.get('vc_id')
            if not voice_channel_id:
                voice_channel = await interaction.guild.create_voice_channel(f"{group['name']} VC")
                await self.bot.db.update_voice_channel(group['id'], voice_channel.id)
                logger.info(f"Created new voice channel {voice_channel.id} for group {group['id']}")
            else:
                ch = interaction.guild.get_channel(voice_channel_id)
                if isinstance(ch, discord.VoiceChannel):
                    voice_channel = ch

            if not voice_channel:
                msg = "Could not locate or create a voice channel."
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return

            if isinstance(interaction.user, discord.Member) and interaction.user.voice:
                try:
                    await interaction.user.move_to(voice_channel)
                    logger.info(f"Moved user {interaction.user.id} to voice channel {voice_channel.id}")
                except Exception as e:
                    logger.warning(f"Could not move user to voice channel: {e}")
            else:
                logger.warning(f"User {interaction.user.id} is not in a voice channel")
                msg = f"Please join the voice channel {voice_channel.mention} to start the Pomodoro session (or use `require_vc: False`)."
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return

        session = PomodoroSession(
            group_id=group.get('group_id') or group['id'],
            focus=focus_calc,
            short_break=short_calc,
            long_break=long_calc,
            guild_id=interaction.guild_id,
            text_id=group.get('text_id'),
            vc_id=group.get('vc_id'),
            require_vc=require_vc
        )

        self.sessions[group['id']] = session
        if group.get('group_id'):
            self.sessions[group['group_id']] = session

        if not self.run_timer.is_running():
            self.run_timer.start()

        logger.info(f"Started Pomodoro session for group {group['id']} (require_vc={require_vc})")
        mode_text = "🔊 Voice Channel Required" if require_vc else "💬 Text-Only Mode"
        response_msg = (
            f"🍅 **Pomodoro session started!**\n"
            f"• **Focus**: {focus_calc}m\n"
            f"• **Short Break**: {short_calc}m\n"
            f"• **Long Break**: {long_calc}m (every 4 cycles)\n"
            f"• **Mode**: {mode_text}"
        )
        if interaction.response.is_done():
            await interaction.followup.send(response_msg)
        else:
            await interaction.response.send_message(response_msg)

        await self._update_group_gui(group.get('group_id') or group['id'])

    @app_commands.command(name="edit_pomodoro", description="Edit timings or VC settings for the active Pomodoro session")
    @app_commands.describe(
        focus="New focus duration in minutes (auto-calculates breaks if others omitted)",
        short_break="New short break duration in minutes",
        long_break="New long break duration in minutes",
        require_vc="Toggle whether Voice Channel is required"
    )
    async def edit_pomodoro(
        self,
        interaction: discord.Interaction,
        focus: Optional[int] = None,
        short_break: Optional[int] = None,
        long_break: Optional[int] = None,
        require_vc: Optional[bool] = None
    ):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        group = await self._resolve_group(interaction)
        session = self._get_session(group)
        if not group or not session:
            msg = "No active Pomodoro session found for your group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        # Check permissions: owner, creator, or manager
        is_mgr = await check_manager(interaction)
        if interaction.user.id not in (group.get('creator_id'), group.get('owner_id')) and not is_mgr:
            msg = "Only the group owner or a server manager can edit Pomodoro settings."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        # Handle timing changes
        if any(x is not None for x in (focus, short_break, long_break)):
            # If only one was provided, auto-calculate with ratio
            f_calc, sb_calc, lb_calc = calculate_pomodoro_ratio(
                focus if focus is not None else (None if (short_break is not None or long_break is not None) else session.focus),
                short_break if short_break is not None else None,
                long_break if long_break is not None else None
            )
            session.focus = f_calc
            session.short_break = sb_calc
            session.long_break = lb_calc

            # Adjust timer cap if current stage duration shrank
            if session.current_stage == "focus" and session.timer > session.focus * 60:
                session.timer = session.focus * 60
            elif session.current_stage == "short_break" and session.timer > session.short_break * 60:
                session.timer = session.short_break * 60
            elif session.current_stage == "long_break" and session.timer > session.long_break * 60:
                session.timer = session.long_break * 60

        if require_vc is not None:
            session.require_vc = require_vc

        embed = discord.Embed(title="⚙️ Pomodoro Settings Updated", color=discord.Color.green())
        embed.add_field(name="Focus Duration", value=f"{session.focus} minutes", inline=True)
        embed.add_field(name="Short Break", value=f"{session.short_break} minutes", inline=True)
        embed.add_field(name="Long Break", value=f"{session.long_break} minutes", inline=True)
        embed.add_field(name="Mode", value="🔊 Voice Channel Required" if session.require_vc else "💬 Text-Only Mode", inline=False)
        embed.add_field(name="Current Stage Timer", value=str(timedelta(seconds=max(0, session.timer))), inline=True)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

        await self._update_group_gui(group.get('group_id') or group['id'])

    @app_commands.command(name="end_pomodoro", description="End the current Pomodoro session")
    async def end_pomodoro(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        logger.info(f"Attempt to end Pomodoro session by user {interaction.user.id}")
        group = await self._resolve_group(interaction)
        session = self._get_session(group)
        if not group or not session:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            msg = "No active Pomodoro session for your group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        self.sessions.pop(group['id'], None)
        if group.get('group_id'):
            self.sessions.pop(group['group_id'], None)

        if not self.sessions and self.run_timer.is_running():
            self.run_timer.stop()
        logger.info(f"Ended Pomodoro session for group {group['id']}")
        if interaction.response.is_done():
            await interaction.followup.send("Pomodoro session ended.")
        else:
            await interaction.response.send_message("Pomodoro session ended.")

        await self._update_group_gui(group.get('group_id') or group['id'])

    @app_commands.command(name="pause_pomodoro", description="Pause the current Pomodoro session")
    async def pause_pomodoro(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        logger.info(f"Attempt to pause Pomodoro session by user {interaction.user.id}")
        group = await self._resolve_group(interaction)
        session = self._get_session(group)
        if not group or not session:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            msg = "No active Pomodoro session for your group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        if session.is_paused:
            msg = "Session is already paused."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        session.is_paused = True
        logger.info(f"Paused Pomodoro session for group {group['id']}")
        if interaction.response.is_done():
            await interaction.followup.send("Pomodoro session paused.")
        else:
            await interaction.response.send_message("Pomodoro session paused.")

        await self._update_group_gui(group.get('group_id') or group['id'])

    @app_commands.command(name="resume_pomodoro", description="Resume the paused Pomodoro session")
    async def resume_pomodoro(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        logger.info(f"Attempt to resume Pomodoro session by user {interaction.user.id}")
        group = await self._resolve_group(interaction)
        session = self._get_session(group)
        if not group or not session:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            msg = "No active Pomodoro session for your group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        if not session.is_paused:
            msg = "Session is not paused."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        session.is_paused = False
        logger.info(f"Resumed Pomodoro session for group {group['id']}")
        if interaction.response.is_done():
            await interaction.followup.send("Pomodoro session resumed.")
        else:
            await interaction.response.send_message("Pomodoro session resumed.")

        await self._update_group_gui(group.get('group_id') or group['id'])

    @tasks.loop(seconds=1)
    async def run_timer(self):
        # Use set to avoid double-processing if keyed by both id and UUID
        seen_sessions = set()
        for group_id, session in list(self.sessions.items()):
            if id(session) in seen_sessions:
                continue
            seen_sessions.add(id(session))

            if session.is_paused:
                continue

            if session.timer is None:
                session.timer = session.focus * 60

            session.timer -= 1

            if session.timer <= 0:
                guild_id = session.guild_id
                if session.current_stage == "focus":
                    session.cycles += 1
                    if session.cycles % 4 == 0:
                        session.current_stage = "long_break"
                        session.timer = session.long_break * 60
                        logger.info(f"Group {group_id} starting long break")
                        msg = random.choice(FOCUS_END_LONG_BREAK_MESSAGES).format(m=session.long_break)
                        await self.send_notification(guild_id, group_id, msg)
                    else:
                        session.current_stage = "short_break"
                        session.timer = session.short_break * 60
                        logger.info(f"Group {group_id} starting short break")
                        msg = random.choice(FOCUS_END_SHORT_BREAK_MESSAGES).format(m=session.short_break)
                        await self.send_notification(guild_id, group_id, msg)
                else:
                    session.current_stage = "focus"
                    session.timer = session.focus * 60
                    logger.info(f"Group {group_id} starting focus session")
                    msg = random.choice(BREAK_END_FOCUS_MESSAGES).format(m=session.focus)
                    await self.send_notification(guild_id, group_id, msg)

                await self._update_group_gui(session.group_id)

    async def send_notification(self, guild_id, group_id, message):
        """Strictly route Pomodoro notifications to the group's text or VC channel."""
        if not guild_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        session = self.sessions.get(group_id)
        text_id = getattr(session, 'text_id', None)
        vc_id = getattr(session, 'vc_id', None)
        require_vc = getattr(session, 'require_vc', True)

        # Fallback to database lookup if IDs missing from session
        if not text_id or not vc_id:
            db_grp = await self.bot.db.fetch_study_group_by_id(group_id)
            if db_grp:
                text_id = text_id or db_grp.get('text_id')
                vc_id = vc_id or db_grp.get('vc_id')

        # Format role mention
        role_mention = ""
        _, session_role_id = await self.bot.db.get_group_roles(group_id)
        if session_role_id:
            role = guild.get_role(session_role_id)
            if role:
                role_mention = f"{role.mention} "

        notification_sent = False

        # 1. If require_vc is enabled and voice channel exists, send to the voice channel
        if require_vc and vc_id:
            voice_channel = guild.get_channel(vc_id)
            if voice_channel and (isinstance(voice_channel, discord.VoiceChannel) or hasattr(voice_channel, 'send')):
                try:
                    await voice_channel.send(f"{role_mention}{message}")
                    logger.info(f"Sent notification to voice channel {vc_id} for group {group_id}")
                    notification_sent = True
                except Exception as e:
                    logger.warning(f"Could not send notification to VC {vc_id}: {e}")

        # 2. If not sent to VC or require_vc is False, send strictly to the group's text channel
        if not notification_sent and text_id:
            text_channel = guild.get_channel(text_id)
            if text_channel and (isinstance(text_channel, (discord.TextChannel, discord.Thread)) or hasattr(text_channel, 'send')):
                try:
                    await text_channel.send(f"{role_mention}{message}")
                    logger.info(f"Sent notification to group text channel {text_id} for group {group_id}")
                    notification_sent = True
                except Exception as e:
                    logger.error(f"Error sending notification to group text channel {text_id}: {e}")

        if not notification_sent:
            logger.warning(f"Could not route notification for group {group_id}: no valid group text or voice channel found.")

    @app_commands.command(name="pomodoro_status", description="Check the status of the current Pomodoro session")
    async def pomodoro_status(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        logger.info(f"Pomodoro status check by user {interaction.user.id}")
        group = await self._resolve_group(interaction)
        session = self._get_session(group)

        if not group or not session:
            logger.warning(f"No active Pomodoro session for user {interaction.user.id}")
            msg = "No active Pomodoro session for your group."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        timer_seconds = session.timer if session.timer is not None else session.focus * 60
        remaining_time = timedelta(seconds=max(0, timer_seconds))
        status = "Paused" if session.is_paused else "Running"
        stage_names = {
            "focus": "🎯 Focus",
            "short_break": "☕ Short Break",
            "long_break": "🌴 Long Break"
        }
        stage = stage_names.get(session.current_stage, session.current_stage.capitalize())

        embed = discord.Embed(title="Pomodoro Status", color=discord.Color.blue())
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Current Stage", value=stage, inline=True)
        embed.add_field(name="Time Remaining", value=str(remaining_time), inline=True)
        embed.add_field(name="Completed Cycles", value=str(session.cycles), inline=True)
        embed.add_field(name="Mode", value="🔊 Voice Required" if session.require_vc else "💬 Text-Only", inline=True)

        logger.info(f"Sent Pomodoro status for group {group['id']}")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Pomodoro(bot))
    logger.info("Pomodoro cog loaded")
