# Chief Productivity Officer (CPO) Discord Bot Commands

## Study Groups

- `/create_group <name> [max_size]`: Create a new study group
  - `name`: The name of the study group
  - `max_size`: (Optional) Maximum number of members allowed in the group (default is 10)
  - Creates a new study group with the specified name and optional size limit. Also creates associated roles for the group.

- `/join_group <name>`: Join an existing study group
  - `name`: The name of the study group you want to join
  - Adds you to the specified study group if it exists and isn't full.

- `/leave_group <name>`: Leave the current study group
  - `name`: The name of the study group you want to leave
  - Removes you from the specified study group.

- `/end_group <name>`: End a study group (group creator or manager only)
  - `name`: The name of the study group to end
  - Deletes the specified study group, removing all members and associated roles.

- `/transfer_group <new_owner> [group_name]`: Transfer study group ownership
  - `new_owner`: The server member to transfer ownership to
  - `group_name`: (Optional) The name of the study group (defaults to current channel's group)
  - Transfers ownership of the study group, updating database records and role privileges.

- `/list_groups`: List all active study groups in the server
  - Displays a list of all current study groups with their member counts.

- `/invite_to_group <group_name> <user>`: Invite a user to your study group
  - `group_name`: The name of your study group
  - `user`: The user you want to invite
  - Sends an invitation to the specified user to join your study group.

## Pomodoro

- `/start_pomodoro [focus] [short_break] [long_break]`: Start a Pomodoro session
  - `focus`: (Optional) Duration of focus sessions in minutes (default is 25)
  - `short_break`: (Optional) Duration of short breaks in minutes (default is 5)
  - `long_break`: (Optional) Duration of long breaks in minutes (default is 15)
  - Starts a new Pomodoro session for your study group with the specified durations.

- `/end_pomodoro`: End the current Pomodoro session
  - Stops the ongoing Pomodoro session for your study group.

- `/pause_pomodoro`: Pause the current Pomodoro session
  - Temporarily halts the timer in the ongoing Pomodoro session.

- `/resume_pomodoro`: Resume the paused Pomodoro session
  - Continues the timer from where it was paused in the Pomodoro session.

- `/pomodoro_status`: Check the status of the current Pomodoro session
  - Displays information about the ongoing Pomodoro session, including current stage, time remaining, and completed cycles.

## Voice Channels

- `/create_vc [name]`: Create a voice channel for the study group
  - `name`: (Optional) Custom name for the voice channel
  - Creates a new voice channel for your study group, visible only to group members.

- `/delete_vc`: Delete the voice channel for the study group
  - Removes the voice channel associated with your study group.

## Task List

- `/task_add <description>`: Add a new task to your list
  - `description`: The description of the task
  - Adds a new task to your personal task list.

- `/task_complete <task_id>`: Mark a task as complete
  - `task_id`: The ID of the task to mark as complete
  - Marks the specified task as completed in your task list.

- `/task_list`: List your current tasks
  - Displays a list of all your current tasks, both completed and incomplete.

## Check-in

- `/checkin <duration> <mentions>`: Start a check-in session
  - `duration`: The duration of the check-in session (e.g., "30m" for 30 minutes)
  - `mentions`: Users or roles to include in the check-in session
  - Starts a new check-in session with specified duration and participants.

## Management & Authorization

### Authorization Tiers
- **Admin Tier** (Permission Level 3-4): Server Owner, Server Administrators (`administrator=True`), Bot Developers. Admin commands are invisible to non-admins in Discord's slash command picker.
- **Mod Tier** (Permission Level 2): Moderators with `manage_guild`, `manage_channels`, `manage_roles`, `moderate_members`, `kick_members`, `ban_members`, staff roles, or registered in DB.
- **User Tier** (Permission Level 0-1): Baseline server members and study group participants.

### Management Commands

- `/sync_commands [guild_only: bool = False]`: Synchronize application slash commands with Discord (Admin only, invisible to non-admins)
  - `guild_only`: When `True`, synchronizes slash commands exclusively to the current server; when `False`, syncs globally.

- `/user_level [user: Optional[discord.Member]]`: Check the authorization level and tier of any member (Visible to all)
  - `user`: Optional member to inspect (defaults to yourself). Returns an embed displaying the user's High-Level Tier (`Admin`, `Mod`, `User`) and numeric permission level.

- `/add_bot_developer <user>`: Add a bot developer (Bot Developer only, Admin permission required)
  - `user`: The user to promote to bot developer.

- `/add_guild_manager <user>`: Add a guild manager (Admin only)
  - `user`: The user to promote to administrator/manager.

- `/remove_guild_manager <user>`: Remove a guild manager (Admin only)
  - `user`: The user to demote from manager status.

- `/list_managers`: List all managers and staff for this server (Moderator / Admin permission required)
  - Displays all staff members, moderators, administrators, and bot developers.

- `/set_permission_level <user> <level>`: Set the permission level for a user (Bot Developer only)
  - `user`: The user to set permissions for.
  - `level`: The level to assign (0: User, 1: Member, 2: Mod, 3: Admin, 4: Dev).

- `/sync_managers`: Synchronize server owner and moderators (Admin only)
  - Scans the guild and registers the server owner & administrators as `ADMIN` (Level 3) and moderators/staff as `MODERATOR` (Level 2).

Note: All commands use slash command syntax (`/`). Commands requiring elevated permissions use Discord's native `default_permissions` to remain hidden from unauthorized members in the Discord client interface.

---