import sqlite3
from sqlite3 import Error
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base class for database-related errors."""
    pass

class DuplicateEntryError(DatabaseError):
    """Raised when attempting to insert a duplicate entry."""
    pass

class NotFoundError(DatabaseError):
    """Raised when a requested entry is not found."""
    pass

class ForeignKeyError(DatabaseError):
    """Raised when a foreign key constraint is violated."""
    pass

class DBHandler:
    def __init__(self, db_file):
        """Initializes the database handler."""
        self.db_file = db_file
        self.conn = self.create_connection()

    def create_connection(self):
        """Creates a database connection."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            logger.info(f"Connected to database: {self.db_file}")
        except Error as e:
            logger.error(f"Error connecting to database: {e}")
        return conn

    def close_connection(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info(f"Closed connection to database: {self.db_file}")

    def execute_query(self, query, params=None):
        """Executes a SQL query."""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            logger.debug(f"Executed query: {query}, with params: {params}")
            return cursor
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            logger.error(f"Integrity error: {e}")
            if 'UNIQUE constraint' in str(e):
                raise DuplicateEntryError("Duplicate entry found in the database.") from e
            elif 'FOREIGN KEY constraint' in str(e):
                raise ForeignKeyError("Foreign key constraint violated.") from e
            else:
                raise DatabaseError(f"A database integrity error occurred: {e}") from e
        except sqlite3.OperationalError as e:
            self.conn.rollback()
            logger.error(f"Operational error: {e}")
            raise DatabaseError(f"An operational error occurred in the database: {e}") from e
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"A database error occurred: {e}") from e

    def fetch_one(self, query, params=None):
        """Fetches one row from the query."""
        cursor = self.execute_query(query, params)
        result = cursor.fetchone()
        if not result:
            logger.debug(f"No results found for query: {query}")
            raise NotFoundError("No entry found in the database.")
        return result

    def fetch_all(self, query, params=None):
        """Fetches all rows from the query."""
        cursor = self.execute_query(query, params)
        return cursor.fetchall()

    def add_task(self, guild_id, description, owner_id=None):
        """Adds a task to the database."""
        query = "INSERT INTO tasks (guild_id, description, owner_id) VALUES (?, ?, ?)"
        self.execute_query(query, (guild_id, description, owner_id))
        logger.info(f"Task added with description: {description} by owner: {owner_id} in guild: {guild_id}")

    def get_task(self, task_id, guild_id):
        """Retrieves a task by its ID and guild ID."""
        query = "SELECT * FROM tasks WHERE task_id = ? AND guild_id = ?"
        try:
            task = self.fetch_one(query, (task_id, guild_id))
            logger.info(f"Retrieved task with ID: {task_id} in guild: {guild_id}")
            return task
        except NotFoundError as e:
            logger.warning(f"Task with ID: {task_id} not found in guild: {guild_id}. {e}")
            raise

    def list_tasks(self, guild_id, owner_id=None):
        """Lists all tasks in a guild, optionally for a specific owner."""
        if owner_id:
            query = "SELECT * FROM tasks WHERE guild_id = ? AND owner_id = ?"
            tasks = self.fetch_all(query, (guild_id, owner_id))
        else:
            query = "SELECT * FROM tasks WHERE guild_id = ?"
            tasks = self.fetch_all(query, (guild_id,))
        logger.info(f"Listed tasks in guild: {guild_id}")
        return tasks

    def complete_task(self, task_id, guild_id):
        """Marks a task as completed."""
        query = "UPDATE tasks SET completed = 1 WHERE task_id = ? AND guild_id = ?"
        self.execute_query(query, (task_id, guild_id))
        logger.info(f"Task with ID: {task_id} completed in guild: {guild_id}")

    def delete_task(self, task_id, guild_id):
        """Deletes a task from the database."""
        query = "DELETE FROM tasks WHERE task_id = ? AND guild_id = ?"
        self.execute_query(query, (task_id, guild_id))
        logger.info(f"Task with ID: {task_id} deleted in guild: {guild_id}")

    def add_developer(self, user_id, guild_id):
        """Adds a user as a developer."""
        query = "INSERT INTO developers (user_id, guild_id) VALUES (?, ?)"
        self.execute_query(query, (user_id, guild_id))
        logger.info(f"User with ID: {user_id} added as developer in guild: {guild_id}")

    def get_developer(self, user_id, guild_id):
        """Retrieves a developer by their ID and guild ID."""
        query = "SELECT * FROM developers WHERE user_id = ? AND guild_id = ?"
        try:
            developer = self.fetch_one(query, (user_id, guild_id))
            logger.info(f"Retrieved developer with ID: {user_id} in guild: {guild_id}")
            return developer
        except NotFoundError as e:
            logger.warning(f"Developer with ID: {user_id} not found in guild: {guild_id}. {e}")
            raise

    def list_developers(self, guild_id):
        """Lists all developers in a guild."""
        query = "SELECT * FROM developers WHERE guild_id = ?"
        developers = self.fetch_all(query, (guild_id,))
        logger.info(f"Listed developers in guild: {guild_id}")
        return developers

    def remove_developer(self, user_id, guild_id):
        """Removes a user from being a developer."""
        query = "DELETE FROM developers WHERE user_id = ? AND guild_id = ?"
        self.execute_query(query, (user_id, guild_id))
        logger.info(f"Developer with ID: {user_id} removed in guild: {guild_id}")

    def add_manager(self, user_id, guild_id):
        """Adds a user as a manager."""
        query = "INSERT INTO managers (user_id, guild_id) VALUES (?, ?)"
        self.execute_query(query, (user_id, guild_id))
        logger.info(f"User with ID: {user_id} added as manager in guild: {guild_id}")

    def get_manager(self, user_id, guild_id):
        """Retrieves a manager by their ID and guild ID."""
        query = "SELECT * FROM managers WHERE user_id = ? AND guild_id = ?"
        try:
            manager = self.fetch_one(query, (user_id, guild_id))
            logger.info(f"Retrieved manager with ID: {user_id} in guild: {guild_id}")
            return manager
        except NotFoundError as e:
            logger.warning(f"Manager with ID: {user_id} not found in guild: {guild_id}. {e}")
            raise

    def list_managers(self, guild_id):
        """Lists all managers in a guild."""
        query = "SELECT * FROM managers WHERE guild_id = ?"
        managers = self.fetch_all(query, (guild_id,))
        logger.info(f"Listed managers in guild: {guild_id}")
        return managers

    def remove_manager(self, user_id, guild_id):
        """Removes a user from being a manager."""
        query = "DELETE FROM managers WHERE user_id = ? AND guild_id = ?"
        self.execute_query(query, (user_id, guild_id))
        logger.info(f"Manager with ID: {user_id} removed in guild: {guild_id}")

    def set_permission_level(self, user_id, guild_id, level):
        """Sets the permission level of a user."""
        query = "INSERT INTO permissions (user_id, guild_id, level) VALUES (?, ?, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET level = excluded.level"
        self.execute_query(query, (user_id, guild_id, level))
        logger.info(f"Set permission level {level} for user with ID: {user_id} in guild: {guild_id}")

    def get_permission_level(self, user_id, guild_id):
        """Gets the permission level of a user."""
        query = "SELECT level FROM permissions WHERE user_id = ? AND guild_id = ?"
        try:
            permission = self.fetch_one(query, (user_id, guild_id))
            logger.info(f"Retrieved permission level for user with ID: {user_id} in guild: {guild_id}")
            return permission[0]
        except NotFoundError as e:
            logger.warning(f"No permission found for user with ID: {user_id} in guild: {guild_id}. {e}")
            raise

    def create_pomodoro_session(self, guild_id, channel_id, start_time, end_time=None, cycle=None, current_stage=None):
        """Creates a new Pomodoro session."""
        query = "INSERT INTO pomodoro_sessions (guild_id, channel_id, start_time, end_time, cycle, current_stage) VALUES (?, ?, ?, ?, ?, ?)"
        self.execute_query(query, (guild_id, channel_id, start_time, end_time, cycle, current_stage))
        logger.info(f"Pomodoro session created in channel: {channel_id} in guild: {guild_id}")

    def get_pomodoro_session(self, guild_id, channel_id):
        """Retrieves a Pomodoro session by guild ID and channel ID."""
        query = "SELECT * FROM pomodoro_sessions WHERE guild_id = ? AND channel_id = ?"
        try:
            session = self.fetch_one(query, (guild_id, channel_id))
            logger.info(f"Retrieved Pomodoro session in channel: {channel_id} in guild: {guild_id}")
            return session
        except NotFoundError as e:
            logger.warning(f"Pomodoro session in channel: {channel_id} not found in guild: {guild_id}. {e}")
            raise

    def update_pomodoro_session(self, guild_id, channel_id, end_time=None, cycle=None, current_stage=None):
        """Updates a Pomodoro session."""
        updates = []
        params = []

        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time)
        if cycle is not None:
            updates.append("cycle = ?")
            params.append(cycle)
        if current_stage is not None:
            updates.append("current_stage = ?")
            params.append(current_stage)

        if not updates:
            logger.warning(f"No updates provided for Pomodoro session in channel: {channel_id} in guild: {guild_id}")
            return

        query = "UPDATE pomodoro_sessions SET " + ", ".join(updates) + " WHERE guild_id = ? AND channel_id = ?"
        params.extend([guild_id, channel_id])
        self.execute_query(query, params)
        logger.info(f"Pomodoro session updated in channel: {channel_id} in guild: {guild_id}")

    def delete_pomodoro_session(self, guild_id, channel_id):
        """Deletes a Pomodoro session."""
        query = "DELETE FROM pomodoro_sessions WHERE guild_id = ? AND channel_id = ?"
        self.execute_query(query, (guild_id, channel_id))
        logger.info(f"Pomodoro session deleted in channel: {channel_id} in guild: {guild_id}")

    def create_study_group(self, guild_id, name, category_id, owner_id, max_members=None, is_permanent=0, text_channel_id=None, voice_channel_id=None):
        """Creates a new study group."""
        query = "INSERT INTO study_groups (guild_id, name, category_id, owner_id, max_members, is_permanent, text_channel_id, voice_channel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        self.execute_query(query, (guild_id, name, category_id, owner_id, max_members, is_permanent, text_channel_id, voice_channel_id))
        logger.info(f"Study group '{name}' created in guild: {guild_id}")

    def get_study_group(self, guild_id, group_id=None, name=None):
        """Retrieves a study group by its ID or name."""
        if group_id:
            query = "SELECT * FROM study_groups WHERE group_id = ? AND guild_id = ?"
            try:
                group = self.fetch_one(query, (group_id, guild_id))
                logger.info(f"Retrieved study group with ID: {group_id} in guild: {guild_id}")
                return group
            except NotFoundError as e:
                logger.warning(f"Study group with ID: {group_id} not found in guild: {guild_id}. {e}")
                raise
        elif name:
            query = "SELECT * FROM study_groups WHERE name = ? AND guild_id = ?"
            try:
                group = self.fetch_one(query, (name, guild_id))
                logger.info(f"Retrieved study group named: {name} in guild: {guild_id}")
                return group
            except NotFoundError as e:
                logger.warning(f"Study group named: {name} not found in guild: {guild_id}. {e}")
                raise
        else:
            raise ValueError("Either group_id or name must be provided")

    def update_study_group(self, group_id, guild_id, name=None, category_id=None, owner_id=None, max_members=None, is_permanent=None, text_channel_id=None, voice_channel_id=None):
        """Updates a study group."""
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
        if owner_id is not None:
            updates.append("owner_id = ?")
            params.append(owner_id)
        if max_members is not None:
            updates.append("max_members = ?")
            params.append(max_members)
        if is_permanent is not None:
            updates.append("is_permanent = ?")
            params.append(is_permanent)
        if text_channel_id is not None:
            updates.append("text_channel_id = ?")
            params.append(text_channel_id)
        if voice_channel_id is not None:
            updates.append("voice_channel_id = ?")
            params.append(voice_channel_id)

        if not updates:
            logger.warning(f"No updates provided for study group with ID: {group_id} in guild: {guild_id}")
            return

        query = "UPDATE study_groups SET " + ", ".join(updates) + " WHERE group_id = ? AND guild_id = ?"
        params.extend([group_id, guild_id])
        self.execute_query(query, params)
        logger.info(f"Study group with ID: {group_id} updated in guild: {guild_id}")

    def delete_study_group(self, group_id, guild_id):
        """Deletes a study group."""
        query = "DELETE FROM study_groups WHERE group_id = ? AND guild_id = ?"
        self.execute_query(query, (group_id, guild_id))
        logger.info(f"Study group with ID: {group_id} deleted in guild: {guild_id}")

    def add_group_member(self, member_id, group_id, is_muted=0, is_deafened=0):
        """Adds a member to a study group."""
        query = "INSERT INTO group_members (member_id, group_id, is_muted, is_deafened) VALUES (?, ?, ?, ?)"
        self.execute_query(query, (member_id, group_id, is_muted, is_deafened))
        logger.info(f"Member with ID: {member_id} added to group: {group_id}")

    def get_group_members(self, group_id):
        """Retrieves all members of a study group."""
        query = "SELECT * FROM group_members WHERE group_id = ?"
        members = self.fetch_all(query, (group_id,))
        logger.info(f"Retrieved members for group: {group_id}")
        return members

    def update_group_member(self, member_id, group_id, is_muted=None, is_deafened=None):
        """Updates a group member."""
        updates = []
        params = []

        if is_muted is not None:
            updates.append("is_muted = ?")
            params.append(is_muted)
        if is_deafened is not None:
            updates.append("is_deafened = ?")
            params.append(is_deafened)

        if not updates:
            logger.warning(f"No updates provided for member with ID: {member_id} in group: {group_id}")
            return

        query = "UPDATE group_members SET " + ", ".join(updates) + " WHERE member_id = ? AND group_id = ?"
        params.extend([member_id, group_id])
        self.execute_query(query, params)
        logger.info(f"Member with ID: {member_id} updated in group: {group_id}")

    def remove_group_member(self, member_id, group_id):
        """Removes a member from a study group."""
        query = "DELETE FROM group_members WHERE member_id = ? AND group_id = ?"
        self.execute_query(query, (member_id, group_id))
        logger.info(f"Member with ID: {member_id} removed from group: {group_id}")

    def get_study_group_count(self, guild_id, is_permanent=None):
        """Gets the total amount of study groups, or the total amount of permanent groups, depending on the is_permanent value."""
        if is_permanent is not None:
            query = "SELECT COUNT(*) FROM study_groups WHERE guild_id = ? AND is_permanent = ?"
            count = self.fetch_one(query, (guild_id, is_permanent))
            logger.info(f"Retrieved the amount of {'permanent' if is_permanent else 'temporary'} study groups in guild: {guild_id}")
            return count[0]
        else:
            query = "SELECT COUNT(*) FROM study_groups WHERE guild_id = ?"
            count = self.fetch_one(query, (guild_id,))
            logger.info(f"Retrieved the total amount of study groups in guild: {guild_id}")
            return count[0]

    def get_all_study_groups(self, guild_id):
        """Retrieves all study groups in a guild."""
        query = "SELECT * FROM study_groups WHERE guild_id = ?"
        groups = self.fetch_all(query, (guild_id,))
        logger.info(f"Retrieved all study groups in guild: {guild_id}")
        return groups
