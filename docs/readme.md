# Chief Productivity Officer (CPO) Discord Bot

Chief Productivity Officer (CPO) is a versatile Discord bot designed to boost productivity and organization within your Discord server. It offers a wide range of features, including study group management, Pomodoro sessions, task tracking, and more. CPO is built to help users stay focused, collaborate effectively, and achieve their goals within the Discord environment.

## Key Features

*   **Study Group Management:**
    *   Create, join, and manage study groups with customizable roles, voice channels, and text channels.
    *   Temporary and permanent group options.
    *   Vote-kick system for group management.
    * Automatic ownership transfer for permanent groups.
    * Automatic group deletion for temporary groups when they are no longer in use.
    *   Toggle member speaking and video permissions.
*   **Pomodoro Sessions:**
    *   Start, pause, resume, and end Pomodoro sessions for individuals or groups.
    *   Configurable work, short break, and long break durations.
    *   Automated timers and notifications.
    *   Voice channel integration for group sessions.
    *   Automatic session end when all members leave the voice channel.
*   **Check-In Sessions:**
    *   Schedule check-in sessions for task updates and collaboration.
    *   Send initial and reminder messages.
    *   Track member presence (present, absent, exited).
    *   Automatic progression of members to "absent" if they don't respond.
    *   Automatic session end if no members remain.
*   **Task Management:**
    *   Create, complete, and list tasks.
    *   Set due dates and reminders for tasks.
    * Manage tasks in an easy to use way.
*   **Dynamic Voice Channels:**
    *   Automatically manage voice channels for study groups and Pomodoro sessions.
    *   Create and delete channels as needed.
*   **User Management and Permissions:**
    *   Manage user permissions and roles.
    *   Add or remove bot developers and guild managers.
    *   Set individual permission levels.
* **Database**:
    * Store all the bot data in a database.
* **Logging**:
    * Log all the actions of the bot for debugging.
* **Plans for pycord migration**:
    * The project plans to migrate to pycord to get access to more features and improve the performance.
* **Plans for MongoDB migration**:
    * The project plans to migrate to MongoDB for better scalability, performance and flexibility.

## Installation

1.  **Clone the repository:**
2.  **Install dependencies:**
3.  **Set up your Discord bot:**

    *   Create a new application on the [Discord Developer Portal](https://discord.com/developers/applications).
    *   Add a bot to your application and copy the bot token.
    *   Invite the bot to your server with the necessary permissions.

4.  **Create a `.env` file:**

    *   Create a `.env` file in the project root.
    *   Add your bot token and developer ID:
DISCORD_BOT_TOKEN=your_bot_token_here
BOT_DEVELOPER_ID=your_discord_user_id_here
5.  **Run the bot:**
bash python bot.py

## Usage

Once the bot is running, you can interact with it using commands in your Discord server.

*   **Study Group Management:**
    *   `/create_group <group_name>`: Create a new study group.
    * `/make_permanent`: Make a temporary group permanent.
    * `/make_temporary`: Make a permanent group temporary.
    *   `/group_add_member <user_id>`: Add a member to the group.
    *   `/group_remove_member <user_id>`: Remove a member from the group.
    *   `/group_transfer_ownership <user_id>`: Transfer ownership to another member.
    * **Buttons**: Use the buttons to manage the group, leave the group, vote kick a member, mute/unmute, or to toggle the video.
*   **Pomodoro Sessions:**
    *   `/start_pomodoro`: Start a Pomodoro session.
    *   `/end_pomodoro`: End the Pomodoro session.
    * `/pause_pomodoro`: Pause the pomodoro.
    * `/resume_pomodoro`: Resume the pomodoro.
    * `/pomodoro_status`: Check the current status of the pomodoro.
*   **Check-in Sessions:**
    *   `/checkin`: Start a check-in session.
    * **Buttons**: Use the buttons to set yourself as present, absent or exited from the session.
* **Task management**:
    * `/add_task`: Add a new task.
    * `/list_tasks`: List the tasks.
    * `/complete_task`: Complete a task.
    * `/delete_task`: Delete a task.
* **Management**:
    * `/add_bot_developer`: Add a user as a bot developer.
    * `/add_guild_manager`: Add a user as a guild manager.
    * `/remove_guild_manager`: Remove a guild manager.
    * `/list_managers`: List all the managers of the guild.
    * `/set_permission_level`: Set the permissions of a user.

For a complete list of available commands, see the [COMMANDS.md](COMMANDS.md) file.

## Project Structure

*   `bot.py`: Main bot file that initializes and runs the bot.
*   `database.py`: Handles all database operations.
*   `utils.py`: Contains utility functions used across the bot.
*   `cogs/`:
    *   `__init__.py`: Initializes the cogs package.
    *   `checkin.py`: Implements check-in session functionality.
    *   `manager.py`: Handles permission management and bot administration.
    *   `pomodoro.py`: Implements Pomodoro session functionality.
    *   `study_groups.py`: Manages study group creation and operations.
    *   `tasklist.py`: Handles task management features.
    *   `voice_channels.py`: Manages dynamic voice channel creation and deletion.
* `docs/`:
    * `commands.md`: Contains the commands for the bot.
    * `readme.md`: Contains the project description and information.
    * `dev-log.md`: Contains the development logs of the project.

## Contributing

Contributions are welcome! If you'd like to contribute:

1.  Fork the repository.
2.  Create a new branch for your feature: `git checkout -b feature/YourAmazingFeature`.
3.  Commit your changes: `git commit -m 'Add some AmazingFeature'`.
4.  Push to your branch: `git push origin feature/YourAmazingFeature`.
5.  Open a Pull Request.

## Logging

The bot uses Python's built-in `logging` module for comprehensive logging across all components. Logs are useful for debugging and monitoring the bot's behavior.

## Acknowledgments

*   [Pycord](https://pycord.dev/)
*   [Discord.py](https://discordpy.readthedocs.io/en/stable/)
*   SQLite database
*   MongoDB database
* All the people who contributed to this project.

## Support

If you encounter any problems or have any questions, please open an issue on this repository. For more detailed information on usage and commands, refer to the [COMMANDS.md](COMMANDS.md) file.
