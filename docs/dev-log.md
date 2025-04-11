# Development Log - CPO Discord Bot

## 2024-01-14: Project Kickoff

**Title:** Initial Setup and Planning

**Summary:**
*   Created a new branch for the Pycord migration effort.
*   Reviewed the project's goals and overall structure.
*   Started outlining the development plan.
* Decided on the features we want to have on the bot.

**Decisions:**

*   The project will migrate to Pycord in the future.
* The database will be migrated to MongoDB.
* The database will use separate tables for Pomodoro sessions, Study Groups, group members and tasks.
* The database should have a robust design, and it should be easily expandable.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The current SQLite database structure should be able to be migrated to MongoDB.

**Refactoring Efforts:**

*   Refactoring the code to make the database operations more efficient.

**Open Questions/Future Considerations:**

*   Should we add any indexes to the database tables to improve performance?
*   How will we handle database migrations in the future?

## 2023-12-16: Study Group Cog Implementation

**Title:** Implementing the Study Group Cog.

**Summary:**
* Initial implementation of the study group cog.

**Challenges:**
*   Creating test cases that cover all the possible scenarios.
*   Mocking the database and discord interactions.
* Creating the logic for the pomodoro to end.

**Decisions:**
*   Use `AsyncMock` to mock asynchronous methods.
*   Use `patch` to mock classes and methods.
* The pomodoro should end when all of the users leave the voice channel.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The project is evolving well, and it is ready for migration to Pycord and MongoDB.

**Refactoring Efforts:**

*   Refactored the code to make it more testable.

**Open Questions/Future Considerations:**

*   What other edge cases should we test for?

## 2023-12-18: Study Group Persistence

**Title:** Implementing Study Group Persistence and Member/Manager Departure Handling

**Summary:**

*   Implemented Study Group persistence.
*   Implemented automatic manager transfer and deletion of temporary groups.

**Challenges:**

*   Handling various edge cases when members leave the group.
*   Ensuring data consistency in the database.

**Decisions:**

*   Use a boolean field to differentiate between permanent and temporary groups.
*   Implement automatic owner transfer for permanent groups.
*   Delete temporary groups when all members leave.
* The database will store the `is_permanent` data.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The code is being prepared for migration, but there is nothing to do yet.

**Refactoring Efforts:**

*   Refactored the `leave_group_callback` to handle various scenarios.
* Refactored code for better readability and organization.

**Open Questions/Future Considerations:**

*   How should we handle large numbers of study groups in the future?
*   Are there any other edge cases we haven't considered?

## 2024-01-17: Documentation and migration plans

**Title:** Updating the Documentation and assessing the migration plans

**Summary:**

* Updated the `docs/commands.md` file with the new commands.
* Updated the `docs/readme.md` file with all the information.
* Created the `docs/dev-log.md` file to track the project development.
* Conducted a code review.
* Conducted a database assessment.

**Challenges:**

*   Ensuring the documentation is accurate and comprehensive.
* Determining the feasibility of the migration plans.
* Making sure that the code is ready for migration.

**Decisions:**

*   Use the `docs/commands.md` file to document the bot commands.
*   Use the `docs/readme.md` to explain the project and how to use it.
* Use the `docs/dev-log.md` to track the development of the project.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
*   The code is being refactored to make the migration to Pycord easier.
* The current database design is suitable for a migration to MongoDB.
*   The performance of the current SQLite database is acceptable.

**Refactoring Efforts:**

*   Refactored the code to handle the new documentation files.
* Updated the code to make it easy to maintain.

**Open Questions/Future Considerations:**

*   Should we start the migration to pycord now, or should we wait?
*   Should we add indexes to the database to improve the performance?
*   Is there any new code that should be refactored?


---
## 2023-12-14: Project Kickoff and Initial Assessment

**Title:** Project Initialization and Core Feature Definition

**Summary:**

