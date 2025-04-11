# Project Agents Information

This document provides essential information for agents working on the StudyBot project.

## Project Overview

### Project Name

StudyBot

### Project Description

StudyBot is a Discord bot designed to facilitate and enhance study sessions and group work within Discord servers. It offers features such as:

*   Study group management
*   Pomodoro timers
*   Task lists
*   Check-in sessions
*   Voice channel management
*   Bot and user Management

### Project Goal

The primary goal of StudyBot is to create a comprehensive and user-friendly toolset that helps users organize, manage, and optimize their study time and group collaborations within Discord.

### Project Workflow

1.  **Task Assignment:** Tasks are assigned and prioritized based on project goals.
2.  **Code Implementation:** Implement features, bug fixes, or improvements.
3.  **Code Review:** Review code for quality and correctness.
4.  **Testing:** Thoroughly test changes to ensure they work as intended.
5.  **Documentation:** Update documentation to reflect changes.
6.  **Commit:** Commit the changes and push to the remote repository.
7.  **Deployment:** Deploy changes to the live environment.
8.  **Monitoring:** Monitor the changes to ensure no errors or problems are introduced.

### Project Architecture

StudyBot follows a modular design, with the main components being:

*   **`bot.py`:** The core bot file, responsible for bot initialization, event handling, and cog loading.
*   **`cogs/`:** A directory containing individual feature modules (cogs), such as `checkin.py`, `manager.py`, `pomodoro.py`, `study_groups.py`, `tasklist.py`, and `voice_channels.py`.
*   **`database.py`:** The database layer, currently using SQLite. It handles all database interactions.
*   **`utils.py`:** Contains utility functions used across the project.
*   **`docs/`:** Contains project documentation, including commands, agent information, and developer logs.

### Data Model

The database is managed by `database.py` and uses SQLite. Here are the tables and their columns:

#### `study_groups`

*   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
*   `guild_id` (INTEGER, NOT NULL)
*   `group_id` (TEXT, NOT NULL, UNIQUE)
*   `name` (TEXT, NOT NULL)
*   `creator_id` (INTEGER, NOT NULL)
*   `owner_id` (INTEGER, NOT NULL)
*   `category_id` (INTEGER, NOT NULL)
*   `max_members` (INTEGER, NOT NULL)
*   `group_role_id` (INTEGER, DEFAULT 0)
*   `vc_id` (INTEGER, DEFAULT 0)
*   `text_id` (INTEGER, DEFAULT 0)
*   `info_embed_id` (INTEGER, DEFAULT 0)
*   `video_timer` (INTEGER, DEFAULT 10)
*   `start_time` (REAL, NOT NULL)
*   `end_time` (REAL, NOT NULL)
*   `duration` (INTEGER, NOT NULL)
*   `active` (BOOLEAN, DEFAULT 0)
*   `is_permanent` (BOOLEAN, DEFAULT 0)

#### `study_groups_members`

*   `group_id` (TEXT, NOT NULL, FOREIGN KEY referencing `study_groups.group_id`)
*   `user_id` (INTEGER, NOT NULL)
*   PRIMARY KEY (`group_id`, `user_id`)

#### `pomodoro_sessions`

*   `id` (INTEGER, PRIMARY KEY)
*   `group_id` (TEXT, FOREIGN KEY referencing `study_groups.group_id`)
* `current_stage` (TEXT CHECK(`current_stage` IN ('focus', 'short_break', 'long_break')) DEFAULT 'focus')

#### `managers`

*   `user_id` (INTEGER, NOT NULL)
*   `guild_id` (INTEGER)
*   `permission_level` (INTEGER, NOT NULL)
* PRIMARY KEY (`user_id`, `guild_id`)

#### `voice_channel_logs`

*   `id` (INTEGER, PRIMARY KEY)
*   `group_id` (INTEGER, FOREIGN KEY referencing `study_groups.id` ON DELETE CASCADE)
*   `channel_id` (INTEGER)
*   `creator_id` (INTEGER)
*   `create_time` (REAL)

#### `guild_settings`

*   `guild_id` (INTEGER, PRIMARY KEY)
*   `vc_cleanup_time` (INTEGER)
*   `vc_category_id` (INTEGER)
* `logging_channel_id` (INTEGER)

#### `tasks`

*   `id` (INTEGER, PRIMARY KEY)
*   `group_id` (TEXT, NOT NULL)
*   `description` (TEXT, NOT NULL)
*   `completed` (INTEGER, NOT NULL, DEFAULT 0)
*   `created_at` (REAL, NOT NULL)
*   `due_date` (REAL)
*   `reminders_sent` (TEXT)

