import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo.errors
from bson import ObjectId

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

    # --- Generic Database Operations ---

    async def _save(self, collection_name: str, data: dict) -> ObjectId:
        """Generic method to save data to a collection."""
        try:
            result = await self.db[collection_name].insert_one(data)
            logger.info(f"Document saved to collection '{collection_name}' with ID {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error saving document to collection '{collection_name}': {e}")
            raise

    async def _update(self, collection_name: str, filter_query: dict, update_data: dict) -> None:
        """Generic method to update data in a collection."""
        try:
            result = await self.db[collection_name].update_one(filter_query, {'$set': update_data})
            if result.modified_count > 0:
                logger.info(f"Document updated in collection '{collection_name}'")
            else:
                logger.warning(f"Document not found or not updated in collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error updating document in collection '{collection_name}': {e}")

    async def _fetch(self, collection_name: str, filter_query: dict) -> Optional[dict]:
        """Generic method to fetch a document from a collection."""
        try:
            document = await self.db[collection_name].find_one(filter_query)
            if document:
                logger.debug(f"Document fetched from collection '{collection_name}'")
                return document
            else:
                logger.debug(f"Document not found in collection '{collection_name}'")
                return None
        except Exception as e:
            logger.error(f"Error fetching document from collection '{collection_name}': {e}")
            return None

    async def _delete(self, collection_name: str, filter_query: dict) -> None:
        """Generic method to delete a document from a collection."""
        try:
            await self.db[collection_name].delete_one(filter_query)
            logger.info(f"Document deleted from collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error deleting document from collection '{collection_name}': {e}")

    # --- Space Operations ---

    async def save_space(self, space: Union[Space, StudySpace, WorkSpace, SocialSpace, UtilitySpace, Pod]) -> None:
        """Saves a new space to the database."""
        await self._save('spaces', space.__dict__)

    async def update_space(self, space_id: str, update_data: Dict[str, Any]) -> None:
        """Updates a space by its space_id."""
        await self._update('spaces', {'space_id': space_id}, update_data)

    async def fetch_space(self, space_id: str) -> Optional[Space]:
        """Fetches a space by its space_id."""
        space_data = await self._fetch('spaces', {'space_id': space_id})
        if space_data:
            return self._create_space_object(space_data)
        else:
            return None

    async def delete_space(self, space_id: str) -> None:
        """Deletes a space by its space_id."""
        await self._delete('spaces', {'space_id': space_id})

    def _create_space_object(self, space_data: Dict[str, Any]) -> Space:
        """Creates the appropriate Space subclass object based on the space type and subtype."""
        space_type = space_data.get('type')
        space_subtype = space_data.get('subtype')

        if space_type == 'study':
            if space_subtype == 'pod':
                return Pod(**space_data)
            else:
                return StudySpace(**space_data)
        elif space_type == 'work':
            return WorkSpace(**space_data)
        elif space_type == 'social':
            return SocialSpace(**space_data)
        elif space_type == 'utility':
            return UtilitySpace(**space_data)
        else:
            raise ValueError(f"Invalid space type: {space_type}")

    # --- Check-in Session Operations ---

    async def save_checkin_session(self, checkin_session: CheckinSession) -> None:
        """Saves a new check-in session to the database."""
        await self._save('checkin_sessions', checkin_session.__dict__)

    async def update_checkin_session(self, session_id: str, update_data: Dict[str, Any]) -> None:
        """Updates a check-in session by its session_id."""
        await self._update('checkin_sessions', {'session_id': session_id}, update_data)

    async def fetch_checkin_session(self, session_id: str) -> Optional[CheckinSession]:
        """Fetches a check-in session by its session_id."""
        session_data = await self._fetch('checkin_sessions', {'session_id': session_id})
        if session_data:
            return CheckinSession(**session_data)
        else:
            return None

    async def delete_checkin_session(self, session_id: str) -> None:
        """Deletes a check-in session by its session_id."""
        await self._delete('checkin_sessions', {'session_id': session_id})

    # --- User Operations ---

    async def save_user(self, user: User) -> None:
        """Saves a new user to the database."""
        await self._save('users', user.__dict__)

    async def update_user(self, user_id: int, guild_id: int, update_data: Dict[str, Any]) -> None:
        """Updates a user in the database."""
        await self._update('users', {'user_id': user_id, 'guild_id': guild_id}, update_data)

    async def fetch_user(self, user_id: int, guild_id: int) -> Optional[User]:
        """Retrieves a user from the database."""
        user_data = await self._fetch('users', {'user_id': user_id, 'guild_id': guild_id})
        if user_data:
            return User(**user_data)
        else:
            return None

    async def delete_user(self, user_id: int, guild_id: int) -> None:
        """Deletes a user from the database."""
        await self._delete('users', {'user_id': user_id, 'guild_id': guild_id})

    # --- Pomodoro Session Operations ---

    async def save_pomodoro_session(self, pomodoro_session: PomodoroSession) -> None:
        """Saves a new Pomodoro session to the database."""
        await self._save('pomodoro_sessions', pomodoro_session.__dict__)

    async def update_pomodoro_session(self, session_id: ObjectId, update_data: Dict[str, Any]) -> None:
        """Updates a Pomodoro session by its session_id."""
        await self._update('pomodoro_sessions', {'_id': session_id}, update_data)

    async def fetch_pomodoro_session(self, session_id: ObjectId) -> Optional[PomodoroSession]:
        """Fetches a Pomodoro session by its session_id."""
        session_data = await self._fetch('pomodoro_sessions', {'_id': session_id})
        if session_data:
            return PomodoroSession(**session_data)
        else:
            return None

    async def delete_pomodoro_session(self, session_id: ObjectId) -> None:
        """Deletes a Pomodoro session by its session_id."""
        await self._delete('pomodoro_sessions', {'_id': session_id})

    # --- Task Operations ---

    async def save_task(self, task: Task) -> ObjectId:
        """Saves a new task to the database."""
        return await self._save('tasks', task.__dict__)

    async def update_task(self, task_id: ObjectId, update_data: Dict[str, Any]) -> None:
        """Updates a task by its task_id."""
        await self._update('tasks', {'_id': task_id}, update_data)

    async def fetch_task(self, task_id: ObjectId) -> Optional[Task]:
        """Fetches a task by its task_id."""
        task_data = await self._fetch('tasks', {'_id': task_id})
        if task_data:
            return Task(**task_data)
        else:
            return None

    async def delete_task(self, task_id: ObjectId) -> None:
        """Deletes a task by its task_id."""
        await self._delete('tasks', {'_id': task_id})

    # --- User Permissions Operations ---

    async def save_user_permissions(self, user_permissions: UserPermissions) -> None:
        """Saves new user permissions to the database."""
        await self._save('user_permissions', user_permissions.__dict__)

    async def update_user_permissions(self, user_id: int, guild_id: int, update_data: Dict[str, Any]) -> None:
        """Updates user permissions in the database."""
        await self._update('user_permissions', {'user_id': user_id, 'guild_id': guild_id}, update_data)

    async def fetch_user_permissions(self, user_id: int, guild_id: int) -> Optional[UserPermissions]:
        """Retrieves user permissions from the database."""
        permissions_data = await self._fetch('user_permissions', {'user_id': user_id, 'guild_id': guild_id})
        if permissions_data:
            return UserPermissions(**permissions_data)
        else:
            return None

    async def delete_user_permissions(self, user_id: int, guild_id: int) -> None:
        """Deletes user permissions from the database."""
        await self._delete('user_permissions', {'user_id': user_id, 'guild_id': guild_id})

        # --- Role Permissions Operations ---

    async def add_role_permissions(self, role_permissions: UserPermissions) -> None:
        """Adds role permissions to the database."""
        try:
            await self.db['user_permissions'].insert_one(role_permissions.__dict__)
            logger.info(f"Added permissions for role {role_permissions.role_id} in guild {role_permissions.guild_id}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Permissions for role {role_permissions.role_id} in guild {role_permissions.guild_id} already exist.")
        except Exception as e:
            logger.error(f"Error adding role permissions: {e}")

    async def update_role_permissions(self, role_id: int, guild_id: int, permissions: List[str]) -> None:
        """Updates role permissions in the database."""
        try:
            result = await self.db['user_permissions'].update_one(
                {'role_id': role_id, 'guild_id': guild_id},
                {'$set': {'permissions': permissions}}
            )
            if result.modified_count > 0:
                logger.info(f"Updated permissions for role {role_id} in guild {guild_id}")
            else:
                logger.warning(f"Permissions for role {role_id} in guild {guild_id} not found or not updated.")
        except Exception as e:
            logger.error(f"Error updating role permissions: {e}")

    async def fetch_role_permissions(self, role_id: int, guild_id: int) -> Optional[UserPermissions]:
        """Retrieves role permissions from the database."""
        try:
            permissions_data = await self.db['user_permissions'].find_one({'role_id': role_id, 'guild_id': guild_id})
            if permissions_data:
                return UserPermissions(**permissions_data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting permissions for role {role_id} in guild {guild_id}: {e}")
            return None

    async def delete_role_permissions(self, role_id: int, guild_id: int) -> None:
        """Deletes role permissions from the database."""
        try:
            await self.db['user_permissions'].delete_one({'role_id': role_id, 'guild_id': guild_id})
            logger.info(f"Removed permissions for role {role_id} in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error removing role permissions: {e}")

    # --- Guild Settings Operations ---

    async def save_guild_settings(self, guild_settings: GuildSettings) -> None:
        """Saves guild settings to the database."""
        await self._save('guild_settings', guild_settings.__dict__)

    async def update_guild_settings(self, guild_id: int, update_data: Dict[str, Any]) -> None:
        """Updates guild settings in the database."""
        await self._update('guild_settings', {'guild_id': guild_id}, update_data)

    async def fetch_guild_settings(self, guild_id: int) -> Optional[GuildSettings]:
        """Retrieves guild settings from the database."""
        settings_data = await self._fetch('guild_settings', {'guild_id': guild_id})
        if settings_data:
            return GuildSettings(**settings_data)
        else:
            return None

    async def delete_guild_settings(self, guild_id: int) -> None:
        """Deletes guild settings from the database."""
        await self._delete('guild_settings', {'guild_id': guild_id})