*   This log marks the beginning of a new development phase for the CPO (Chief Productivity Officer) Discord bot project. The primary goals are to assess the current state of the project, refactor existing code, expand its features, and eventually migrate to Pycord and MongoDB.
*   The project's main features were defined: Study Groups, Pomodoro Sessions, Check-In Sessions, Task Management, Dynamic Voice Channels, User Statistics, and Customizable Permissions.
*   Initial assessment of the project structure was made. Files such as `bot.py`, `database.py`, `main.py`, `utils.py`, and the cogs (`checkin.py`, `manager.py`, `pomodoro.py`, `study_groups.py`, `tasklist.py`, `voice_channels.py`) were identified.
*  The initial assessment found that the project had some features implemented, like the `checkin` cog, but most of them were either empty or incomplete.
* The initial plan was to expand the database, implement the pomodoro cog, implement the study groups cog, begin adding tests and updating the documentation.

**Challenges:**

*   Understanding the full scope of the project and the long-term goals.
*   Assessing the state of the existing codebase and identifying areas for improvement.

**Decisions:**

* The first step will be to expand the database.
* The second step will be to implement the study groups cog.
* The third step will be to implement the pomodoro cog.
* Create `test_file.py` and start adding test cases.
* Update the documentation files, `docs/commands.md` and `docs/readme.md`

**Progress Towards Pycord/MongoDB:**

*   Initial discussion about the intent to migrate to Pycord and MongoDB.
* No direct actions taken yet.

**Refactoring Efforts:**

*   Initial plan to refactor the code to make it more efficient and readable.
* A new `utils.py` file was created. The functions `parse_seconds_to_hms`, `parse_mentions` and `validate_group_parameters` were moved there.
* The database constants where added.
* The `on_command_error` event handler was updated.

**Open Questions/Future Considerations:**

*   What are the specific advantages of migrating to Pycord?
*   What are the benefits and drawbacks of using MongoDB over SQLite for this project?
*   What is the ideal database structure to handle all of the features of the bot?

## 2023-12-15: Database Expansion and `utils`

**Title:** Database Expansion and `utils.py` functions moved.

**Summary:**

*   Expanded the database structure to include data for Pomodoro sessions, Study Groups, group members, and task owners.
*   Created new tables: `pomodoro_sessions`, `study_groups`, and `group_members`.
*   Added a new column `owner_id` to the `tasks` table.
* Updated the database methods to handle the new tables and columns.
* The functions `parse_seconds_to_hms`, `parse_mentions` and `validate_group_parameters` were moved to the `utils.py` file.
* Test cases for the `utils.py` functions were created.
*  The error handling in the `main.py` file was improved.
* The decision was made to complete the study group cog, since it is one of the main features of the bot.

**Challenges:**

*   Designing an efficient database schema that can handle all of the project's features.
*   Ensuring existing database operations are not broken by the changes.
* Handling the changes in the files when moving the functions to the utils file.

**Decisions:**

*   The database will use separate tables for Pomodoro sessions, Study Groups, group members and tasks.
*  The database should have a robust design, and it should be easily expandable.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The current SQLite database structure should be able to be migrated to MongoDB.

**Refactoring Efforts:**

*   Refactoring the code to make the database operations more efficient.

**Open Questions/Future Considerations:**

*   Should we add any indexes to the database tables to improve performance?
*   How will we handle database migrations in the future?

## 2023-12-16: Study Group Cog Implementation

**Title:** Implementing the Study Group Cog.

**Summary:**

*   Implemented the core functionality of the Study Group cog in `study_groups.py`.
*   Implemented the `leave_group_callback`, `votekick_callback`, `speak_toggle_callback`, and `video_toggle_callback`.
*   Enhanced the `/create_group` command to check for duplicates.
*   Added management commands: `/group_add_member`, `/group_remove_member`, and `/group_transfer_ownership`.
* Added error handling and refactored the code.
* All the methods were updated to fit the new database structure.

**Challenges:**

*   Implementing the voting system for `votekick_callback`.
*   Managing the state of study groups (members, channels, roles, etc.).
* Creating the channels, roles and categories.
* Keeping the database and the bot data in sync.

