import sqlite3
import asyncio
from datetime import datetime
import logging
from typing import List, Any, Dict, Optional

logger = logging.getLogger(__name__)

class DBHandler:
    def __init__(self, db_name: str ='bot_database.sqlite'):
        self.db_name :str = db_name
        self.conn: Optional[sqlite3.Connection] = None
        self.lock : asyncio.Lock = asyncio.Lock()
        logger.info(f"Database initialized with name: {db_name}")

    async def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_name}")
        await self.create_tables()

    async def create_tables(self):
        async with self.lock:
            cursor = self.conn.cursor()
            
            # Check if the info_embed_id column exists
            cursor.execute("PRAGMA table_info(study_groups);")
            columns = [column[1] for column in cursor.fetchall()]

            # If info_embed_id column does not exist, add it
            if 'info_embed_id' not in columns:
                cursor.execute('ALTER TABLE study_groups ADD COLUMN info_embed_id INTEGER DEFAULT 0;')
                logger.info("Added 'info_embed_id' column to 'study_groups' table.")
            
            ### STUDY GROUPS TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                group_id TEXT NOT NULL UNIQUE,
                creator_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                max_members INTEGER NOT NULL,
                group_role_id INTEGER DEFAULT 0,
                vc_id INTEGER DEFAULT 0,
                text_id INTEGER DEFAULT 0,
                info_embed_id INTEGER DEFAULT 0,
                speak_enabled BOOLEAN DEFAULT 1,
                video_mode TEXT DEFAULT 'off',
                video_timer INTEGER DEFAULT 10,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration INTEGER NOT NULL,
                active BOOLEAN DEFAULT 0
            )
            ''')
            logger.info("Created 'study_groups' table.")

            ### STUDY GROUP MEMBERS TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups_members (
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES study_groups (group_id),
                PRIMARY KEY (group_id, user_id)
            )
            ''')
            logger.info("Created 'study_groups_members' table.")

            ### POMODORO TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY,
                group_id INTEGER,
                start_time REAL,
                end_time REAL,
                focus_duration INTEGER,
                short_break_duration INTEGER,
                long_break_duration INTEGER,
                FOREIGN KEY (group_id) REFERENCES study_groups (id)
            )
            ''')
            logger.info("Created 'pomodoro_sessions' table.")

            ### MANAGERS TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                guild_id INTEGER,
                permission_level INTEGER NOT NULL
            )
            ''')
            logger.info("Created 'managers' table.")

            ### VOICE CHANNEL LOGS
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_channel_logs (
                id INTEGER PRIMARY KEY,
                group_id INTEGER,
                channel_id INTEGER,
                creator_id INTEGER,
                create_time TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES study_groups (id)
            )
            ''')
            logger.info("Created 'voice_channel_logs' table.")

            ### GUILD SETTINGS
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                vc_cleanup_time INTEGER DEFAULT 600,
                vc_category_id INTEGER
            )
            ''')
            logger.info("Created 'guild_settings' table.")

            ### TASKS
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            logger.info("Created 'tasks' table.")

            ### CHECKIN SESSIONS TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                creator_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                text_id INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                start_time REAL NOT NULL,
                last_reminder_time REAL NOT NULL,
                next_reminder_time REAL NOT NULL,
                reminder_count INTEGER NOT NULL,
                last_reminder_message_id INTEGER,
                active BOOLEAN DEFAULT 1
            )
            ''')
            logger.info("Created 'checkin_sessions' table.")

            ### CHECKIN MEMBERS TABLE
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkin_members (
                session_id TEXT NOT NULL,
                member_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                absences INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES checkin_sessions (session_id),
                PRIMARY KEY (session_id, member_id)
            )
            ''')
            logger.info("Created 'checkin_members' table.")

            self.conn.commit()
            logger.info("Database tables created or verified.")

    async def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")


    ### --- STUDY GROUP DB OPERATIONS --- ###

    ### Save Study Group
    async def save_study_group(self, study_group_data: Dict[str, Any]) -> None:
        """Insert a new study group into the database."""
        async with self.lock:
            cursor = self.conn.cursor()  # Generate a unique group ID
            cursor.execute('''
            INSERT INTO study_groups (
                guild_id, name, group_id, creator_id, owner_id, category_id, 
                max_members, group_role_id, vc_id, text_id, info_embed_id, 
                speak_enabled, video_mode, video_timer, 
                start_time, end_time, duration, active
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                study_group_data["guild_id"],
                study_group_data["name"],
                study_group_data["group_id"],
                study_group_data["creator_id"],
                study_group_data["owner_id"],
                study_group_data["category_id"],
                study_group_data["max_members"],
                study_group_data["group_role_id"],
                study_group_data["vc_id"],
                study_group_data["text_id"],
                study_group_data["info_embed_id"],
                study_group_data["speak_enabled"],
                study_group_data["video_mode"],
                study_group_data["video_timer"],
                study_group_data["start_time"],
                study_group_data["end_time"],
                study_group_data["duration"],
                study_group_data["active"]
            ))
            self.conn.commit()
            logger.info(f"Study group '{study_group_data['name']}' created with ID {study_group_data['group_id']}")
        

    ### Update Study Group
    async def update_study_group_by_id(self, study_group_data: Dict[str, Any]) -> None:
        # List of fields to update dynamically
        fields_to_update = []
        values = []

        # Append fields only if they are present in the passed data
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

        if "start_time" in study_group_data:
            fields_to_update.append("start_time = ?")
            values.append(study_group_data["start_time"])

        if "duration" in study_group_data:
            fields_to_update.append("duration = ?")
            values.append(study_group_data["duration"])

        if "end_time" in study_group_data:
            fields_to_update.append("end_time = ?")
            values.append(study_group_data["end_time"])

        if "speak_enabled" in study_group_data:
            fields_to_update.append("speak_enabled = ?")
            values.append(study_group_data["speak_enabled"])

        if "video_mode" in study_group_data:
            fields_to_update.append("video_mode = ?")
            values.append(study_group_data["video_mode"])

        if "video_timer" in study_group_data:
            fields_to_update.append("video_timer = ?")
            values.append(study_group_data["video_timer"])

        if "active" in study_group_data:
            fields_to_update.append("active = ?")
            values.append(study_group_data["active"])

        # If no fields are present to update, return early
        if not fields_to_update:
            logger.warning("No fields to update for the study group.")
            return

        # Ensure that the group_id is always added as the last value for the WHERE clause
        values.append(study_group_data["group_id"])

        # Construct the SQL query dynamically based on the fields to update
        query = f"UPDATE study_groups SET {', '.join(fields_to_update)} WHERE group_id = ?"

        # Execute the dynamically generated query
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()

        logger.info(f"StudyGroup '{study_group_data.get('name', 'Unknown')}' updated in the database.")


    ### Fetch Study Group by NAME (and GUILD ID)
    async def fetch_study_group_by_name(self, name : str, guild_id : str) -> Dict[str, Any]:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE LOWER(name) = LOWER(?) AND guild_id = ?', (name, guild_id))
            study_group_db = cursor.fetchone()
            logger.debug(f"Retrieved study group by name '{name}' for guild {guild_id}: {'Found' if study_group_db else 'Not found'}")
            return dict(study_group_db) if study_group_db else None


    ### Fetch Study Group by GROUP ID
    async def fetch_study_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE group_id = ?', (group_id,))
            group = cursor.fetchone()
            if group:
                logger.debug(f"Fetched StudyGroup {group_id}: Found.")
                return dict(group)
            else:
                logger.debug(f"Fetched StudyGroup {group_id}: Not found.")
                return None


    ### Add Member to Study Group by Group ID
    async def add_member_to_study_group_db(self, group_id: str, user_id: int) -> None:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR IGNORE INTO study_group_members (group_id, user_id)
            VALUES (?, ?)
            ''', (group_id, user_id))
            self.conn.commit()
            logger.info(f"Added member {user_id} to StudyGroup {group_id}.")


    ### Remove Member from Study Group by Group ID
    async def remove_member_from_study_group_db(self, group_id: str, user_id: int) -> None:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            DELETE FROM group_members WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            self.conn.commit()
            logger.info(f"Removed member {user_id} from StudyGroup {group_id}.")


    ### Transfer Study Group Ownership, using Group ID
    async def transfer_ownership_study_group_db(self, group_id: str, new_owner_id: int) -> None:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE study_groups SET owner_id = ? WHERE group_id = ?
            ''', (new_owner_id, group_id))
            self.conn.commit()
            logger.info(f"Ownership of StudyGroup {group_id} transferred to {new_owner_id}.")


    ### Fetch Study Group Members from Group ID
    async def fetch_members_of_group(self, group_id: str) -> List[int]:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT user_id FROM group_members WHERE group_id = ?', (group_id,))
            members_ids = [row['user_id'] for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(members_ids)} members for StudyGroup {group_id}.")
            return members_ids


    ### Fetch Owner of Group by Group ID
    async def fetch_owner_of_group(self, group_id: str) -> Optional[int]:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT owner_id FROM study_groups WHERE group_id = ?', (group_id,))
            owner = cursor.fetchone()
            logger.debug(f"Fetched owner for Study Group {group_id}: {owner['owner_id'] if owner else 'Not found'}.")
            return owner['owner_id'] if owner else None


    ### Delete Study Group
    async def delete_study_group(self, group_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM study_groups WHERE id = ?', (group_id,))
            cursor.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
            self.conn.commit()
            logger.info(f"Deleted study group with ID: {group_id}")


    ### Get Groups the User is in (Fetches multiple groups per user)
    async def get_study_groups_of_user(self, user_id : int, guild_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT study_groups.* 
                FROM study_groups 
                JOIN study_group_members ON study_groups.id = study_group_members.group_id
                WHERE study_group_members.user_id = ? AND study_groups.guild_id = ?
            ''', (user_id, guild_id))
            groups = cursor.fetchall()  # Fetch all groups within the guild
            logger.debug(f"Retrieved {len(groups)} group(s) for user {user_id} in guild {guild_id}.\n The groups are: {[group.name for group in groups]}")
            return groups


    ### Get All Groups in the Guild
    async def get_all_study_groups_of_guild(self, guild_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE guild_id = ?', (guild_id,))
            groups = cursor.fetchall()
            logger.debug(f"Retrieved {len(groups)} study groups for guild {guild_id}")
            return groups  



    ### --- CHECKIN SESSION DB OPERATIONS --- ###


    ## Save Check-in Session
    async def save_checkin_session(self, session_data: Dict[str, Any]) -> None:
        """Insert a new check-in session into the database."""
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO checkin_sessions (
                session_id, guild_id, name, creator_id, owner_id, text_id, 
                duration, start_time, last_reminder_time, next_reminder_time, reminder_count, last_reminder_message_id, active
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
            self.conn.commit()
            logger.info(f"Check-in session '{session_data['name']}' created with ID {session_data['session_id']}.")
    
    
    ## Update Check-in Session
    async def update_checkin_session(self, session_data: Dict[str, Any]) -> None:
        """Update an existing check-in session in the database by session ID."""
        async with self.lock:
            cursor = self.conn.cursor()
            update_fields = []
            update_values = []

            # Dynamically build the query based on which fields are in session_data
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

            # Ensure that we're updating only the necessary fields
            if update_fields:
                update_values.append(session_data["session_id"])  # Add session_id for the WHERE clause
                query = f"UPDATE checkin_sessions SET {', '.join(update_fields)} WHERE session_id = ?"
                cursor.execute(query, update_values)
                self.conn.commit()

            logger.info(f"Check-in session '{session_data['session_id']}' updated in the database.")

    
    ## Fetch Check-in Session by Session ID
    async def fetch_checkin_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a check-in session from the database by session ID."""
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM checkin_sessions WHERE session_id = ?', (session_id,))
            session = cursor.fetchone()
            logger.debug(f"Fetched check-in session {session_id}: {'Found' if session else 'Not found'}.")
            return dict(session) if session else None


    ## Add or Update Check-in Member
    async def add_or_update_checkin_member(self, session_id: str, member_id: int, status: str, absences: int = 0) -> None:
        """Insert or update a member's status in a check-in session."""
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO checkin_members (session_id, member_id, status, absences)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, member_id) DO UPDATE SET
                status = excluded.status,
                absences = excluded.absences
            ''', (session_id, member_id, status, absences))
            self.conn.commit()
            logger.info(f"Updated member {member_id} in check-in session {session_id} with status '{status}' and absences {absences}.")


    ## Fetch Check-in Members by Session ID
    async def fetch_checkin_members(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetch all members in a check-in session."""
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM checkin_members WHERE session_id = ?', (session_id,))
            members = cursor.fetchall()
            logger.debug(f"Fetched {len(members)} members for check-in session {session_id}.")
            return [dict(member) for member in members]


    ## Fetch Active Check-in Sessions
    async def fetch_active_checkin_sessions(self) -> List[Dict[str, Any]]:
        """
        Fetch all active check-in sessions from the database.
        Returns a list of active sessions with all relevant session data.
        """
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM checkin_sessions WHERE active = 1')
            sessions = cursor.fetchall()
            logger.debug(f"Fetched {len(sessions)} active check-in sessions.")
            return [dict(session) for session in sessions]


    ## Delete Check-in Session
    async def delete_checkin_session(self, session_id: str) -> None:
        """Remove a check-in session and its members from the database."""
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM checkin_members WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM checkin_sessions WHERE session_id = ?', (session_id,))
            self.conn.commit()
            logger.info(f"Deleted check-in session with ID: {session_id}.")








    async def update_group_roles(self, group_id, admin_role_id, session_role_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE study_groups
            SET admin_role_id = ?, session_role_id = ?
            WHERE id = ?
            ''', (admin_role_id, session_role_id, group_id))
            self.conn.commit()
            logger.info(f"Updated roles for group {group_id}: admin_role_id={admin_role_id}, session_role_id={session_role_id}")

    async def get_group_roles(self, group_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT admin_role_id, session_role_id FROM study_groups WHERE id = ?', (group_id,))
            roles = cursor.fetchone()
            logger.debug(f"Retrieved roles for group {group_id}: {roles}")
            return roles

    async def update_voice_channel(self, group_id, voice_channel_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE study_groups
            SET voice_channel_id = ?
            WHERE id = ?
            ''', (voice_channel_id, group_id))
            self.conn.commit()
            logger.info(f"Updated voice channel for group {group_id}: voice_channel_id={voice_channel_id}")

    async def log_vc_creation(self, group_id, channel_id, creator_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO voice_channel_logs (group_id, channel_id, creator_id, create_time)
            VALUES (?, ?, ?, ?)
            ''', (group_id, channel_id, creator_id, datetime.now()))
            self.conn.commit()
            logger.info(f"Logged voice channel creation: group={group_id}, channel={channel_id}, creator={creator_id}")

    async def get_vc_logs(self, guild_id, start_date):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT channel_id, creator_id, create_time FROM voice_channel_logs
            JOIN study_groups ON voice_channel_logs.group_id = study_groups.id
            WHERE study_groups.guild_id = ? AND create_time >= ?
            ''', (guild_id, start_date))
            logs = cursor.fetchall()
            logger.debug(f"Retrieved {len(logs)} VC logs for guild {guild_id} since {start_date}")
            return logs

    async def update_vc_cleanup_time(self, guild_id, cleanup_time):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO guild_settings (guild_id, vc_cleanup_time)
            VALUES (?, ?)
            ''', (guild_id, cleanup_time))
            self.conn.commit()
            logger.info(f"Updated VC cleanup time for guild {guild_id}: {cleanup_time} seconds")

    async def get_vc_cleanup_time(self, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT vc_cleanup_time FROM guild_settings WHERE guild_id = ?', (guild_id,))
            result = cursor.fetchone()
            cleanup_time = result['vc_cleanup_time'] if result else 600
            logger.debug(f"Retrieved VC cleanup time for guild {guild_id}: {cleanup_time} seconds")
            return cleanup_time

    async def update_vc_category(self, guild_id, category_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO guild_settings (guild_id, vc_category_id)
            VALUES (?, ?)
            ''', (guild_id, category_id))
            self.conn.commit()
            logger.info(f"Updated VC category for guild {guild_id}: category_id={category_id}")

    async def get_vc_category(self, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT vc_category_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
            result = cursor.fetchone()
            category_id = result['vc_category_id'] if result else None
            logger.debug(f"Retrieved VC category for guild {guild_id}: {category_id}")
            return category_id

    async def add_manager(self, user_id, guild_id, permission_level):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO managers (user_id, guild_id, permission_level)
            VALUES (?, ?, ?)
            ''', (user_id, guild_id, permission_level))
            self.conn.commit()
            logger.info(f"Added/Updated manager: user={user_id}, guild={guild_id}, permission_level={permission_level}")

    async def remove_manager(self, user_id, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM managers WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
            self.conn.commit()
            logger.info(f"Removed manager: user={user_id}, guild={guild_id}")

    async def get_manager(self, user_id, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM managers WHERE user_id = ? AND (guild_id = ? OR guild_id IS NULL)', (user_id, guild_id))
            manager = cursor.fetchone()
            logger.debug(f"Retrieved manager info for user {user_id} in guild {guild_id}: {'Found' if manager else 'Not found'}")
            return manager

    async def get_all_managers(self, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM managers WHERE guild_id = ? OR guild_id IS NULL', (guild_id,))
            managers = cursor.fetchall()
            logger.debug(f"Retrieved {len(managers)} managers for guild {guild_id}")
            return managers

    async def add_task(self, user_id, description):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO tasks (user_id, description)
            VALUES (?, ?)
            ''', (user_id, description))
            task_id = cursor.lastrowid
            self.conn.commit()
            logger.info(f"Added task for user {user_id}: ID={task_id}, description='{description}'")
            return task_id

    async def complete_task(self, user_id, task_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE tasks SET completed = 1
            WHERE id = ? AND user_id = ?
            ''', (task_id, user_id))
            self.conn.commit()
            success = cursor.rowcount > 0
            logger.info(f"{'Completed' if success else 'Failed to complete'} task {task_id} for user {user_id}")
            return success

    async def get_user_tasks(self, user_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,))
            tasks = cursor.fetchall()
            logger.debug(f"Retrieved {len(tasks)} tasks for user {user_id}")
            return tasks
