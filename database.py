import sqlite3
from datetime import datetime
import logging
from typing import List, Any, Dict, Optional

logger = logging.getLogger(__name__)

class DBHandler:
    def __init__(self, db_path: str):
        """Initializes the DBHandler with the path to the SQLite database file."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        logger.info("Database handler initialized for SQLite.")

    async def connect(self) -> None:
        """Connects to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # To access columns by name
            logger.info(f"Connected to SQLite database: {self.db_path}")
            cursor = self.conn.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                group_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                creator_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                max_members INTEGER NOT NULL,
                group_role_id INTEGER DEFAULT 0,
                vc_id INTEGER DEFAULT 0,
                text_id INTEGER DEFAULT 0,
                info_embed_id INTEGER DEFAULT 0,
                video_timer INTEGER DEFAULT 10,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration INTEGER NOT NULL,
                active BOOLEAN DEFAULT 0,
                is_permanent BOOLEAN DEFAULT 0
            )
            ''')
            logger.info("Created 'study_groups' table.")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_groups_members (
                    group_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES study_groups (group_id),
                    PRIMARY KEY (group_id, user_id)
                )
            ''')
            logger.info("Created 'study_groups_members' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY,
                group_id TEXT,
                current_stage TEXT CHECK(current_stage IN ('focus', 'short_break', 'long_break')) DEFAULT 'focus',
                FOREIGN KEY (group_id) REFERENCES study_groups (group_id)
            )
            ''')
            logger.info("Created 'pomodoro_sessions' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                user_id INTEGER NOT NULL,
                guild_id INTEGER,
                permission_level INTEGER NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
            ''')

            logger.info("Created 'managers' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_channel_logs (
                id INTEGER PRIMARY KEY,
                group_id INTEGER,
                channel_id INTEGER,
                creator_id INTEGER,
                create_time REAL,
                FOREIGN KEY (group_id) REFERENCES study_groups (id) ON DELETE CASCADE
            )
            ''')
            logger.info("Created 'voice_channel_logs' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                vc_cleanup_time INTEGER,
                vc_category_id INTEGER,
                logging_channel_id INTEGER
            )
            ''')
            logger.info("Created 'guild_settings' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                group_id TEXT NOT NULL,
                description TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                due_date REAL,
                reminders_sent TEXT
            )
            ''')
            logger.info("Created 'tasks' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                guild_id INTEGER,
                name TEXT NOT NULL,
                creator_id INTEGER,
                owner_id INTEGER NOT NULL,
                text_id INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                start_time REAL NOT NULL,
                last_reminder_time REAL NOT NULL,
                next_reminder_time REAL NOT NULL,
                reminder_count INTEGER NOT NULL,
                last_reminder_message_id INTEGER NOT NULL DEFAULT 0,
                active BOOLEAN DEFAULT 1
            )
            ''')
            logger.info("Created 'checkin_sessions' table.")

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkin_members (
                session_id TEXT NOT NULL,
                member_id INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES checkin_sessions (session_id) ON DELETE CASCADE,
                PRIMARY KEY (session_id, member_id)
            )
            ''')
            logger.info("Created 'checkin_members' table.")

            # Create indexes
            logger.info("Database tables created.")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def __del__(self):
        """Closes the database connection when the object is deleted."""
        self.close()

    def close(self) -> None:
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

            # Add indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_study_groups_group_id ON study_groups (group_id)
            ''')
            logger.info("Created index on study_groups (group_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_study_groups_guild_id ON study_groups (guild_id)
            ''')
            logger.info("Created index on study_groups (guild_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_study_groups_members_group_id ON study_groups_members (group_id)
            ''')
            logger.info("Created index on study_groups_members (group_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_study_groups_members_user_id ON study_groups_members (user_id)
            ''')
            logger.info("Created index on study_groups_members (user_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_group_id ON pomodoro_sessions (group_id)
            ''')
            logger.info("Created index on pomodoro_sessions (group_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_voice_channel_logs_group_id ON voice_channel_logs (group_id)
            ''')
            logger.info("Created index on voice_channel_logs (group_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_voice_channel_logs_channel_id ON voice_channel_logs (channel_id)
            ''')
            logger.info("Created index on voice_channel_logs (channel_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id ON guild_settings (guild_id)
            ''')
            logger.info("Created index on guild_settings (guild_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id)
            ''')
            logger.info("Created index on tasks (user_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_checkin_sessions_session_id ON checkin_sessions (session_id)
            ''')
            logger.info("Created index on checkin_sessions (session_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_checkin_sessions_guild_id ON checkin_sessions (guild_id)
            ''')
            logger.info("Created index on checkin_sessions (guild_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_checkin_members_session_id ON checkin_members (session_id)
            ''')
            logger.info("Created index on checkin_members (session_id)")

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_managers_user_id ON managers (user_id)
            ''')
            logger.info("Created index on managers (user_id)")

    ### --- STUDY GROUP DB OPERATIONS --- ###

    async def save_study_group(self, study_group_data: Dict[str, Any]) -> int:
        """Saves a study group to the database.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO study_groups (
                    guild_id, group_id, name, creator_id, owner_id, category_id, max_members, group_role_id, vc_id, text_id, info_embed_id, video_timer, start_time, end_time, duration, active, is_permanent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                study_group_data["guild_id"],
                study_group_data["group_id"],
                study_group_data["name"],                
                study_group_data["creator_id"],
                study_group_data["owner_id"],
                study_group_data["category_id"],
                study_group_data["max_members"],
                study_group_data["group_role_id"],
                study_group_data["vc_id"],
                study_group_data["text_id"],
                study_group_data["info_embed_id"],
                study_group_data["start_time"],
                study_group_data["end_time"],
                study_group_data["duration"],
                study_group_data["active"],
                study_group_data["is_permanent"]
            ))
            study_group_id = cursor.lastrowid
            logger.info(f"Study group '{study_group_data['name']}' created with ID {study_group_data['group_id']}")            
            return study_group_id
        except sqlite3.Error as e:
            logger.error(f"Error saving study group '{study_group_data['name']}': {e}")
            raise

    async def update_member_study_group(self, group_id: str, user_id: int) -> None:
        """Updates a member's status in a study group."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO study_groups_members (group_id, user_id)
                VALUES (?, ?)
            ''', (group_id, user_id))            
            logger.info(f"Updated member {user_id} in study group {group_id}")
        except sqlite3.Error as e:
            logger.error(f"Error updating member {user_id} in study group {group_id}: {e}")
            raise

    async def update_study_group(self, study_group_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates a study group in the database.

        Args:
            study_group_data (Dict[str, Any]): Dictionary containing the update data.

        Returns:
            Optional[Dict[str, Any]]: The updated study group data or None if not found.
        """
        try:
            fields_to_update = []
            values = []

            if "name" in study_group_data:
                fields_to_update.append("name = ?")
                values.append(study_group_data["name"])

            if "owner_id" in study_group_data:
                fields_to_update.append("owner_id = ?")
                values.append(study_group_data["owner_id"])

            if "category_id" in study_group_data:
                fields_to_update.append("category_id = ?")
                values.append(study_group_data["category_id"])

            if "max_members" in study_group_data:
                fields_to_update.append("max_members = ?")
                values.append(study_group_data["max_members"])

            if "group_role_id" in study_group_data:
                fields_to_update.append("group_role_id = ?")
                values.append(study_group_data["group_role_id"])

            if "text_id" in study_group_data:
                fields_to_update.append("text_id = ?")
                values.append(study_group_data["text_id"])

            if "info_embed_id" in study_group_data:
                fields_to_update.append("info_embed_id = ?")
                values.append(study_group_data["info_embed_id"])

            if "vc_id" in study_group_data:
                fields_to_update.append("vc_id = ?")
                values.append(study_group_data["vc_id"])

            if "end_time" in study_group_data:
                fields_to_update.append("end_time = ?")
                values.append(study_group_data["end_time"])

            if "speak_enabled" in study_group_data:
                fields_to_update.append("speak_enabled = ?")
                values.append(study_group_data["speak_enabled"])

            if "active" in study_group_data:
                fields_to_update.append("active = ?")
                values.append(study_group_data["active"])

            if "is_permanent" in study_group_data:
                fields_to_update.append("is_permanent = ?")
                values.append(study_group_data["is_permanent"])

            if not fields_to_update:
                logger.warning("No fields to update for the study group.")
                return None

            values.append(study_group_data["group_id"])
            query = f"UPDATE study_groups SET {', '.join(fields_to_update)} WHERE group_id = ?"

            cursor = self.conn.cursor()
            cursor.execute(query, values)

            cursor.execute(
                'SELECT * FROM study_groups WHERE group_id = ?', (study_group_data["group_id"],))
            group = cursor.fetchone()
            if group:
                logger.debug(
                    f"Fetched StudyGroup {study_group_data['group_id']}: Found.")
                return dict(group)
            else:
                logger.debug(
                    f"Fetched StudyGroup {study_group_data['group_id']}: Not found.")
                return None
        except sqlite3.Error as e:
            logger.error(
                f"Error updating study group {study_group_data['group_id']}: {e}")
            raise

    async def fetch_study_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a study group by its group_id.

        Args:
            group_id (str): The ID of the study group to fetch.

        Returns:
            Optional[Dict[str, Any]]: The study group data or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM study_groups WHERE group_id = ?", (group_id,))            
            study_group = cursor.fetchone()
            return dict(study_group) if study_group else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching study group with ID '{group_id}': {e}")
            raise

    def fetch_study_group_by_name(self, name: str, guild_id: int) -> Optional[Dict[str, Any]]:
        """Fetches a study group by its name and guild ID.

        Args:
            name (str): The name of the study group to fetch.
            guild_id (int): The ID of the guild.

        Returns:
            Optional[Dict[str, Any]]: The study group data or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE name = ? AND guild_id = ?', (name, guild_id))
            group = cursor.fetchone()
            if group:
                logger.debug(
                    f"Fetched StudyGroup by name '{name}' and guild_id '{guild_id}': Found.")
                return dict(group)
            else:
                logger.debug(
                    f"Fetched StudyGroup by name '{name}' and guild_id '{guild_id}': Not found.")
                return None
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching study group with name '{name}' in guild {guild_id}: {e}")
            raise

    def remove_member_from_study_group_db(self, group_id: str, user_id: int) -> None:
        """Removes a member from a study group.

        Args:
            group_id (str): The ID of the study group.
            user_id (int): The ID of the user to remove.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM study_groups_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))            
            logger.info(
                f"Removed member {user_id} from study group {group_id}.")
        except sqlite3.Error as e:
            logger.error(
                f"Error removing member {user_id} from study group {group_id}: {e}")
            raise

    def transfer_ownership_study_group_db(self, group_id: str, new_owner_id: int) -> None:
        """Transfers ownership of a study group to a new owner.

        Args:
            group_id (str): The ID of the study group.
            new_owner_id (int): The ID of the new owner.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''                
                UPDATE study_groups SET owner_id = ? WHERE group_id = ?
            ''', (new_owner_id, group_id))
            logger.info(
                f"Ownership of StudyGroup {group_id} transferred to {new_owner_id}.")
        except sqlite3.Error as e:
            logger.error(
                f"Error transferring ownership of study group {group_id} to {new_owner_id}: {e}")
            raise

    def fetch_members_of_group(self, group_id: str) -> List[int]:
        """Fetches all members of a study group.

        Args:
            group_id (str): The ID of the study group.

        Returns:
            List[int]: A list of user IDs of the members.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT user_id FROM study_groups_members WHERE group_id = ?', (group_id,))
            members_ids = [row['user_id'] for row in cursor.fetchall()]
            logger.debug(
                f"Fetched {len(members_ids)} members for study group {group_id}.")
            return members_ids
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching members of study group {group_id}: {e}")
            raise
    
    def fetch_owner_of_group(self, group_id: str) -> Optional[int]:
        """Fetches the owner of a study group.

        Args:
            group_id (str): The ID of the study group.

        Returns:
            Optional[int]: The user ID of the owner or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT owner_id FROM study_groups WHERE group_id = ?', (group_id,))
            owner = cursor.fetchone()
            logger.debug(
                f"Fetched owner for study group {group_id}: {owner['owner_id'] if owner else 'Not found'}.")
            return owner['owner_id'] if owner else None
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching owner of study group {group_id}: {e}")
            raise
    
    async def delete_study_group(self, group_id: int) -> None:
        """Deletes a study group.

        Args:
            group_id (int): The ID of the study group to delete.
        """
        try:
            cursor = self.conn.cursor()            
            cursor.execute("DELETE FROM study_groups WHERE id = ?", (group_id,))            
            cursor.execute("DELETE FROM study_groups_members WHERE group_id = ?", (group_id,))
            logger.info(f"Deleted study group with ID {group_id}")            
        except sqlite3.Error as e:
            logger.error(
                f"Error deleting study group with id {group_id}: {e}")
            raise

    def get_study_groups_of_user(self, user_id: int, guild_id: int) -> List[sqlite3.Row]:
        """Gets all study groups a user is in, within a specific guild.

        Args:
            user_id (int): The ID of the user.
            guild_id (int): The ID of the guild.

        Returns:
            List[sqlite3.Row]: A list of study groups.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT study_groups.* 
                FROM study_groups
                JOIN study_groups_members ON study_groups.group_id = study_groups_members.group_id
                WHERE study_groups_members.user_id = ? AND study_groups.guild_id = ?
            ''', (user_id, guild_id))
            groups = cursor.fetchall()
            logger.debug(
                f"Retrieved {len(groups)} group(s) for user {user_id} in guild {guild_id}.")
            return groups
        except sqlite3.Error as e:
            logger.error(
                f"Error getting study groups for user {user_id} in guild {guild_id}: {e}")
            raise

    def get_all_study_groups_of_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        """Gets all study groups in a specific guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            List[Dict[str, Any]]: A list of study groups.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM study_groups WHERE guild_id = ?', (guild_id,))
            groups = cursor.fetchall()
            groups_as_dicts = [dict(group) for group in groups]
            logger.debug(
                f"Retrieved {len(groups_as_dicts)} study groups for guild {guild_id}")
            return groups_as_dicts
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching study groups for guild {guild_id}: {e}")
            return []

    def get_member_study_group(self, user_id : int, group_id : str):
        """Gets a specific study groups from a user.

        Args:
            user_id (int): The ID of the user.
            group_id (str): The ID of the group.
        """
        pass

    ### --- CHECKIN SESSION DB OPERATIONS --- ###

    def save_checkin_session(self, session_data: Dict[str, Any]) -> None:
        """Saves a new check-in session to the database.

        Args:
            session_data (Dict[str, Any]): Dictionary containing check-in session data.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO checkin_sessions (
                    session_id, guild_id, name, creator_id, owner_id, text_id, 
                    duration, start_time, last_reminder_time, next_reminder_time, 
                    reminder_count, last_reminder_message_id, active
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_data["session_id"],
                session_data["guild_id"],
                session_data["name"],
                session_data["creator_id"],
                session_data["owner_id"],
                session_data["text_id"],
                session_data["duration"],
                session_data["start_time"],
                session_data["last_reminder_time"],
                session_data["next_reminder_time"],
                session_data["reminder_count"],
                session_data["last_reminder_message_id"],
                session_data["active"]
            ))
            logger.info(
                f"Check-in session '{session_data['name']}' created with ID {session_data['session_id']}.")
        except sqlite3.Error as e:
            logger.error(f"Error saving check-in session: {e}")
            raise

    def update_checkin_session(self, session_data: Dict[str, Any]) -> None:
        """Updates an existing check-in session in the database by session ID.

        Args:
            session_data (Dict[str, Any]): Dictionary containing the update data.
        """
        try:
            cursor = self.conn.cursor()
            update_fields = []
            update_values = []

            if "last_reminder_time" in session_data:
                update_fields.append("last_reminder_time = ?")
                update_values.append(session_data["last_reminder_time"])

            if "next_reminder_time" in session_data:
                update_fields.append("next_reminder_time = ?")
                update_values.append(session_data["next_reminder_time"])

            if "reminder_count" in session_data:
                update_fields.append("reminder_count = ?")
                update_values.append(session_data["reminder_count"])

            if "last_reminder_message_id" in session_data:
                update_fields.append("last_reminder_message_id = ?")
                update_values.append(session_data["last_reminder_message_id"])

            if "active" in session_data:
                update_fields.append("active = ?")
                update_values.append(session_data["active"])

            if update_fields:
                update_values.append(
                    session_data["session_id"])  # Add session_id for the WHERE clause
                query = f"UPDATE checkin_sessions SET {', '.join(update_fields)} WHERE session_id = ?"
                cursor.execute(query, update_values)                

            logger.info(
                f"Check-in session '{session_data['session_id']}' updated in the database.")
        except sqlite3.Error as e:
            logger.error(f"Error updating check-in session: {e}")
            raise

    def fetch_checkin_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a check-in session from the database by session ID.

        Args:
            session_id (str): The ID of the check-in session to fetch.

        Returns:
            Optional[Dict[str, Any]]: The check-in session data or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM checkin_sessions WHERE session_id = ?', (session_id,))
            session = cursor.fetchone()
            logger.debug(
                f"Fetched check-in session {session_id}: {'Found' if session else 'Not found'}.")
            return dict(session) if session else None
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching check-in session {session_id}: {e}")
            raise

    def add_or_update_checkin_member(self, session_id: str, member_id: int, status: str, absences: int = 0) -> None:
        """Inserts or updates a member's status in a check-in session.

        Args:
            session_id (str): The ID of the check-in session.
            member_id (int): The ID of the member.
            status (str): The status of the member.
            absences (int, optional): The number of absences for the member. Defaults to 0.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO checkin_members (session_id, member_id, status, absences)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, member_id) DO UPDATE SET
                    status = excluded.status,
                    absences = excluded.absences
            ''', (session_id, member_id, status, absences))
            logger.info(
                f"Updated member {member_id} in check-in session {session_id} with status '{status}' and absences {absences}.")
        except sqlite3.Error as e:
            logger.error(
                f"Error updating member {member_id} in check-in session {session_id}: {e}")
            raise

    def fetch_checkin_members(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetches all members in a check-in session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT member_id, status, absences
                FROM checkin_members
                WHERE session_id = ?
            ''', (session_id,))
            members = cursor.fetchall()
            logger.debug(
                f"Fetched {len(members)} members for check-in session {session_id}.")
            return [dict(member) for member in members]
        except sqlite3.Error as e:
            logger.error(
                f"Error fetching members for check-in session {session_id}: {e}")
            raise

    async def fetch_active_checkin_sessions(self) -> List[Dict[str, Any]]:
        """Fetches all active check-in sessions from the database.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an active session.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM checkin_sessions WHERE active = 1")
            sessions = cursor.fetchall()
            return [dict(session) for session in sessions]
        except sqlite3.Error as e:
            logger.error(f"Error fetching active check-in sessions: {e}")
            raise

    async def is_manager(self, user_id: int, guild_id: int) -> bool:
        """Checks if a user is a manager in a given guild.

        Args:
            user_id (int): The ID of the user.
            guild_id (int): The ID of the guild.

        Returns:
            bool: True if the user is a manager, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM managers WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            row = cursor.fetchone()
            return bool(row)  # Returns True if a row is found, False otherwise
        except sqlite3.Error as e:
            logger.error(f"Error checking if user {user_id} is a manager in guild {guild_id}: {e}")
            raise

    async def fetch_all_checkin_sessions(self) -> List[Dict[str, Any]]:
        """Fetches all check-in sessions from the database.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a session.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM checkin_sessions")
            sessions = cursor.fetchall()
            return [dict(session) for session in sessions]
        except sqlite3.Error as e:
            logger.error(f"Error fetching all check-in sessions: {e}")
            raise

