# Chief Productivity Officer (CPO) Discord Bot Commands

## Study Groups

- `/create_group <name> [max_size]`: Create a new study group
  - `name`: The name of the study group
  - `max_size`: (Optional) Maximum number of members allowed in the group (default is 10)
  - `mentions`: The users to add to the group.

- `/join_group <name>`: Join an existing study group
  - `name`: The name of the study group you want to join
  - Adds you to the specified study group if it exists and isn't full.

- `/leave_group <name>`: Leave the current study group
  - `name`: The name of the study group you want to leave
  - Removes you from the specified study group.

- `/make_permanent <name>`: Make a temporary study group permanent (Group Owner only, up to 5 per guild)
  - `name`: The name of the study group to make permanent.
  - Converts a temporary study group to permanent, allowing it to persist even when all members leave. Limited to 5 permanent groups per guild.

- `/make_temporary <name>`: Make a permanent study group temporary (Group Owner only)
  - `name`: The name of the study group to make temporary.
  - Converts a permanent study group to temporary, causing it to be deleted when all members leave.

- `/group_add_member <group_name> <user_id>`: Add a member to a study group (Group Owner only)
    - `group_name`: The name of the group to add the member to.
    - `user_id`: The ID of the user to add.
    - Adds a member to the study group.

- `/group_remove_member <group_name> <user_id>`: Remove a member from a study group (Group Owner only)
    - `group_name`: The name of the group to remove the member from.
    - `user_id`: The ID of the user to remove.
    - Removes a member from the study group.

- `/end_group <name>`: End a study group (group creator or manager only)
  - `name`: The name of the study group to end
  - Deletes the specified study group, removing all members and associated roles.

- `/group_add_member <user_id>`: Add a member to a study group (Group Owner only)
    - `user_id`: The ID of the user to add
    - Adds a member to the study group.




- `/list_groups`: List all active study groups in the server
  - Displays a list of all current study groups with their member counts.

- `/invite_to_group <group_name> <user>`: Invite a user to your study group

- `/group_transfer_ownership <group_name> <user_id>`: Transfer ownership of a study group (Group Owner only)
    - `group_name`: The name of the group to transfer ownership of.
    - `user_id`: The ID of the user to transfer ownership to.
    - Transfers ownership of the study group to another member.
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

## Management

- `/add_bot_developer <user>`: Add a bot developer (Bot Developer only)
  - `user`: The user to promote to bot developer
  - Grants the highest level of permissions to the specified user.

- `/add_guild_manager <user>`: Add a guild manager (Bot Developer only)
  - `user`: The user to promote to guild manager
  - Grants server-specific management permissions to the specified user.

- `/remove_guild_manager <user>`: Remove a guild manager (Bot Developer only)
  - `user`: The user to demote from guild manager
  - Removes server-specific management permissions from the specified user.

- `/list_managers`: List all managers for this server
  - Displays a list of all users with elevated permissions (bot developers and guild managers) for the current server.

- `/set_permission_level <user> <level>`: Set the permission level for a user (Bot Developer only)
  - `user`: The user to set permissions for
  - `level`: The permission level to set (0: Regular User, 1: Group Creator, 2: Guild Manager, 3: Bot Developer)
  - Sets a specific permission level for the specified user.

Note: All commands use slash command syntax (/).



---