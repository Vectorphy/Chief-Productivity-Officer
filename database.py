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
            cursor.execute("PRAGMA table_info(study_groups_db);")
            columns = [column[1] for column in cursor.fetchall()]

            # If info_embed_id column does not exist, add it
            if 'info_embed_id' not in columns:
                cursor.execute('ALTER TABLE study_groups_db ADD COLUMN info_embed_id INTEGER DEFAULT 0;')
                logger.info("Added 'info_embed_id' column to 'study_groups_db' table.")
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups_db (
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

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_group_members_db (
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES study_groups_db (group_id),
                PRIMARY KEY (group_id, user_id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY,
                group_id INTEGER,
                start_time REAL,
                end_time REAL,
                focus_duration INTEGER,
                short_break_duration INTEGER,
                long_break_duration INTEGER,
                FOREIGN KEY (group_id) REFERENCES study_groups_db (id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                guild_id INTEGER,
                permission_level INTEGER NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_channel_logs (
                id INTEGER PRIMARY KEY,
                group_id INTEGER,
                channel_id INTEGER,
                creator_id INTEGER,
                create_time TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES study_groups_db (id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                vc_cleanup_time INTEGER DEFAULT 600,
                vc_category_id INTEGER
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            self.conn.commit()
            logger.info("Database tables created or verified.")

    async def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")


    ### --- STUDY GROUP FUNCTIONS --- ###

    ### Save Study Group
    async def save_study_group(self, study_group_data: Dict[str, Any]) -> None:
        """Insert a new study group into the database."""
        async with self.lock:
            cursor = self.conn.cursor()  # Generate a unique group ID
            cursor.execute('''
            INSERT INTO study_groups_db (
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
            fields_to_update.append("text_channel_id = ?")
            values.append(study_group_data["text_id"])
        
        if "info_embed_id" in study_group_data:
            fields_to_update.append("info_embed_id = ?")
            values.append(study_group_data["info_embed_id"])


        if "vc_id" in study_group_data:
            fields_to_update.append("voice_channel_id = ?")
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
        query = f"UPDATE study_groups_db SET {', '.join(fields_to_update)} WHERE group_id = ?"

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
            cursor.execute('SELECT * FROM study_groups_db WHERE LOWER(name) = LOWER(?) AND guild_id = ?', (name, guild_id))
            study_group_db = cursor.fetchone()
            logger.debug(f"Retrieved study group by name '{name}' for guild {guild_id}: {'Found' if study_group_db else 'Not found'}")
            return dict(study_group_db) if study_group_db else None


    ### Fetch Study Group by GROUP ID
    async def fetch_study_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups_db WHERE group_id = ?', (group_id,))
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
            INSERT OR IGNORE INTO group_members (group_id, user_id)
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
            UPDATE study_groups_db SET owner_id = ? WHERE group_id = ?
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
            cursor.execute('SELECT owner_id FROM study_groups_db WHERE group_id = ?', (group_id,))
            owner = cursor.fetchone()
            logger.debug(f"Fetched owner for Study Group {group_id}: {owner['owner_id'] if owner else 'Not found'}.")
            return owner['owner_id'] if owner else None


    async def delete_study_group(self, group_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM study_groups_db WHERE id = ?', (group_id,))
            cursor.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
            self.conn.commit()
            logger.info(f"Deleted study group with ID: {group_id}")


    ### Get Groups the User is in (Fetches multiple groups per user)
    async def get_study_groups_of_user(self, user_id : int, guild_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT study_groups.* 
                FROM study_groups_db 
                JOIN study_group_members ON study_groups_db.id = study_group_members.group_id
                WHERE study_group_members.user_id = ? AND study_groups_db.guild_id = ?
            ''', (user_id, guild_id))
            groups = cursor.fetchall()  # Fetch all groups within the guild
            logger.debug(f"Retrieved {len(groups)} group(s) for user {user_id} in guild {guild_id}.\n The groups are: {[group.name for group in groups]}")
            return groups


    ### Get All Groups in the Guild
    async def get_all_study_groups_of_guild(self, guild_id : int):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups_db WHERE guild_id = ?', (guild_id,))
            groups = cursor.fetchall()
            logger.debug(f"Retrieved {len(groups)} study groups for guild {guild_id}")
            return groups






    async def update_group_roles(self, group_id, admin_role_id, session_role_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE study_groups_db
            SET admin_role_id = ?, session_role_id = ?
            WHERE id = ?
            ''', (admin_role_id, session_role_id, group_id))
            self.conn.commit()
            logger.info(f"Updated roles for group {group_id}: admin_role_id={admin_role_id}, session_role_id={session_role_id}")

    async def get_group_roles(self, group_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT admin_role_id, session_role_id FROM study_groups_db WHERE id = ?', (group_id,))
            roles = cursor.fetchone()
            logger.debug(f"Retrieved roles for group {group_id}: {roles}")
            return roles

    async def update_voice_channel(self, group_id, voice_channel_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE study_groups_db
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
            JOIN study_groups_db ON voice_channel_logs.group_id = study_groups_db.id
            WHERE study_groups_db.guild_id = ? AND create_time >= ?
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
        

