import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import ProductivityService

logger = logging.getLogger(__name__)

class ProductivityTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.productivity_service = ProductivityService(bot.db)
        logger.info("ProductivityTracker cog initialized")

    @app_commands.command(name="productivity", description="Display your productivity metrics")
    async def productivity(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        metrics = await self.productivity_service.get_productivity_metrics(user_id)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Productivity Metrics",
            color=discord.Color.green()
        )
        embed.add_field(name="Tasks Completed", value=str(metrics["tasks_completed"]), inline=False)
        embed.add_field(name="Time Spent (hours, mock)", value=str(metrics["time_spent"]), inline=False)
        embed.add_field(name="Efficiency Score (tasks/hour)", value=str(metrics["efficiency_score"]), inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ProductivityTracker(bot))
    logger.info("Loaded ProductivityTracker cog")
