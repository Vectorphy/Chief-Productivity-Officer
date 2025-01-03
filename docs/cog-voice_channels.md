# Voice Channel Management Cog

This document describes the functionality of the  `voice_channels`  cog, which is responsible for managing voice channels related to study groups within the [Bot Name] Discord bot.

## Overview

The  `voice_channels`  cog automates the creation and deletion of voice channels for study groups, ensuring a clean and organized server. It provides commands for manually creating and deleting voice channels, and it also includes a listener that automatically deletes empty study group voice channels after a specified period of inactivity. This helps prevent clutter and makes it easier for users to find active study groups.

## Commands

### `/create_vc`

**Description:**  Creates a new voice channel for the study group. The channel is created within the same category as the study group's text channel and is given permissions that allow only study group members and bot managers to connect.

**Parameters:**

Parameter | Data Type | Required/Optional | Description | Example |
|--|--|--|--|--|
| `name` | `string` | Optional | The name of the voice channel. If not provided, the channel will be named "[Study Group Name] VC". | `My Study Group Voice` |

**Permissions:**

-   This command can only be used by the study group owner or a bot manager.

**Error Handling:**

-   If a voice channel already exists for the study group, the bot will return an error message.
-   If the bot does not have permission to create channels in the study group's category, it will return an error message.

**Examples:**

-   `/create_vc`  (creates a voice channel with the default name)
-   `/create_vc name:Discussion Room`

### `/delete_vc`

**Description:**  Deletes the voice channel associated with the study group.

**Parameters:**

-   This command does not take any parameters. The bot will automatically identify the voice channel associated with the study group based on the user's context (i.e., the study group they are currently in).

**Permissions:**

-   This command can only be used by the study group owner or a bot manager.

**Error Handling:**

-   If there is no voice channel associated with the study group, the bot will return an error message.
-   If the bot does not have permission to delete the voice channel, it will return an error message.

**Examples:**

-   `/delete_vc`

## Event Listeners

### `on_voice_state_update`

**Description:**  This listener monitors voice channel activity and automatically deletes empty study group voice channels after a specified period of inactivity.

**Logic:**

1.  **User Leaves Voice Channel:**  When a user leaves a voice channel, the listener checks if the channel is associated with a study group.
2.  **Empty Channel Check:**  If the channel is empty (no users connected) and belongs to a study group, a timer is started.
3.  **Inactivity Timeout:**  If the channel remains empty for the specified duration (configurable in the bot's settings, defaulting to 10 minutes), the channel is deleted.

**Benefits:**

-   **Automatic Cleanup:**  Keeps the server organized by removing unused voice channels.
-   **Resource Management:**  Frees up server resources by deleting inactive channels.
-   **Improved User Experience:**  Makes it easier for users to find active study groups.

## Internal Logic

The  `voice_channels`  cog uses a hybrid approach to manage voice channel information:

-   **In-Memory Cache:**  The cog stores the ID of the voice channel associated with each study group in memory for fast access. This allows the bot to quickly retrieve the voice channel ID without needing to query the database every time.
-   **Database Persistence:**  The cog uses the  `database.py`  module to store and retrieve voice channel IDs from the  `study_groups`  collection in the database. This ensures that the information is persistent and can be retrieved even if the bot restarts.

**Workflow:**

1.  **Study Group Creation:**  When a new study group is created, the  `voice_channels`  cog is notified and creates a new voice channel for the group. The voice channel ID is stored both in memory and in the database.
2.  **Voice Channel Usage:**  When a user joins or leaves a voice channel, the  `on_voice_state_update`  listener checks if the channel is associated with a study group and manages the inactivity timer accordingly.
3.  **Study Group Deletion:**  When a study group is deleted, the  `voice_channels`  cog is notified and deletes the associated voice channel. The voice channel ID is removed from both the in-memory cache and the database.

## Interaction with Other Cogs

The  `voice_channels`  cog primarily interacts with the  `study_groups`  cog:

-   **Study Group Creation:**  The  `study_groups`  cog calls a method in the  `voice_channels`  cog to create a new voice channel when a study group is created.
-   **Study Group Deletion:**  The  `study_groups`  cog calls a method in the  `voice_channels`  cog to delete the associated voice channel when a study group is deleted.
-   **Voice Channel Information:**  The  `study_groups`  cog can retrieve the voice channel ID associated with a study group from the  `voice_channels`  cog.

## Future Enhancements

-   **Customizable Channel Names:**  Allow study group creators to specify a custom name for their voice channel.
-   **Configurable Permissions:**  Allow study group creators to customize the permissions for their voice channel, such as allowing specific roles to connect or limiting the number of users who can join.
-   **Voice Activity Detection:**  Integrate with voice activity detection to automatically pause the inactivity timer when users are actively speaking in the voice channel.

## Documentation Updates

-   **Project Overview:**  Update the Project Overview document to include a more detailed description of the voice channel management feature.
-   **API Documentation:**  If you plan to expose APIs for managing voice channels, update the API documentation to include the relevant endpoints and methods.
-   **`study_groups.md`:**  Update the  `study_groups`  cog documentation to mention the interaction with the  `voice_channels`  cog for creating and deleting voice channels.

---