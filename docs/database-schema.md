## Database Schema for [Bot Name]

This document outlines the schema for the MongoDB database used by the [Bot Name] Discord bot. It describes the collections, fields, data types, and relationships within the database.

### Collections

The database consists of the following collections:

1.  **`study_groups`:**  Stores information about study groups.
2.  **`checkin_sessions`:**  Stores data related to check-in sessions.
3.  **`tasks`:**  Stores user-created tasks.
4.  **`managers`:**  Stores information about bot managers and their permissions.
5.  **[Optional: Add other collections as needed based on your bot's features]**

### Fields

#### 1.  `study_groups`  Collection

| Field | Data Type | Description |
|--|--|--|
| `guild_id` | `int` | The ID of the Discord guild (server) where the study group exists. |
| `name` | `string` | The name of the study group. |
| `group_id` | `string` | A unique ID for the study group (could be a UUID). |
| `creator_id` | `int` | The ID of the Discord user who created the study group. |
| `owner_id` | `int` |The ID of the Discord user who is the current owner of the study group. |
| `category_id` | `int` | The ID of the Discord category where the study group's channels are located. |
| `max_members` | `int` | The maximum number of members allowed in the study group. |
| `member_ids` | `array` | An array of Discord user IDs representing the members of the study group. |
| `group_role_id` | `int` | The ID of the Discord role assigned to members of the study group. |
| `vc_id` | `int` | The ID of the Discord voice channel for the study group. |
| `info_embed_id` | `int` | The ID of the Discord message containing the study group's information embed. |
| `start_time` | `datetime` | The date and time when the study group was created. |
| `duration` | `int` | The duration of the study group session in seconds. |
| `end_time` | `datetime` | The date and time when the study group session is scheduled to end. |
| `speak_enabled` | `boolean` | Whether speaking is enabled in the voice channel (default: True). |
| `video_mode` | `string` | The video mode for the voice channel ("on", "off", "force"). |
| `video_timer` | `int` | The timer (in seconds) for forcing video to be on (if  `video_mode`  is "force"). |
| `active` | `boolean` | Whether the study group is currently active (default: True).|

#### 2.  `checkin_sessions`  Collection

| Field | Data Type | Description |
|--|--|--|
| `session_id` | `string` | A unique ID for the check-in session (could be a UUID). |
| `guild_id` | `int` | The ID of the Discord guild where the check-in session is taking place.
| `name` | `string` | The name of the check-in session. |
| `creator_id` | `int` | The ID of the Discord user who created the check-in session. |
| `owner_id` | `int` | The ID of the Discord user who is the current owner of the check-in session. |
| `text_id` | `int` | The ID of the Discord text channel where the check-in session is happening. |
| `member_ids` | `array` | An array of Discord user IDs representing the members of the check-in session. |
| `duration` | `int` | The duration of each check-in interval in seconds. |
| `start_time` | `datetime` | The date and time when the check-in session started. |
| `last_reminder_time` | `datetime` | The date and time when the last check-in reminder was sent. |
| `next_reminder_time` | `datetime` | The date and time when the next check-in reminder is scheduled to be sent. |
| `reminder_count` | `int` | The number of check-in reminders that have been sent. |
| `last_reminder_message_id` | `int` | The ID of the Discord message containing the last check-in reminder. |
| `active` | `boolean` | Whether the check-in session is currently active (default: True). |

#### 3.  `tasks`  Collection

| Field | Data Type | Description |
|--|--|--|
| `user_id` | `int` | The ID of the Discord user who created the task. |
| `description` | `string` | The description of the task. |
| `completed` | `boolean` | Whether the task has been completed (default: False). |
| `created_at` | `datetime` | The date and time when the task was created. |

#### 4.  `managers`  Collection

| Field | Data Type | Description |
|--|--|--|
| `user_id` | `int` | The ID of the Discord user who is a manager. |
| `guild_id` | `int` | The ID of the Discord guild (server) where the manager has permissions (optional). |
| `permission_level` | `int` | The permission level of the manager (see  `PermissionLevel`  enum in  `manager.py`). |

### Relationships

-   **One-to-Many:**  A study group (`study_groups`) can have multiple check-in sessions (`checkin_sessions`).
-   **One-to-Many:**  A user (`user_id`) can have multiple tasks (`tasks`).
-   **Many-to-Many:**  A manager (`managers`) can have permissions in multiple guilds, and a guild can have multiple managers.

### Notes

-   This schema is a starting point and can be modified or extended as needed based on the bot's features and requirements.
-   Consider using MongoDB's schema validation features to enforce data consistency.
-   Ensure you have appropriate indexes on fields frequently used in queries to optimize performance.
