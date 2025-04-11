import discord
from discord import app_commands
from discord.ext import commands
import logging, asyncio
from datetime import datetime, timedelta
import pytz
from database import TasksTable

logger = logging.getLogger(__name__)

class TaskList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Tasklist cog initialized")

    def get_user_timezone(self, user_id: int) -> pytz.timezone:
        # Placeholder: In a real app, you'd fetch this from a user profile or settings
        # For this example, we'll default to 'UTC'.
        # In a real app you would probably have a DB query here
        return pytz.timezone('UTC')

    @app_commands.command(name="task_add", description="Add a new task to your list")
    @app_commands.describe(description="Description of the task", due_date="Due date for the task (YYYY-MM-DD HH:MM)", reminder="Set a reminder for the task? (true/false)")
    async def add_task(self, interaction: discord.Interaction, description: str, due_date: str = None, reminder: bool = False):
        try:
            user_timezone = self.get_user_timezone(interaction.user.id)
            
            # Parse due date with timezone awareness
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                    due_date = user_timezone.localize(due_date)  # Localize to user's timezone
                except ValueError:
                    await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD HH:MM.", ephemeral=True)
                    return

            task_id = await self.bot.db.add_task(interaction.user.id, description, due_date, reminder)
            if due_date:
                await interaction.response.send_message(f"Task added successfully. Task ID: {task_id}. Due Date: {due_date.strftime('%Y-%m-%d %H:%M %Z')}")
            else:
                await interaction.response.send_message(f"Task added successfully. Task ID: {task_id}.")
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            await interaction.response.send_message("An error occurred while adding the task.", ephemeral=True)

    @app_commands.command(name="task_complete", description="Mark a task as complete")
    async def complete_task(self, interaction: discord.Interaction, task_id: int):
        try:
            success = await self.bot.db.complete_task(interaction.user.id, task_id)
            if success:
                await interaction.response.send_message(f"Task {task_id} marked as complete.")
            else:
                await interaction.response.send_message(f"Task {task_id} not found or already completed.")
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            await interaction.response.send_message("An error occurred while completing the task.", ephemeral=True)

    @app_commands.command(name="task_list", description="List your current tasks")
    async def list_tasks(self, interaction: discord.Interaction):
        try:
            tasks = await self.bot.db.get_user_tasks(interaction.user.id)
            if tasks:
                embed = discord.Embed(title=f"{interaction.user.display_name}'s Tasks", color=discord.Color.blue())
                user_timezone = self.get_user_timezone(interaction.user.id)
                for task in tasks:
                    status = "Completed" if task[3] else "In Progress"
                    due_date_str = task[4].astimezone(user_timezone).strftime('%Y-%m-%d %H:%M %Z') if task[4] else "Not set"
                    embed.add_field(name=f"Task {task[0]}", value=f"{task[2]} - {status} - Due: {due_date_str}", inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("You have no tasks.")
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            await interaction.response.send_message("An error occurred while listing your tasks.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskList(bot))
    logger.info("Loaded TaskList cog")