**Decisions:**

*   Implement a basic voting system for `votekick_callback`.
*   Create a `StudyGroup` class to manage the state of study groups.
* The logic for the callbacks was implemented.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The project is evolving well, and it is ready for migration to Pycord and MongoDB.

**Refactoring Efforts:**

*   Refactored the code to make it more readable and efficient.

**Open Questions/Future Considerations:**

*   Should we add a more complex voting system?
*   How will we handle study groups that have been inactive for a long time?

## 2023-12-17: Testing Study Groups and Pomodoro auto end.

**Title:** Testing Study Groups and Pomodoro auto end.

**Summary:**

*   Wrote comprehensive tests for the new methods and commands in the `study_groups.py` cog.
*   Updated existing tests to fit the new code.
*   Modified the `run_timer` loop in `cogs/pomodoro.py` to automatically end a Pomodoro session when all members leave the voice channel.
* The code was refactored and error handling was improved.

**Challenges:**

*   Creating test cases that cover all the possible scenarios.
*   Mocking the database and discord interactions.
* Creating the logic for the pomodoro to end.

**Decisions:**

*   Use `AsyncMock` to mock asynchronous methods.
*   Use `patch` to mock classes and methods.
* The pomodoro should end when all of the users leave the voice channel.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The project is evolving well, and it is ready for migration to Pycord and MongoDB.

**Refactoring Efforts:**

*   Refactored the code to make it more testable.

**Open Questions/Future Considerations:**

*   What other edge cases should we test for?

## 2023-12-18: Study Group Persistence

**Title:** Implementing Study Group Persistence and Member/Manager Departure Handling

**Summary:**

*   Implemented a system to differentiate between temporary and permanent study groups.
*   Added the `/make_permanent` and `/make_temporary` commands.
*   Modified `/create_group` to create temporary groups by default.
*   Implemented logic to handle owner departure: If the owner of a permanent group leaves, transfer ownership to another member. If the owner of a temporary group leaves, remove the group.
*   Implemented logic to delete temporary groups if all members leave. If all members leave a permanent group, delete the channels but keep the group's data in the database.
*   Added a `is_permanent` column to the `study_groups` table.
*  Updated the database methods to handle the new changes.
* Updated the code to handle all the new cases, refactored the code, and improved the error handling.

**Challenges:**

*   Designing the temporary vs. permanent group system.
*   Handling the various scenarios when the owner or members leave.

**Decisions:**

*   By default, groups will be temporary.
*   The `/make_permanent` and `/make_temporary` commands will be used to change the group type.
* Only 5 permanent groups will be allowed per guild.
* The bot will be able to be the owner of a study group, if the owner leaves and there are no more members.
*  The study groups that are permanent will not be deleted, only the channels will be deleted.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The database design was updated to handle the new feature.
* The project is evolving well, and it is ready for migration to Pycord and MongoDB.

**Refactoring Efforts:**

*   Refactored the code to handle the new cases.

**Open Questions/Future Considerations:**

*   Should we add more commands to manage permanent groups?
* How should we handle the case when the bot is the owner and is removed from the guild?

## 2023-12-19: Assessing viability and Documentation

**Title:** Assessing viability of migration and documentation.

**Summary:**

* The plan was made to assess the code, the database and the bot to see if it is good enough for a migration.
* The code was reviewed, and the database was assessed.
* It was decided that the bot was well made, and well structured, and it is ready for a migration.
* The `/docs/commands.md` file was updated.
* The `/docs/readme.md` was created, and the original `readme.md` was copied there, updated, and rewritten.
* The `dev-log.md` was created.

**Challenges:**

* Assessing the code and database to see if it is ready for migration.
* Keeping the documentation up to date.

**Decisions:**

*   The bot will be migrated to Pycord and MongoDB.
* The `/docs/commands.md` will be the main file to see all of the commands.
* The `/docs/readme.md` will have all of the instructions, the usage, the installation, and more information about the project.
* The `dev-log.md` will have the log of all of the changes and decisions.