#### `checkin_sessions`

*   `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
*   `session_id` (TEXT, NOT NULL, UNIQUE)
*   `guild_id` (INTEGER)
*   `name` (TEXT, NOT NULL)
*   `creator_id` (INTEGER)
*   `owner_id` (INTEGER, NOT NULL)
*   `text_id` (INTEGER, NOT NULL)
*   `duration` (INTEGER, NOT NULL)
*   `start_time` (REAL, NOT NULL)
*   `last_reminder_time` (REAL, NOT NULL)
*   `next_reminder_time` (REAL, NOT NULL)
*   `reminder_count` (INTEGER, NOT NULL)
* `last_reminder_message_id` (INTEGER, NOT NULL DEFAULT 0)
*   `active` (BOOLEAN, DEFAULT 1)

#### `checkin_members`

*   `session_id` (TEXT, NOT NULL, FOREIGN KEY referencing `checkin_sessions.session_id` ON DELETE CASCADE)
*   `member_id` (INTEGER, NOT NULL)
* PRIMARY KEY (`session_id`, `member_id`)

### API and Functions (`database.py`)

All functions in `database.py` are asynchronous (`async def`).

#### Study Group Operations

*   **`save_study_group(study_group_data: Dict[str, Any]) -> int`**
    *   **Parameters:** `study_group_data` (dictionary containing group details).
    *   **Returns:** The ID of the newly created study group.
    *   **Description:** Saves a new study group to the database.
*   **`update_member_study_group(group_id: str, user_id: int) -> None`**
    *   **Parameters:** `group_id` (ID of the group), `user_id` (ID of the member).
    *   **Returns:** None.
    *   **Description:** Updates a member's status in a study group.
*   **`update_study_group(study_group_data: Dict[str, Any]) -> Optional[Dict[str, Any]]`**
    *   **Parameters:** `study_group_data` (dictionary containing updated group details).
    *   **Returns:** The updated study group data or None if not found.
    *   **Description:** Updates an existing study group in the database.
*   **`fetch_study_group_by_id(group_id: str) -> Optional[Dict[str, Any]]`**
    *   **Parameters:** `group_id` (ID of the group).
    *   **Returns:** The study group data or None if not found.
    *   **Description:** Fetches a study group by its ID.
*   **`fetch_study_group_by_name(name: str, guild_id: int) -> Optional[Dict[str, Any]]`**
    *   **Parameters:** `name` (name of the group), `guild_id` (ID of the guild).
    *   **Returns:** The study group data or None if not found.
    *   **Description:** Fetches a study group by its name and guild ID.
*   **`remove_member_from_study_group_db(group_id: str, user_id: int) -> None`**
    *   **Parameters:** `group_id` (ID of the group), `user_id` (ID of the member).
    *   **Returns:** None.
    *   **Description:** Removes a member from a study group.
*   **`transfer_ownership_study_group_db(group_id: str, new_owner_id: int) -> None`**
    *   **Parameters:** `group_id` (ID of the group), `new_owner_id` (ID of the new owner).
    *   **Returns:** None.
    *   **Description:** Transfers ownership of a study group.
*   **`fetch_members_of_group(group_id: str) -> List[int]`**
    *   **Parameters:** `group_id` (ID of the group).
    *   **Returns:** A list of user IDs of the members.
    *   **Description:** Fetches all members of a study group.
*   **`fetch_owner_of_group(group_id: str) -> Optional[int]`**
    *   **Parameters:** `group_id` (ID of the group).
    *   **Returns:** The user ID of the owner or None if not found.
    *   **Description:** Fetches the owner of a study group.
*   **`delete_study_group(group_id: int) -> None`**
    *   **Parameters:** `group_id` (ID of the group).
    *   **Returns:** None.
    *   **Description:** Deletes a study group.
*   **`get_study_groups_of_user(user_id: int, guild_id: int) -> List[sqlite3.Row]`**
    *   **Parameters:** `user_id` (ID of the user), `guild_id` (ID of the guild).
    *   **Returns:** A list of study groups.
    *   **Description:** Gets all study groups a user is in, within a specific guild.
*   **`get_all_study_groups_of_guild(guild_id: int) -> List[Dict[str, Any]]`**
    *   **Parameters:** `guild_id` (ID of the guild).
    *   **Returns:** A list of study groups.
    *   **Description:** Gets all study groups in a specific guild.
* **`get_member_study_group(user_id : int, group_id : str)`**
    *   **Parameters:** `user_id` (The ID of the user.), `group_id` (The ID of the group.)
    *   **Returns:** Nothing, is a stub for now.
    *   **Description:** Gets a specific study groups from a user.

#### Check-in Session Operations

*   **`save_checkin_session(session_data: Dict[str, Any]) -> None`**
    *   **Parameters:** `session_data` (dictionary containing session details).
    *   **Returns:** None.
    *   **Description:** Saves a new check-in session to the database.
*   **`update_checkin_session(session_data: Dict[str, Any]) -> None`**
    *   **Parameters:** `session_data` (dictionary containing updated session details).
    *   **Returns:** None.
    *   **Description:** Updates an existing check-in session.
*   **`fetch_checkin_session(session_id: str) -> Optional[Dict[str, Any]]`**
    *   **Parameters:** `session_id` (ID of the session).
    *   **Returns:** The session data or None if not found.
    *   **Description:** Fetches a check-in session by its ID.
* **`add_or_update_checkin_member(self, session_id: str, member_id: int, status: str, absences: int = 0) -> None`**
    *   **Parameters:** `session_id` (The ID of the check-in session.), `member_id` (The ID of the member.), `status` (The status of the member.), `absences` (The number of absences for the member.)
    *   **Returns:** None.
    *   **Description:** Inserts or updates a member's status in a check-in session.
* `fetch_checkin_members(session_id: str) -> List[Dict[str, Any]]`
    *   **Parameters:** `session_id` (The ID of the check-in session.)
    *   **Returns:** List of members.
    *   **Description:** Fetches all members in a check-in session.

### Allowed Things

*   Creating, modifying, and deleting code files.
*   Creating, modifying, and deleting documentation files.
*   Using Python 3.11 or higher.
*   Using Git for version control.
*   Using the sqlite3 library.
* Creating any new function or file needed to improve the project.
* Using any tool to improve the project, like code writing, code reading, or any other.
* Ask for any assistance needed.

### Forbidden Things

*   Using any external API unless explicitly permitted.
*   Making changes to the Git history.
*   Compromising security in any way.
*   Breaking the existing code or functionality.
* Sharing the project's code with anyone.
* Writing any code that can be harmful or illegal.

### General Instructions

*   **Code Quality:** Write clean, well-documented, and efficient code.
*   **Error Handling:** Implement proper error handling and logging.
*   **Testing:** Test code thoroughly before committing.
*   **Modularity:** Keep code modular and organized.
*   **Readability:** Prioritize code readability and clarity.
* **Documentation**: Document any change made in the /docs folder.
* **Follow instructions**: Always follow the instructions given.
* **Ask for feedback**: Ask for feedback when needed.

### Specific Instructions

*   **Database Interactions:** Use the `database.py` file for all database operations.
*   **Asynchronous Operations:** All database functions are asynchronous, use `await` when calling them.
* **Database indexing**: Create any index needed in the `connect` function in `database.py`.
* **Commit Messages:** Write clear and descriptive commit messages.
* **Follow workflow**: Follow the project workflow.
* **Type hints**: Always use type hints.
* **Logging**: Always use the logger.
* **Check if a file/function exist**: If a function or file is called or edited, check if it exists before doing so.
* **If you don't know, ask**: If you don't know how to do something, ask for assistance.
* **If the instructions are unclear**: If the instructions are unclear, ask for clarification.

### Additional Information

*   **Dependencies:** Check `requirements.txt` for project dependencies.
*   **Entry Point:** `main.py` or `bot.py` is the main entry point for running the bot.
*   **Environment:** The bot runs within a Discord server environment.
* **Logging**: Use the `logger` created in the database.py file to log any important event or error.
* **If in doubt, ask**: If you have any doubt, ask for clarification.

### Project documentation

* /docs/commands.md: Documentation for the bot commands.
* /docs/dev-log.md: A log to document any change or relevant event.
* /docs/readme.md: A short description of the project.
* /docs/agents.md: This file, to provide all the necessary information for the agents.
* /docs/architecture.md: A file that describes the project architecture.
* /docs/api.md: A file that describes the project API.
* /docs/data-model.md: A file that describes the project data model.
* /docs/implementation.md: A file that describes the project implementation.
* /docs/testing.md: A file that describes the project testing.
* /docs/deployment.md: A file that describes the project deployment.

### Further development

* **Cogs Update:** Update the cogs to use the updated database.py methods.
* **Testing:** Run the tests to ensure everything is working correctly.

***
