import sqlite3
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='bot_database.sqlite'):
        self.db_name = db_name
        self.conn = None
        self.lock = asyncio.Lock()
        logger.info(f"Database initialized with name: {db_name}")

    async def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_name}")
        await self.create_tables()

    async def create_tables(self):
        async with self.lock:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                creator_id INTEGER NOT NULL,
                max_size INTEGER NOT NULL,
                end_time REAL NOT NULL,
                guild_id INTEGER NOT NULL,
                admin_role_id INTEGER,
                session_role_id INTEGER,
                voice_channel_id INTEGER
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                user_id INTEGER,
                FOREIGN KEY (group_id) REFERENCES study_groups (id),
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
                FOREIGN KEY (group_id) REFERENCES study_groups (id)
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
                FOREIGN KEY (group_id) REFERENCES study_groups (id)
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

    async def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

    async def create_study_group(self, name, creator_id, max_size, end_time, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO study_groups (name, creator_id, max_size, end_time, guild_id, admin_role_id, session_role_id, voice_channel_id)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
            ''', (name, creator_id, max_size, end_time, guild_id))
            group_id = cursor.lastrowid
            self.conn.commit()
            logger.info(f"Created study group: {name} (ID: {group_id})")
            return group_id
    async def get_study_group_by_name(self, guild_id, name):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE LOWER(name) = LOWER(?) AND guild_id = ?', (name, guild_id))
            group = cursor.fetchone()
            logger.debug(f"Retrieved study group by name '{name}' for guild {guild_id}: {'Found' if group else 'Not found'}")
            return group

    async def get_study_group(self, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE guild_id = ?', (guild_id,))
            group = cursor.fetchone()
            logger.debug(f"Retrieved study group for guild {guild_id}: {'Found' if group else 'Not found'}")
            return group

    async def delete_study_group(self, group_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM study_groups WHERE id = ?', (group_id,))
            cursor.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
            self.conn.commit()
            logger.info(f"Deleted study group with ID: {group_id}")

    async def get_user_group(self, user_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT study_groups.* 
                FROM study_groups 
                JOIN group_members ON study_groups.id = group_members.group_id
                WHERE group_members.user_id = ?
            ''', (user_id,))
            group = cursor.fetchone()
            logger.debug(f"Retrieved group for user {user_id}: {'Found' if group else 'Not found'}")
            return group

    async def add_group_member(self, group_id, user_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR IGNORE INTO group_members (group_id, user_id)
            VALUES (?, ?)
            ''', (group_id, user_id))
            self.conn.commit()
            logger.info(f"Added user {user_id} to group {group_id}")

    async def remove_group_member(self, group_id, user_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
            DELETE FROM group_members
            WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            self.conn.commit()
            logger.info(f"Removed user {user_id} from group {group_id}")

    async def get_group_members(self, group_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT user_id FROM group_members WHERE group_id = ?', (group_id,))
            members = [row['user_id'] for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(members)} members for group {group_id}")
            return members
        
    async def get_all_study_groups(self, guild_id):
        async with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM study_groups WHERE guild_id = ?', (guild_id,))
            groups = cursor.fetchall()
            logger.debug(f"Retrieved {len(groups)} study groups for guild {guild_id}")
            return groups


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
        

