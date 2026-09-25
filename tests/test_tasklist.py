import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cogs.tasklist import TaskList


class TestTaskListCog(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_db = AsyncMock()
        self.mock_bot.db = self.mock_db
        self.cog = TaskList(self.mock_bot)

    def test_add_task_command(self):
        async def run_test():
            self.mock_db.add_task.return_value = 42
            interaction = AsyncMock()
            interaction.user.id = 12345

            await self.cog.add_task.callback(self.cog, interaction, description="Complete math assignment")

            self.mock_db.add_task.assert_called_once_with(12345, "Complete math assignment")
            interaction.response.send_message.assert_called_once_with("Task added successfully. Task ID: 42")

        asyncio.run(run_test())

    def test_complete_task_command(self):
        async def run_test():
            self.mock_db.complete_task.return_value = True
            interaction = AsyncMock()
            interaction.user.id = 12345

            await self.cog.complete_task.callback(self.cog, interaction, task_id=42)

            self.mock_db.complete_task.assert_called_once_with(12345, 42)
            interaction.response.send_message.assert_called_once_with("Task 42 marked as complete.")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
