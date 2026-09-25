import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DBHandler


class TestDBHandler(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing
        self.db = DBHandler(db_name=":memory:")

    def tearDown(self):
        async def cleanup():
            await self.db.close()
        asyncio.run(cleanup())

    def test_database_initialization_and_tasks(self):
        async def run_test():
            await self.db.connect()

            # Test adding task
            task_id = await self.db.add_task(user_id=123, description="Write documentation")
            self.assertIsNotNone(task_id)

            # Test getting tasks
            tasks = await self.db.get_user_tasks(user_id=123)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]['description'], "Write documentation")
            self.assertEqual(tasks[0]['completed'], 0)

            # Test completing task
            success = await self.db.complete_task(user_id=123, task_id=task_id)
            self.assertTrue(success)

            # Verify completed state
            tasks = await self.db.get_user_tasks(user_id=123)
            self.assertEqual(tasks[0]['completed'], 1)

        asyncio.run(run_test())

    def test_manager_permissions(self):
        async def run_test():
            await self.db.connect()

            # Add manager
            await self.db.add_manager(user_id=999, guild_id=100, permission_level=3)
            manager = await self.db.get_manager(user_id=999, guild_id=100)
            self.assertIsNotNone(manager)
            self.assertEqual(manager['permission_level'], 3)

            # Remove manager
            await self.db.remove_manager(user_id=999, guild_id=100)
            manager_after = await self.db.get_manager(user_id=999, guild_id=100)
            self.assertIsNone(manager_after)

        asyncio.run(run_test())

    def test_study_group_transfer_and_channel_lookup(self):
        async def run_test():
            await self.db.connect()

            # Save study group
            group_data = {
                "group_id": "sg-transfer-test",
                "guild_id": 885134,
                "name": "Physics Cohort",
                "creator_id": 111,
                "owner_id": 111,
                "category_id": 222,
                "group_role_id": 333,
                "vc_id": 444,
                "text_id": 555,
                "start_time": 1000.0,
                "duration": 3600,
                "end_time": 4600.0,
                "max_members": 5,
                "active": 1,
            }
            await self.db.save_study_group(group_data)

            # Lookup by channel
            by_channel = await self.db.get_study_group_by_channel(555)
            self.assertIsNotNone(by_channel)
            assert by_channel is not None
            self.assertEqual(by_channel["name"], "Physics Cohort")
            self.assertEqual(by_channel["owner_id"], 111)

            # Transfer ownership
            await self.db.transfer_ownership_study_group_db("sg-transfer-test", 999)
            transferred = await self.db.fetch_study_group_by_id("sg-transfer-test")
            self.assertIsNotNone(transferred)
            assert transferred is not None
            self.assertEqual(transferred["owner_id"], 999)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