**Progress Towards Pycord/MongoDB:**

* The first steps towards the migration where made, and the viability was assessed.
* The bot, and the database are ready for migration.

**Refactoring Efforts:**

* The code was refactored and improved.

**Open Questions/Future Considerations:**

* What are the steps to migrate to Pycord and MongoDB?

## 2024-01-14: Project Kickoff

**Title:** Initial Setup and Planning

**Summary:**
*   Created a new branch for the Pycord migration effort.
*   Reviewed the project's goals and overall structure.
*   Started outlining the development plan.
* Decided on the features we want to have on the bot.

**Decisions:**

*   The project will migrate to Pycord in the future.
* The database will be migrated to MongoDB.
* The database will use separate tables for Pomodoro sessions, Study Groups, group members and tasks.
* The database should have a robust design, and it should be easily expandable.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The current SQLite database structure should be able to be migrated to MongoDB.

**Refactoring Efforts:**

*   Refactoring the code to make the database operations more efficient.

**Open Questions/Future Considerations:**

*   Should we add any indexes to the database tables to improve performance?
*   How will we handle database migrations in the future?

## 2023-12-16: Study Group Cog Implementation

**Title:** Implementing the Study Group Cog.

**Summary:**
* Initial implementation of the study group cog.

**Challenges:**
*   Creating test cases that cover all the possible scenarios.
*   Mocking the database and discord interactions.
* Creating the logic for the pomodoro to end.

**Decisions:**
*   Use `AsyncMock` to mock asynchronous methods.
*   Use `patch` to mock classes and methods.
* The pomodoro should end when all of the users leave the voice channel.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The project is evolving well, and it is ready for migration to Pycord and MongoDB.

**Refactoring Efforts:**

*   Refactored the code to make it more testable.

**Open Questions/Future Considerations:**

*   What other edge cases should we test for?

## 2023-12-18: Study Group Persistence

**Title:** Implementing Study Group Persistence and Member/Manager Departure Handling

**Summary:**

*   Implemented Study Group persistence.
*   Implemented automatic manager transfer and deletion of temporary groups.

**Challenges:**

*   Handling various edge cases when members leave the group.
*   Ensuring data consistency in the database.

**Decisions:**

*   Use a boolean field to differentiate between permanent and temporary groups.
*   Implement automatic owner transfer for permanent groups.
*   Delete temporary groups when all members leave.
* The database will store the `is_permanent` data.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
* The code is being prepared for migration, but there is nothing to do yet.

**Refactoring Efforts:**

*   Refactored the `leave_group_callback` to handle various scenarios.
* Refactored code for better readability and organization.

**Open Questions/Future Considerations:**

*   How should we handle large numbers of study groups in the future?
*   Are there any other edge cases we haven't considered?

## 2024-01-17: Documentation and migration plans

**Title:** Updating the Documentation and assessing the migration plans

**Summary:**

* Updated the `docs/commands.md` file with the new commands.
* Updated the `docs/readme.md` file with all the information.
* Created the `docs/dev-log.md` file to track the project development.
* Conducted a code review.
* Conducted a database assessment.

**Challenges:**

*   Ensuring the documentation is accurate and comprehensive.
* Determining the feasibility of the migration plans.
* Making sure that the code is ready for migration.

**Decisions:**

*   Use the `docs/commands.md` file to document the bot commands.
*   Use the `docs/readme.md` to explain the project and how to use it.
* Use the `docs/dev-log.md` to track the development of the project.

**Progress Towards Pycord/MongoDB:**

*   No direct actions taken yet.
*   The code is being refactored to make the migration to Pycord easier.
* The current database design is suitable for a migration to MongoDB.
*   The performance of the current SQLite database is acceptable.

**Refactoring Efforts:**

*   Refactored the code to handle the new documentation files.
* Updated the code to make it easy to maintain.

**Open Questions/Future Considerations:**

*   Should we start the migration to pycord now, or should we wait?
*   Should we add indexes to the database to improve the performance?
*   Is there any new code that should be refactored?

