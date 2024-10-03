import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo.errors

logger = logging.getLogger(__name__)

from .models import StudyGroup, CheckinSession, Task, UserPermissions, GuildSettings

class DBHandler:
    """Handles asynchronous database interactions with MongoDB using Motor."""

    def __init__(self, mongo_uri: str, db_name: str):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorClient] = None
        self.lock: asyncio.Lock = asyncio.Lock()
        logger.info("Database handler initialized for MongoDB.")

    async def connect(self):
        """Connects to the MongoDB database."""
        try:
            async with self.lock:
                self.client = AsyncIOMotorClient(self.mongo_uri)
                self.db = self.client[self.db_name]
                logger.info(f"Connected to MongoDB database: {self.db_name}")

                # Create indexes (if needed)
                await self.create_indexes()
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")

    async def create_indexes(self):
        """Creates indexes for efficient querying."""
        try:
            await self.db['study_groups'].create_index("group_id", unique=True)
            logger.info("Created unique index on study_groups.group_id")

            # Add other indexes as needed
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    async def close(self) -> None:
        """Closes the database connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    # --- Study Group Operations ---

    async def save_study_group(self, study_group: StudyGroup) -> None:
        """Saves a new study group to the database."""
        try:
            result = await self.db['study_groups'].insert_one(study_group.__dict__)
            logger.info(f"Study group '{study_group.name}' created with ID {result.inserted_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Study group with ID {study_group.group_id} already exists.")
        except Exception as e:
            logger.error(f"Error saving study group: {e}")

    async def update_study_group_by_id(self, group_id: str, update_data: Dict[str, Any]) -> None:
        """Updates a study group by its group_id."""
        try:
            result = await self.db['study_groups'].update_one({'group_id': group_id}, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"StudyGroup with ID {group_id} updated in the database.")
            else:
                logger.warning(f"StudyGroup with ID {group_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating study group: {group_id} - {e}")

    async def fetch_study_group_by_name(self, name: str, guild_id: int) -> Optional[StudyGroup]:
        """Fetches a study group by its name and guild ID."""
        try:
            study_group_data = await self.db['study_groups'].find_one({'name': name, 'guild_id': guild_id})
            if study_group_data:
                return StudyGroup(**study_group_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching study group by name '{name}' in guild {guild_id}: {e}")
            return None

    async def fetch_study_group_by_id(self, group_id: str) -> Optional[StudyGroup]:
        """Fetches a study group by its group_id."""
        try:
            study_group_data = await self.db['study_groups'].find_one({'group_id': group_id})
            if study_group_data:
                return StudyGroup(**study_group_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching study group by ID {group_id}: {e}")
            return None

    async def delete_study_group(self, group_id: str) -> None:
        """Deletes a study group by its group_id."""
        try:
            await self.db['study_groups'].delete_one({'group_id': group_id})
            logger.info(f"Deleted study group with ID: {group_id}")
        except Exception as e:
            logger.error(f"Error deleting study group with ID {group_id}: {e}")

    # --- Check-in Session Operations ---

    async def save_checkin_session(self, checkin_session: CheckinSession) -> None:
        """Saves a new check-in session to the database."""
        try:
            result = await self.db['checkin_sessions'].insert_one(checkin_session.__dict__)
            logger.info(f"Check-in session '{checkin_session.name}' created with ID {result.inserted_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Check-in session with ID {checkin_session.session_id} already exists.")
        except Exception as e:
            logger.error(f"Error saving check-in session: {e}")

    async def update_checkin_session(self, session_id: str, update_data: Dict[str, Any]) -> None:
        """Updates a check-in session by its session_id."""
        try:
            result = await self.db['checkin_sessions'].update_one({'session_id': session_id}, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"Check-in session with ID {session_id} updated in the database.")
            else:
                logger.warning(f"Check-in session with ID {session_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating check-in session: {session_id} - {e}")

    async def fetch_checkin_session(self, session_id: str) -> Optional[CheckinSession]:
        """Fetches a check-in session by its session_id."""
        try:
            session_data = await self.db['checkin_sessions'].find_one({'session_id': session_id})
            if session_data:
                return CheckinSession(**session_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching check-in session by ID {session_id}: {e}")
            return None

    async def delete_checkin_session(self, session_id: str) -> None:
        """Deletes a check-in session by its session_id."""
        try:
            await self.db['checkin_sessions'].delete_one({'session_id': session_id})
            logger.info(f"Deleted check-in session with ID: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting check-in session with ID {session_id}: {e}")

    # --- Task Operations ---

    async def add_task(self, task: Task) -> ObjectId:
        """Adds a new task to the database."""
        try:
            result = await self.db['tasks'].insert_one(task.__dict__)
            logger.info(f"Added task for user {task.user_id}: ID={result.inserted_id}, description='{task.description}'")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            raise  # Re-raise the exception to be handled by the calling function

    async def complete_task(self, user_id: int, task_id: ObjectId) -> bool:
        """Marks a task as complete."""
        try:
            result = await self.db['tasks'].update_one({'_id': task_id, 'user_id': user_id}, {'$set': {'completed': True}})
            success = result.modified_count > 0
            logger.info(f"{'Completed' if success else 'Failed to complete'} task {task_id} for user {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error completing task {task_id} for user {user_id}: {e}")
            return False

    async def get_user_tasks(self, user_id: int) -> List[Task]:
        """Retrieves all tasks for a user."""
        try:
            tasks_data = await self.db['tasks'].find({'user_id': user_id}).to_list(length=None)
            tasks = [Task(**task_data) for task_data in tasks_data]
            logger.debug(f"Retrieved {len(tasks)} tasks for user {user_id}")
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks for user {user_id}: {e}")
            return []

    # --- User Permissions Operations ---

    async def add_user_permissions(self, user_permissions: UserPermissions) -> None:
        """Adds user permissions to the database."""
        try:
            await self.db['user_permissions'].insert_one(user_permissions.__dict__)
            logger.info(f"Added permissions for user {user_permissions.user_id} in guild {user_permissions.guild_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Permissions for user {user_permissions.user_id} in guild {user_permissions.guild_id} already exist.")
        except Exception as e:
            logger.error(f"Error adding user permissions: {e}")

    async def update_user_permissions(self, user_id: int, guild_id: int, permissions: List[str]) -> None:
        """Updates user permissions in the database."""
        try:
            result = await self.db['user_permissions'].update_one(
                {'user_id': user_id, 'guild_id': guild_id},
                {'$set': {'permissions': permissions}}
            )
            if result.modified_count > 0:
                logger.info(f"Updated permissions for user {user_id} in guild {guild_id}")
            else:
                logger.warning(f"Permissions for user {user_id} in guild {guild_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating user permissions: {e}")

    async def get_user_permissions(self, user_id: int, guild_id: int) -> Optional[List[str]]:
        """Retrieves user permissions from the database."""
        try:
            permissions_data = await self.db['user_permissions'].find_one({'user_id': user_id, 'guild_id': guild_id})
            if permissions_data:
                return permissions_data.get('permissions', [])
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id} in guild {guild_id}: {e}")
            return None

    async def remove_user_permissions(self, user_id: int, guild_id: int) -> None:
        """Removes user permissions from the database."""
        try:
            await self.db['user_permissions'].delete_one({'user_id': user_id, 'guild_id': guild_id})
            logger.info(f"Removed permissions for user {user_id} in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error removing user permissions: {e}")

    # --- Guild Settings Operations ---

    async def save_guild_settings(self, guild_settings: GuildSettings) -> None:
        """Saves guild settings to the database."""
        try:
            await self.db['guild_settings'].insert_one(guild_settings.__dict__)
            logger.info(f"Saved guild settings for guild {guild_settings.guild_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Guild settings for guild {guild_settings.guild_id} already exist.")
        except Exception as e:
            logger.error(f"Error saving guild settings: {e}")

    async def update_guild_settings(self, guild_id: int, update_data: Dict[str, Any]) -> None:
        """Updates guild settings in the database."""
        try:
            result = await self.db['guild_settings'].update_one({'guild_id': guild_id}, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"Updated guild settings for guild {guild_id}")
            else:
                logger.warning(f"Guild settings for guild {guild_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating guild settings: {e}")

    async def get_guild_settings(self, guild_id: int) -> Optional[GuildSettings]:
        """Retrieves guild settings from the database."""
        try:
            settings_data = await self.db['guild_settings'].find_one({'guild_id': guild_id})
            if settings_data:
                return GuildSettings(**settings_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting guild settings for guild {guild_id}: {e}")
            return None

    async def delete_guild_settings(self, guild_id: int) -> None:
        """Deletes guild settings from the database."""
        try:
            await self.db['guild_settings'].delete_one({'guild_id': guild_id})
            logger.info(f"Deleted guild settings for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error deleting guild settings: {e}")
# --
