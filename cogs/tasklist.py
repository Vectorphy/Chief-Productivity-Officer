import discord
from discord import app_commands
from discord.ext import commands
import logging
import pymongo.errors  # Import for handling PyMongo exceptions

logger = logging.getLogger(__name__)

class TaskList(commands.Cog):
    """Cog for managing user task lists."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("Tasklist cog initialized")

    @app_commands.command(name="task_add", description="Add a new task to your list")
    @app_commands.describe(description="The description of your task")
    async def add_task(self, interaction: discord.Interaction, description: str):
        """Adds a task to the user's task list."""
        try:
            task_id = await self.bot.db.add_task(interaction.user.id, description)
            await interaction.response.send_message(f"Task added successfully. Task ID: {task_id}")
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error adding task: {e}")
            await interaction.response.send_message("An error occurred while adding the task. Please try again later.", ephemeral=True)

    @app_commands.command(name="task_complete", description="Mark a task as complete")
    @app_commands.describe(task_id="The ID of the task to mark as complete")
    async def complete_task(self, interaction: discord.Interaction, task_id: int):
        """Marks a task as complete."""
        try:
            success = await self.bot.db.complete_task(interaction.user.id, task_id)
            if success:
                await interaction.response.send_message(f"Task {task_id} marked as complete.")
            else:
                await interaction.response.send_message(f"Task {task_id} not found or already completed.")
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error completing task: {e}")
            await interaction.response.send_message("An error occurred while completing the task. Please try again later.", ephemeral=True)

    @app_commands.command(name="task_list", description="List your current tasks")
    async def list_tasks(self, interaction: discord.Interaction):
        """Lists the user's current tasks."""
        try:
            tasks = await self.bot.db.get_user_tasks(interaction.user.id)
            if tasks:
                embed = discord.Embed(title=f"{interaction.user.display_name}'s Tasks", color=discord.Color.blue())
                for task in tasks:
                    status = "Completed" if task['completed'] else "In Progress"  # Access using dictionary key
                    embed.add_field(name=f"Task {task['id']}", value=f"{task['description']} - {status}", inline=False)  # Access using dictionary keys
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("You have no tasks.")
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error listing tasks: {e}")
            await interaction.response.send_message("An error occurred while listing tasks. Please try again later.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskList(bot))
    logger.info("Loaded TaskList cog")
