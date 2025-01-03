# Pomodoro Cog

This document describes the functionality of the  `pomodoro`  cog, which provides a Pomodoro timer feature within the [Bot Name] Discord bot.

## Overview

The  `pomodoro`  cog enables users to start, pause, resume, and end Pomodoro sessions. It uses a timer to guide users through intervals of focused work and short breaks, helping them stay on track and maintain productivity. The cog can send notifications to remind users when to switch between work and break periods. This technique is especially beneficial for study groups, allowing members to synchronize their work and break times for a more collaborative and focused study session.

## Commands

The following slash commands are available for managing Pomodoro sessions:

### `/start_pomodoro`

**Description:**  Starts a new Pomodoro session with customizable focus, short break, and long break durations.

**Parameters:**

| Parameter | Data Type | Required/Optional | Description | Example |
|--|--|--|--|--|
| `focus` | `int` | Optional (defaults to 25) | The duration of the focus period in minutes. | `30` |
| `short_break` | `int` | Optional (defaults to 5) | The duration of the short break period in minutes. | `10` |
| `long_break` | `int` | Optional (defaults to 15) | The duration of the long break period in minutes. | `20` |

**Error Handling:**

-   If a Pomodoro session is already running for the user's study group, the bot will return an error message.
-   If the user is not in a voice channel, the bot will prompt them to join one.

**Examples:**

-   `/start_pomodoro`  (starts a session with default durations)
-   `/start_pomodoro focus:30 short_break:10 long_break:20`

### `/pause_pomodoro`

**Description:**  Pauses the current Pomodoro session.

**Error Handling:**

-   If there is no active Pomodoro session, the bot will return an error message.

**Examples:**

-   `/pause_pomodoro`

### `/resume_pomodoro`

**Description:**  Resumes a paused Pomodoro session.

**Error Handling:**

-   If there is no active Pomodoro session or the session is not paused, the bot will return an error message.

**Examples:**

-   `/resume_pomodoro`

### `/end_pomodoro`

**Description:**  Ends the current Pomodoro session.

**Error Handling:**

-   If there is no active Pomodoro session, the bot will return an error message.

**Examples:**

-   `/end_pomodoro`

### `/pomodoro_status`

**Description:**  Displays the current status of the Pomodoro session, including the current stage, time remaining, and completed cycles.

**Error Handling:**

-   If there is no active Pomodoro session, the bot will return an error message.

**Examples:**

-   `/pomodoro_status`

## Event Listeners

The  `pomodoro`  cog does not currently use any event listeners. However, you could consider adding event listeners for events like:

-   `on_voice_state_update`: To automatically pause the Pomodoro timer if all members leave the study group's voice channel.
-   `on_member_join`: To send a welcome message to new members joining the study group during a Pomodoro session.

## Internal Logic

The  `pomodoro`  cog uses a timer and in-memory data structures to track Pomodoro sessions. It stores the following information for each active session:

-   `group_id`: The ID of the study group (if applicable).
-   `focus_duration`: The duration of the focus period in minutes.
-   `short_break_duration`: The duration of the short break period in minutes.
-   `long_break_duration`: The duration of the long break period in minutes.
-   `current_stage`: The current stage of the session ("focus", "short_break", or "long_break").
-   `cycles`: The number of completed cycles.
-   `is_paused`: Whether the session is currently paused.
-   `timer`: The remaining time in the current stage in seconds.

**Timer Logic:**

-   The cog uses a  `tasks.loop`  from  `discord.ext.tasks`  to decrement the timer every second.
-   When the timer reaches zero, the cog:
    -   Increments the cycle count.
    -   Switches to the next stage (e.g., from "focus" to "short_break").
    -   Resets the timer based on the duration of the new stage.
    -   Sends a notification to the study group's voice channel (if applicable) announcing the stage change.

## Interaction with Other Cogs

The  `pomodoro`  cog can interact with other cogs, such as:

-   `study_groups`: Pomodoro sessions can be started within study groups, allowing members to participate together. The cog retrieves the study group's voice channel ID from the  `study_groups`  cog to send notifications.
-   `voice_channels`: The cog can send notifications to the study group's voice channel to remind members when to switch between work and break periods.
-   `checkin`: Check-ins could be triggered at the start or end of Pomodoro sessions to track participation. For example, the  `pomodoro`  cog could call a method in the  `checkin`  cog to automatically mark members as present at the start of a session.

## Future Enhancements

-   **Customizable Intervals:**  Allow users to customize the durations of the focus, short break, and long break periods.
-   **Visual Progress Indicators:**  Use Discord embeds to display a visual progress bar or timer for the current Pomodoro session.
-   **Integration with Other Productivity Tools:**  Explore integrating with other productivity tools, such as task management apps or time tracking software.
-   **Sound Notifications:**  Allow users to enable sound notifications for stage changes.
-   **Multiple Concurrent Sessions:**  Disallow users and Allow managers to run multiple Pomodoro sessions simultaneously.

## Documentation Updates

-   **Project Overview:**  Update the Project Overview document to include a more detailed description of the Pomodoro timer feature.
-   **API Documentation:**  If you plan to expose APIs for managing Pomodoro sessions, update the API documentation to include the relevant endpoints and methods.
-   **Cog-Specific Documentation:**  Update the documentation for other cogs that might interact with the  `pomodoro`  cog, such as  `study_groups`,  `voice_channels`, and  `checkin`.
