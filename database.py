import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo.errors

from .models import User, Space, StudySpace, WorkSpace, SocialSpace, UtilitySpace, Pod, CheckinSession, PomodoroSession, Task, GuildSettings

logger = logging.getLogger(__name__)

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
            await self.db['spaces'].create_index("space_id", unique=True)
            logger.info("Created unique index on spaces.space_id")

            # Add other indexes as needed
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    async def close(self) -> None:
        """Closes the database connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    # --- Space Operations ---

    async def save_space(self, space: Space) -> None:
        """Saves a new space to the database."""
        try:
            result = await self.db['spaces'].insert_one(space.__dict__)
            logger.info(f"Space '{space.name}' created with ID {result.inserted_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Space with ID {space.space_id} already exists.")
        except Exception as e:
            logger.error(f"Error saving space: {e}")

    async def update_space_by_id(self, space_id: str, update_data: Dict[str, Any]) -> None:
        """Updates a space by its space_id."""
        try:
            result = await self.db['spaces'].update_one({'space_id': space_id}, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"Space with ID {space_id} updated in the database.")
            else:
                logger.warning(f"Space with ID {space_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating space: {space_id} - {e}")

    async def fetch_space_by_name(self, name: str, guild_id: int) -> Optional[Space]:
        """Fetches a space by its name and guild ID."""
        try:
            space_data = await self.db['spaces'].find_one({'name': name, 'guild_id': guild_id})
            if space_data:
                return self._create_space_object(space_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching space by name '{name}' in guild {guild_id}: {e}")
            return None

    async def fetch_space_by_id(self, space_id: str) -> Optional[Space]:
        """Fetches a space by its space_id."""
        try:
            space_data = await self.db['spaces'].find_one({'space_id': space_id})
            if space_data:
                return self._create_space_object(space_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching space by ID {space_id}: {e}")
            return None

    async def delete_space(self, space_id: str) -> None:
        """Deletes a space by its space_id."""
        try:
            await self.db['spaces'].delete_one({'space_id': space_id})
            logger.info(f"Deleted space with ID: {space_id}")
        except Exception as e:
            logger.error(f"Error deleting space with ID {space_id}: {e}")

    def _create_space_object(self, space_data: Dict[str, Any]) -> Space:
        """Creates the appropriate Space subclass object based on the space type."""
        space_type = space_data.get('type')
        if space_type == 'study':
            return StudySpace(**space_data)
        elif space_type == 'work':
            return WorkSpace(**space_data)
        elif space_type == 'social':
            return SocialSpace(**space_data)
        elif space_type == 'utility':
            return UtilitySpace(**space_data)
        elif space_type == 'pod':
            return Pod(**space_data)
        else:
            raise ValueError(f"Invalid space type: {space_type}")

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

    # --- Pomodoro Session Operations ---

    async def save_pomodoro_session(self, pomodoro_session: PomodoroSession) -> None:
        """Saves a new Pomodoro session to the database."""
        try:
            result = await self.db['pomodoro_sessions'].insert_one(pomodoro_session.__dict__)
            logger.info(f"Pomodoro session created with ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error saving Pomodoro session: {e}")

    async def update_pomodoro_session(self, session_id: ObjectId, update_data: Dict[str, Any]) -> None:
        """Updates a Pomodoro session by its session_id."""
        try:
            result = await self.db['pomodoro_sessions'].update_one({'_id': session_id}, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"Pomodoro session with ID {session_id} updated in the database.")
            else:
                logger.warning(f"Pomodoro session with ID {session_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating Pomodoro session: {session_id} - {e}")

    async def fetch_pomodoro_session(self, session_id: ObjectId) -> Optional[PomodoroSession]:
        """Fetches a Pomodoro session by its session_id."""
        try:
            session_data = await self.db['pomodoro_sessions'].find_one({'_id': session_id})
            if session_data:
                return PomodoroSession(**session_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching Pomodoro session by ID {session_id}: {e}")
            return None

    async def delete_pomodoro_session(self, session_id: ObjectId) -> None:
        """Deletes a Pomodoro session by its session_id."""
        try:
            await self.db['pomodoro_sessions'].delete_one({'_id': session_id})
            logger.info(f"Deleted Pomodoro session with ID: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting Pomodoro session with ID {session_id}: {e}")

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
