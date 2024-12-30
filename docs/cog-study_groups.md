# Study Groups Cog

This document describes the functionality of the `study_groups` cog, which is responsible for managing study groups within the [Bot Name] Discord bot.

## Overview

The `study_groups` cog enables users to create and manage study groups on a Discord server. Each study group has its own dedicated text and voice channels, a role for its members, and a configurable session duration. The cog provides commands for creating, joining, leaving, managing, and ending study groups. This promotes focused collaboration and provides a structured environment for learning.

## Commands

The following slash commands are available for managing study groups:

### `/create_group`

**Description:** Creates a new study group with dedicated text and voice channels, a role for members, and a configurable session duration.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `name` | `string` | Required | The name of the study group. | `Calculus-101` |
| `category` | `discord.CategoryChannel` | Required | The category where the study group channels should be created. | `#Mathematics` |
| `max_members` | `int` | Optional (defaults to 10) | The maximum number of members allowed in the study group. | `20` |
| `mentions` | `user` or `role` mentions | Optional | Mentions of users or roles to initially add to the study group. | `@student-role`, `@user1 @user2` |

**Error Handling:**

- If a study group with the same name already exists in the specified category, the bot will return an error message.
- If the bot does not have permission to create channels in the specified category, it will return an error message.
- If the maximum number of members is invalid (e.g., less than 2), the bot will return an error message.

**Examples:**

- `/create_group name:Calculus-101 category:#Mathematics max_members:20 mentions:@student-role`
- `/create_group name:History-Study category:#Humanities mentions:@user1 @user2`

### `/join_group`

**Description:** Joins an existing study group.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group to join. | `Calculus-101` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the user is already a member of the study group, the bot will return an error message.

**Examples:**

- `/join_group group_name:Calculus-101`

### `/leave_group`

**Description:** Leaves a study group.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group to leave. | `Calculus-101` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the user is not a member of the study group, the bot will return an error message.

**Examples:**

- `/leave_group group_name:Calculus-101`

### `/manage_group`

**Description:** Manages various aspects of a study group.

**Permissions:** Only the study group owner or a bot manager can use this command.

**Subcommands:**

#### `/manage_group rename`

**Description:** Renames the study group.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The current name of the study group. | `Calculus-101` |
| `new_name` | `string` | Required | The new name for the study group. | `Calculus-I` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If a study group with the new name already exists in the same category, the bot will return an error message.

**Examples:**

- `/manage_group rename group_name:Calculus-101 new_name:Calculus-I`

#### `/manage_group extend`

**Description:** Extends the duration of the study group session.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group. | `Calculus-101` |
| `duration` | `string` | Required | The amount of time to extend the session (e.g., "1h", "30m"). | `1h` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the duration is invalid, the bot will return an error message.

**Examples:**

- `/manage_group extend group_name:Calculus-101 duration:1h`

#### `/manage_group transfer_ownership`

**Description:** Transfers ownership of the study group to another member.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group. | `Calculus-101` |
| `new_owner` | `discord.Member` | Required | The member to transfer ownership to. | `@user1` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the new owner is not a member of the study group, the bot will return an error message.

**Examples:**

- `/manage_group transfer_ownership group_name:Calculus-101 new_owner:@user1`

#### `/manage_group add_member`

**Description:** Adds a member to the study group.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group. | `Calculus-101` |
| `member` | `discord.Member` | Required | The member to add to the study group. | `@user3` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the member is already a member of the study group, the bot will return an error message.
- If the study group is full (reached its maximum number of members), the bot will return an error message.

**Examples:**

- `/manage_group add_member group_name:Calculus-101 member:@user3`

#### `/manage_group remove_member`

**Description:** Removes a member from the study group.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group. | `Calculus-101` |
| `member` | `discord.Member` | Required | The member to remove from the study group. | `@user2` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.
- If the member is not a member of the study group, the bot will return an error message.

**Examples:**

- `/manage_group remove_member group_name:Calculus-101 member:@user2`

### `/end_group`

**Description:** Ends a study group, deleting its associated channels and role.

**Permissions:** Only the study group owner or a bot manager can use this command.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|---|---|---|---|---|
| `group_name` | `string` | Required | The name of the study group to end. | `Calculus-101` |

**Error Handling:**

- If the study group does not exist, the bot will return an error message.

**Examples:**

- `/end_group group_name:Calculus-101`

## Event Listeners

### `on_voice_state_update`

**Description:** This listener monitors voice channel activity and automatically deletes empty study group voice channels after a specified period of inactivity. This helps keep the server clean and organized.

**Logic:**

