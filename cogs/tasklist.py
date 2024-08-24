import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TaskList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Tasklist cog initialized")

    @app_commands.command(name="task_add", description="Add a new task to your list")
    async def add_task(self, interaction: discord.Interaction, *, description: str):
        task_id = await self.bot.db.add_task(interaction.user.id, description)
        await interaction.response.send_message(f"Task added successfully. Task ID: {task_id}")

    @app_commands.command(name="task_complete", description="Mark a task as complete")
    async def complete_task(self, interaction: discord.Interaction, task_id: int):
        success = await self.bot.db.complete_task(interaction.user.id, task_id)
        if success:
            await interaction.response.send_message(f"Task {task_id} marked as complete.")
        else:
            await interaction.response.send_message(f"Task {task_id} not found or already completed.")

    @app_commands.command(name="task_list", description="List your current tasks")
    async def list_tasks(self, interaction: discord.Interaction):
        tasks = await self.bot.db.get_user_tasks(interaction.user.id)
        if tasks:
            embed = discord.Embed(title=f"{interaction.user.display_name}'s Tasks", color=discord.Color.blue())
            for task in tasks:
                status = "Completed" if task[3] else "In Progress"
                embed.add_field(name=f"Task {task[0]}", value=f"{task[2]} - {status}", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("You have no tasks.")

async def setup(bot):
    await bot.add_cog(TaskList(bot))
    logger.info("Loaded TaskList cog")