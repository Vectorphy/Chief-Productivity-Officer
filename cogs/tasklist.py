import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

class TaskList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Tasklist cog initialized")

    @app_commands.command(name="task_add", description="Add a new task to your list (scoped to group if inside group channel)")
    @app_commands.describe(description="The task description")
    async def add_task(self, interaction: discord.Interaction, *, description: str):
        group_id = None
        group_name = None
        channel_id = getattr(interaction, 'channel_id', None)
        if isinstance(channel_id, int):
            group = await self.bot.db.get_study_group_by_channel(channel_id)
            if group and isinstance(group, dict):
                group_id = group.get('group_id') or str(group.get('id'))
                group_name = group.get('name')

        if group_id:
            task_id = await self.bot.db.add_task(interaction.user.id, description, group_id=group_id)
            await interaction.response.send_message(f"Task #{task_id} added successfully to **{group_name}**: {description}")
        else:
            task_id = await self.bot.db.add_task(interaction.user.id, description)
            await interaction.response.send_message(f"Task added successfully. Task ID: {task_id}")

    @app_commands.command(name="task_complete", description="Mark a task as complete")
    @app_commands.describe(task_id="The ID or task number to complete")
    async def complete_task(self, interaction: discord.Interaction, task_id: int):
        group_id = None
        channel_id = getattr(interaction, 'channel_id', None)
        if isinstance(channel_id, int):
            group = await self.bot.db.get_study_group_by_channel(channel_id)
            if group and isinstance(group, dict):
                group_id = group.get('group_id') or str(group.get('id'))

        if group_id:
            success = await self.bot.db.complete_task(interaction.user.id, task_id, group_id=group_id)
        else:
            success = await self.bot.db.complete_task(interaction.user.id, task_id)

        if success:
            await interaction.response.send_message(f"Task {task_id} marked as complete.")
        else:
            await interaction.response.send_message(f"Task {task_id} not found or already completed.")

    @app_commands.command(name="task_list", description="List your current tasks")
    @app_commands.describe(all_groups="Show tasks across all groups (default False if inside a group)")
    async def list_tasks(self, interaction: discord.Interaction, all_groups: bool = False):
        group_id = None
        group_name = None
        channel_id = getattr(interaction, 'channel_id', None)
        if not all_groups and isinstance(channel_id, int):
            group = await self.bot.db.get_study_group_by_channel(channel_id)
            if group and isinstance(group, dict):
                group_id = group.get('group_id') or str(group.get('id'))
                group_name = group.get('name')

        if group_id:
            tasks = await self.bot.db.get_user_tasks(interaction.user.id, group_id=group_id)
            title = f"{interaction.user.display_name}'s Tasks — {group_name}"
        else:
            tasks = await self.bot.db.get_user_tasks(interaction.user.id)
            title = f"{interaction.user.display_name}'s Tasks"

        if not tasks:
            await interaction.response.send_message("You have no tasks.")
            return

        embed = discord.Embed(title=title, color=discord.Color.blue())

        # Safe formatting that avoids Discord's 25 embed field limit
        lines = []
        for task in tasks:
            try:
                # sqlite3.Row access
                t_id = task['task_number'] if ('task_number' in task.keys() and task['task_number']) else task['id']
                t_desc = task['description']
                t_comp = bool(task['completed'])
            except (TypeError, IndexError, AttributeError):
                # tuple fallback
                t_id = task[0]
                t_desc = task[2] if len(task) > 2 else "Task"
                t_comp = bool(task[3]) if len(task) > 3 else False

            status_icon = "✅" if t_comp else "⏳"
            status_text = "Completed" if t_comp else "In Progress"
            lines.append(f"{status_icon} **Task #{t_id}**: {t_desc} — *{status_text}*")

        if len(lines) <= 20:
            embed.description = "\n".join(lines)
        else:
            embed.description = "\n".join(lines[:25]) + f"\n\n*...and {len(lines) - 25} more tasks.*"

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TaskList(bot))
    logger.info("Loaded TaskList cog")