- When a user leaves a voice channel, the listener checks if the channel is associated with a study group.
- If the channel is empty and belongs to a study group, a timer is started.
- If the channel remains empty for the specified duration (configurable in the bot's settings), the channel is deleted.

## Internal Logic

The `study_groups` cog uses a combination of in-memory data structures and database interactions to manage study group information. 

- **In-Memory Storage:**  The cog stores active study group data in a dictionary (`self.study_groups`) for fast access. Each key in the dictionary is the study group's unique ID, and the value is a `StudyGroup` object containing the group's data.
- **Database Persistence:**  The cog uses the `database.py` module to interact with the MongoDB database, ensuring that study group data is persistent and can be retrieved even if the bot restarts. The `StudyGroup` object's data is loaded from the database when the bot starts and saved to the database whenever changes are made.

**Data Structures:**

- `StudyGroup` object: Represents a study group and contains the following attributes:
    - `guild_id`: The ID of the Discord guild.
    - `name`: The name of the study group.
    - `group_id`: A unique ID for the study group.
    - `creator_id`: The ID of the user who created the group.
    - `owner_id`: The ID of the user who is the current owner of the group.
    - `category_id`: The ID of the category where the group's channels are located.
    - `max_members`: The maximum number of members allowed in the group.
    - `member_ids`: A list of member IDs.
    - `group_role_id`: The ID of the role assigned to group members.
    - `text_id`: The ID of the text channel.
    - `vc_id`: The ID of the voice channel.
    - `info_embed_id`: The ID of the message containing the group info embed.
    - `start_time`: The time the group was created.
    - `duration`: The duration of the study session.
    - `end_time`: The time the study session is scheduled to end.
    - `speak_enabled`: Whether speaking is enabled in the voice channel.
    - `video_mode`: The video mode for the voice channel.
    - `video_timer`: The timer for forcing video to be on.
    - `active`: Whether the group is currently active.

**Database Interactions:**

- The `database.py` module provides methods for:
    - Saving a new study group to the database.
    - Updating an existing study group in the database.
    - Retrieving a study group from the database by its ID.
    - Deleting a study group from the database.

## Interaction with Other Cogs

The `study_groups` cog interacts with the following cogs:

- `voice_channels`:  The `study_groups` cog relies on the `voice_channels` cog to create and delete voice channels for study groups. When a study group is created, the `study_groups` cog calls a method in the `voice_channels` cog to create a new voice channel for the group. When a study group is ended, the `study_groups` cog calls a method in the `voice_channels` cog to delete the group's voice channel.
- `manager`:  The `study_groups` cog uses the `manager` cog to check user permissions and enforce restrictions on certain commands. For example, before allowing a user to end a study group, the `study_groups` cog checks if the user has the necessary permissions by calling a method in the `manager` cog.

## User Roles and Permissions

- **Study Group Owner:** The user who created the study group is the owner and has full control over the group's settings and members.
- **Study Group Member:** Members can participate in the study group's activities, but they cannot modify the group's settings or manage other members.
- **Bot Manager:** Bot managers have elevated permissions and can manage all study groups on the server, regardless of ownership.

## Configuration and Settings

- **Default Settings:**
    - Maximum Members: 10
    - Session Duration: 12 hours
    - Voice Channel Inactivity Timeout: 10 minutes
- **Customization Options:** Study group owners can customize the group's name, maximum members, and session duration using the `/manage_group` command.

## Examples and Use Cases

- **Online Classes:** Students in an online class can create a study group to discuss course material, work on assignments together, and prepare for exams.
- **Exam Preparation:** Students preparing for an exam can create a study group to quiz each other, share study resources, and motivate each other.
- **Collaborative Projects:** Students working on a group project can create a study group to coordinate their efforts, share ideas, and work on the project together.

## Troubleshooting

- **Common Issues:**
    - **"Study group not found":** Make sure you are using the correct study group name.
    - **"You do not have permission to use this command":** Only the study group owner or a bot manager can use certain commands.
    - **"The study group is full":** The study group has reached its maximum number of members.
- **Support Channels:** If you encounter any issues or have questions, please join our support server [link to support server] or contact us at [support email address].

## Future Enhancements

- **Customizable Notification Preferences:** Allow study group members to customize their notification settings for check-ins, reminders, and other events.
- **Integration with Google Calendar:** Enable users to schedule study group sessions and sync them with their Google Calendars.
- **Task Management Integration:** Integrate with a task management tool like Trello to allow study groups to manage their tasks and assignments collaboratively.

## Documentation Updates

- **Project Overview:** Update the Project Overview document to include a more detailed description of the study groups feature.
- **API Documentation:** If you plan to expose APIs for managing study groups, update the API documentation to include the relevant endpoints and methods.

## --- ### --- ##

# Study Groups Cog

This document describes the functionality of the `study_groups` cog, which is responsible for managing study groups within the [Bot Name] Discord bot.

## Overview

The `study_groups` cog enables users to create and manage study groups on a Discord server. Each study group has its own dedicated text and voice channels, a role for its members, and a configurable session duration. The cog provides commands for creating, joining, leaving, managing, and ending study groups. This promotes focused collaboration and provides a structured environment for learning.

## Commands

The following slash commands are available for managing study groups:

### `/create_group`

**Description:** Creates a new study group with dedicated text and voice channels, a role for members, and a configurable session duration.

**Parameters:**

- `name`: The name of the study group (required).
- `category`: The category where the study group channels should be created (required).
- `max_members`: The maximum number of members allowed in the study group (optional, defaults to 10).
- `mentions`:  Mentions of users or roles to initially add to the study group (optional).

**Examples:**

- `/create_group name:Calculus-101 category:Mathematics max_members:20 mentions:@student-role`
- `/create_group name:History-Study category:Humanities mentions:@user1 @user2`

### `/join_group`

**Description:** Joins an existing study group.

**Parameters:**

- `group_name`: The name of the study group to join (required).

**Examples:**

- `/join_group group_name:Calculus-101`

### `/leave_group`

**Description:** Leaves a study group.

**Parameters:**

- `group_name`: The name of the study group to leave (required).

**Examples:**

- `/leave_group group_name:Calculus-101`

### `/manage_group`

**Description:** Manages various aspects of a study group.

**Subcommands:**

- `/manage_group rename new_name`: Renames the study group.
- `/manage_group extend duration`: Extends the duration of the study group session.
- `/manage_group transfer_ownership new_owner`: Transfers ownership of the study group to another member.
- `/manage_group add_member member`: Adds a member to the study group.
- `/manage_group remove_member member`: Removes a member from the study group.

**[Note: We'll provide more details on the parameters and examples for each subcommand later.]**

### `/end_group`

**Description:** Ends a study group, deleting its associated channels and role.

**Parameters:**

- `group_name`: The name of the study group to end (required).

**Examples:**

- `/end_group group_name:Calculus-101`

## Event Listeners

### `on_voice_state_update`

**Description:** This listener monitors voice channel activity and automatically deletes empty study group voice channels after a specified period of inactivity. This helps keep the server clean and organized.

**Logic:**

- When a user leaves a voice channel, the listener checks if the channel is associated with a study group.
- If the channel is empty and belongs to a study group, a timer is started.
- If the channel remains empty for the specified duration (configurable in the bot's settings), the channel is deleted.

## Internal Logic

The `study_groups` cog uses a combination of in-memory data structures and database interactions to manage study group information. 

- **In-Memory Storage:**  The cog stores active study group data in a dictionary (`self.study_groups`) for fast access. Each key in the dictionary is the study group's unique ID, and the value is a `StudyGroup` object containing the group's data.
- **Database Persistence:**  The cog uses the `database.py` module to interact with the MongoDB database, ensuring that study group data is persistent and can be retrieved even if the bot restarts. The `StudyGroup` object's data is loaded from the database when the bot starts and saved to the database whenever changes are made.

**Data Structures:**

- `StudyGroup` object: Represents a study group and contains the following attributes:
    - `guild_id`: The ID of the Discord guild.
    - `name`: The name of the study group.
    - `group_id`: A unique ID for the study group.
    - `creator_id`: The ID of the user who created the group.
    - `owner_id`: The ID of the user who is the current owner of the group.
    - `category_id`: The ID of the category where the group's channels are located.
    - `max_members`: The maximum number of members allowed in the group.
    - `member_ids`: A list of member IDs.
    - `group_role_id`: The ID of the role assigned to group members.
    - `text_id`: The ID of the text channel.
    - `vc_id`: The ID of the voice channel.
    - `info_embed_id`: The ID of the message containing the group info embed.
    - `start_time`: The time the group was created.
    - `duration`: The duration of the study session.
    - `end_time`: The time the study session is scheduled to end.
    - `speak_enabled`: Whether speaking is enabled in the voice channel.
    - `video_mode`: The video mode for the voice channel.
    - `video_timer`: The timer for forcing video to be on.
    - `active`: Whether the group is currently active.

**Database Interactions:**

- The `database.py` module provides methods for:
    - Saving a new study group to the database.
    - Updating an existing study group in the database.
    - Retrieving a study group from the database by its ID.
    - Deleting a study group from the database.

## Interaction with Other Cogs

The `study_groups` cog interacts with the following cogs:

- `voice_channels`:  The `study_groups` cog relies on the `voice_channels` cog to create and delete voice channels for study groups. When a study group is created, the `study_groups` cog calls a method in the `voice_channels` cog to create a new voice channel for the group. When a study group is ended, the `study_groups` cog calls a method in the `voice_channels` cog to delete the group's voice channel.
- `manager`:  The `study_groups` cog uses the `manager` cog to check user permissions and enforce restrictions on certain commands. For example, before allowing a user to end a study group, the `study_groups` cog checks if the user has the necessary permissions by calling a method in the `manager` cog.

## Future Enhancements

- **Customizable Settings:** Allow study group creators to customize more settings, such as the default video mode for the voice channel, notification preferences, and the inactivity timeout for voice channel deletion.
- **Integration with Other Services:** Explore integrating with external services like Google Calendar or Trello to enhance study group scheduling and task management.
- **Improved User Interfaces:**  Consider using more interactive elements, such as buttons and select menus, to make it easier for users to manage their study groups.

---
