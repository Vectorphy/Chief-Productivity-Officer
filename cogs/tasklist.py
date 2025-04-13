import discord
from discord import app_commands
from discord.ext import commands
import logging, asyncio
from datetime import datetime, timedelta
import pytz, discord
from typing import Optional
from database import DBHandler

logger = logging.getLogger(__name__)

class TaskList(commands.Cog):
    def __init__(self, bot: commands.Bot, db: DBHandler):
        """Initializes the TaskList cog.

        Args:
            bot (commands.Bot): The Discord bot instance.
            db (DBHandler): The database handler instance.
        """
        self.bot: commands.Bot = bot
        self.db: DBHandler = db
        logger.info("TaskList cog initialized.")


    def get_user_timezone(self, user_id: int) -> Optional[pytz.timezone]:
        """Retrieves the timezone for a given user.

        Defaults to 'UTC' if no specific timezone is found. In a real application,
        this would likely involve a database lookup or user profile setting.

        Args:
            user_id (int): The ID of the user.

        Returns:
            Optional[pytz.timezone]: The user's timezone, or None if an error occurs.
        """
        try:
            # Placeholder: In a real app, you'd fetch this from a user profile or settings
            # For this example, we'll default to 'UTC'.
            # In a real app you would probably have a DB query here
            return pytz.timezone('UTC')
        except Exception as e:
            logger.error(f"Error retrieving timezone for user {user_id}: {e}")
            return None


    @app_commands.command(name="task_add", description="Add a new task to your list.")
    @app_commands.describe(description="Description of the task.", due_date="Due date for the task (YYYY-MM-DD HH:MM).", reminder="Set a reminder for the task? (true/false).")
    async def add_task(self, interaction: discord.Interaction, description: str, due_date: Optional[str] = None, reminder: bool = False):
        """Adds a new task to the user's task list.

        Args:
            interaction (discord.Interaction): The Discord interaction.
            description (str): The description of the task.
            due_date (Optional[str]): The due date of the task in 'YYYY-MM-DD HH:MM' format. Defaults to None.
            reminder (bool): Whether to set a reminder for the task. Defaults to False.
        """
        try:
            await interaction.response.defer()
            user_timezone = self.get_user_timezone(interaction.user.id)

            if user_timezone is None:
                await interaction.followup.send("Could not determine your timezone. Please try again later.", ephemeral=True)
                return

            due_date_aware: Optional[datetime] = None
            if due_date:
                try:
                    due_date_naive = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                    due_date_aware = user_timezone.localize(due_date_naive)  # Localize to user's timezone
                except ValueError:
                    await interaction.followup.send("Invalid date format. Please use YYYY-MM-DD HH:MM.", ephemeral=True)
                    return

            task_id = await self.db.add_task(interaction.user.id, description, due_date_aware, reminder)
            if due_date_aware:
                await interaction.followup.send(f"Task added successfully. Task ID: {task_id}. Due Date: {due_date_aware.strftime('%Y-%m-%d %H:%M %Z')}")
            else:
                await interaction.followup.send(f"Task added successfully. Task ID: {task_id}.")
            logger.info(f"Task added for user {interaction.user.id}: '{description}', due on '{due_date if due_date else 'Not Set'}'")

        except Exception as e:
            logger.error(f"Error adding task for user {interaction.user.id}: {e}")
            await interaction.followup.send("An error occurred while adding the task.", ephemeral=True)


    @app_commands.command(name="task_complete", description="Mark a task as complete.")
    async def complete_task(self, interaction: discord.Interaction, task_id: int):
        """Marks a task as completed for the user.

        Args:
            interaction (discord.Interaction): The Discord interaction.
            task_id (int): The ID of the task to mark as complete.
        """
        try:
            await interaction.response.defer()
            success = await self.db.complete_task(interaction.user.id, task_id)
            if success:
                await interaction.followup.send(f"Task {task_id} marked as complete.")
                logger.info(f"Task {task_id} marked as complete for user {interaction.user.id}.")
            else:
                await interaction.followup.send(f"Task {task_id} not found or already completed.")
                logger.warning(f"Task {task_id} not found or already completed for user {interaction.user.id}.")

        except Exception as e:
            logger.error(f"Error completing task {task_id} for user {interaction.user.id}: {e}")
            await interaction.followup.send("An error occurred while completing the task.", ephemeral=True)


    @app_commands.command(name="task_list", description="List your current tasks.")
    async def list_tasks(self, interaction: discord.Interaction):
        """Lists the current tasks for the user.

        Args:
            interaction (discord.Interaction): The Discord interaction.
        """
        try:
            await interaction.response.defer()
            tasks = await self.db.get_user_tasks(interaction.user.id)
            if tasks:
                embed = discord.Embed(title=f"{interaction.user.display_name}'s Tasks", color=discord.Color.blue())
                user_timezone = self.get_user_timezone(interaction.user.id)
                for task in tasks:  # Assuming task structure: (task_id, user_id, description, completed, due_date, reminder)
                    status = "Completed" if task[3] else "In Progress"
                    due_date_str = task[4].astimezone(user_timezone).strftime('%Y-%m-%d %H:%M %Z') if task[4] and user_timezone else "Not set"
                    embed.add_field(name=f"Task {task[0]}", value=f"{task[2]} - {status} - Due: {due_date_str}", inline=False)
                await interaction.followup.send(embed=embed)
                logger.info(f"Tasks listed for user {interaction.user.id}.")
            else:
                await interaction.followup.send("You have no tasks.")
                logger.info(f"No tasks found for user {interaction.user.id}.")

        except Exception as e:
            logger.error(f"Error listing tasks for user {interaction.user.id}: {e}")
            await interaction.followup.send("An error occurred while listing your tasks.", ephemeral=True)


async def setup(bot: commands.Bot, db: DBHandler):
    """Sets up the TaskList cog for the bot.

    Args:
        bot (commands.Bot): The Discord bot instance.
        db (DBHandler): The database handler instance.
    """
    await bot.add_cog(TaskList(bot, db))
    logger.info("Loaded TaskList cog.")

async def setup(bot):
    await bot.add_cog(TaskList(bot))
    logger.info("Loaded TaskList cog")