import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
import sys
import os

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.productivity_tracker import ProductivityTracker
from utils import ProductivityService

class MockDBHandler:
    async def get_user_tasks(self, user_id):
        if user_id == 1:
            return [
                {'id': 1, 'user_id': 1, 'description': 'Task 1', 'completed': True},
                {'id': 2, 'user_id': 1, 'description': 'Task 2', 'completed': False},
                {'id': 3, 'user_id': 1, 'description': 'Task 3', 'completed': True},
            ]
        return []

class TestProductivityService(unittest.TestCase):
    def setUp(self):
        self.db_handler = MockDBHandler()
        self.service = ProductivityService(self.db_handler)

    def test_calculate_efficiency(self):
        self.assertEqual(self.service.calculate_efficiency(10, 2), 5.0)
        self.assertEqual(self.service.calculate_efficiency(10, 0), 0.0)

    def test_get_mock_time_spent(self):
        time_spent = self.service.get_mock_time_spent()
        self.assertTrue(1 <= time_spent <= 40)

    def test_get_tasks_completed(self):
        async def run_test():
            tasks = await self.service.get_tasks_completed(1)
            self.assertEqual(tasks, 2)
            tasks_zero = await self.service.get_tasks_completed(2)
            self.assertEqual(tasks_zero, 0)
        asyncio.run(run_test())

class TestProductivityTrackerCog(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.db = MockDBHandler()
        self.cog = ProductivityTracker(self.bot)

    def test_productivity_command(self):
        async def run_test():
            mock_interaction = AsyncMock()
            mock_interaction.user.id = 1
            mock_interaction.user.display_name = "Test User"

            await self.cog.productivity.callback(self.cog, mock_interaction)

            mock_interaction.response.send_message.assert_called_once()
            embed = mock_interaction.response.send_message.call_args[1]['embed']

            self.assertEqual(embed.title, "Test User's Productivity Metrics")
            self.assertEqual(len(embed.fields), 3)
            self.assertEqual(embed.fields[0].name, "Tasks Completed")
            self.assertEqual(embed.fields[0].value, '2')
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
