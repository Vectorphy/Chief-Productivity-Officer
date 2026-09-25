# Changelog

All notable changes to the **Chief Productivity Officer (CPO)** Discord Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Migration of synchronous SQLite queries in `database.py` to `aiosqlite`.
- Periodic database snapshot and backup routine.

---

## [1.0.0-rc.1] - 2026-09-25

### Added
- **GitHub Workflows & Automated Packaging Infrastructure**:
  - Added [`.github/workflows/ci.yml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.github/workflows/ci.yml) providing multi-version Python testing matrix (3.10, 3.11, 3.12) with automated static typing (`mypy`), linting (`ruff check`), formatting validation (`ruff format`), and test coverage reporting (`pytest`).
  - Added [`.github/workflows/prerelease.yml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.github/workflows/prerelease.yml) automating wheel (`.whl`) and source distribution (`.tar.gz`) packaging via `python -m build` and deploying GitHub Prereleases on `v*` tag pushes or manual `workflow_dispatch`.
  - Configured `[tool.setuptools]` and `[tool.setuptools.packages.find]` in [`pyproject.toml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/pyproject.toml) to support standard wheel/sdist distribution generation.
  - Removed outdated legacy workflows (`workflows/python-app.yml` and `.github/workflows/python-app.yml`).
- **Autonomous Governance & Agentic Architecture Framework**:
  - Overhauled [`AGENTS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/AGENTS.md) with copy-pasteable toolchain directives (install, dev, build, lint, test, format), strict Three-Tier Guardrails (Always Do, Ask First, Never Do), architectural invariants, offline test mocking patterns, and the mandatory Agent Operating Contract.
  - Refreshed [`KNOWLEDGE_GRAPH.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWLEDGE_GRAPH.md) detailing directory topology, component boundaries, execution lifecycles (slash commands & background standup loops), SQLite ER schema, and state invariants.
  - Established [`KNOWN_ISSUES.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWN_ISSUES.md) tracking active defects, architectural debt (such as blocking SQLite calls and high cyclomatic complexity), and security/reliability hazards.
  - Established [`TODO.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/TODO.md) organizing all audit findings into prioritized engineering tiers (P0, P1, P2, and Backlog).
- **On-Demand Single Slash Command Sync (`/sync_commands`)**:
  - Added dedicated `/sync_commands [guild_only: bool = False]` slash command in [`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py) allowing Administrators and Bot Developers to trigger immediate application command synchronization (either globally across all guilds or scoped strictly to the current guild).
- **Admin Command Invisibility for Non-Admins (`default_permissions`)**:
  - Implemented Discord native `@app_commands.default_permissions(...)` on all administrative and management commands so that they are completely invisible to regular non-admin/non-mod users in Discord's slash command picker:
    - `administrator=True`: `/sync_commands`, `/sync_managers`, `/add_bot_developer`, `/add_guild_manager`, `/remove_guild_manager`, `/set_permission_level`, `/settings_checkin`.
    - `manage_guild=True`: `/list_managers`.
    - `manage_channels=True`: `/delete_vc`, `/delete_text_channel`.
    - `manage_roles=True`: `/delete_role`.
- **Three-Tier User Level Hierarchy (`User`, `Mod`, `Admin`)**:
  - Formalized a clear 3-tier authorization model across permission checks, database queries, and UI inspection:
    - **`Admin`** (Levels 3 & 4): Bot Developer (`BOT_DEVELOPER`), Server Owner (`owner_id`), Server Administrator (`perms.administrator`).
    - **`Mod`** (Level 2): Members with `manage_guild`, `manage_channels`, `manage_roles`, `moderate_members`, `kick_members`, `ban_members`, staff role names, or registered in DB as `MODERATOR`.
    - **`User`** (Levels 0 & 1): Baseline members (`REGULAR_USER`) and group participants (`GROUP_MEMBER`).
  - Added `/user_level [user]` command allowing any server member to inspect their own or another user's authorization tier (`Admin`, `Mod`, `User`) and numeric permission level with rich embed styling.
  - Updated `utils.py:check_manager` to grant management and moderation access to database managers with `permission_level >= 2` (`MODERATOR`).
- **Comprehensive 54-Test End-to-End Test Matrix**:
  - Expanded [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py) to 54 exhaustive test flows, covering `/sync_commands` (global/guild/unauthorized), `/user_level` (Admin, Mod, User), tier mapping logic, slash command `default_permissions` visibility verification, and unauthorized rejection on `/settings_checkin`. All 54 tests pass with 100% success.
- **Interactive Group Transfer Dashboard & Slash Command**: Added a dedicated `Transfer Group` button (`🔄`) with an interactive `discord.ui.UserSelect` modal view on the study group dashboard, and registered a `/transfer_group` slash command in [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py).
- **Study Group Slash Commands**: Added `/end_group` slash command in `StudyGroupCog` allowing group creators, owners, and server managers to cleanly close sessions and clean up Discord channels/roles.
- **Channel-Aware Database Lookup**: Added `get_study_group_by_channel` to `DBHandler` in [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py) to resolve active study groups directly from text or voice channel context.
- **Instant Guild Slash Command Propagation**: Added per-guild tree synchronization in [`bot.py:on_ready`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot.py) (`copy_global_to` + `sync(guild=guild)`), eliminating Discord's 1-hour global cache propagation delay.
- Created [`.python-version`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.python-version) setting Python 3.12 as the project default.
- Created [`.vscode/settings.json`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.vscode/settings.json) mapping IDE default interpreter path to `.venv/Scripts/python.exe`.
- Strict typing and type annotations across all project modules (`database.py`, `utils.py`, `cogs/manager.py`, `cogs/pomodoro.py`, `cogs/voice_channels.py`, `cogs/study_groups.py`, `cogs/checkin.py`).

### Changed
- **Permissions Hierarchy Overhaul**:
  - Upgraded `utils.py:check_manager` and `cogs/manager.py:get_permission_level` to natively grant `GUILD_MANAGER` authority to Server Owners (`user.id == guild.owner_id`), server members with moderation permissions (`administrator`, `manage_guild`, `manage_channels`, `manage_roles`, `moderate_members`, `kick_members`, `ban_members`), and members with moderator-style role names.
  - Upgraded `utils.py:is_group_creator`, `StudyGroup.can_control`, and `CheckinGuildSettings.is_owner` to permit server owners and moderators to manage all study groups and check-in sessions.
  - Added safe `.get()` defaults in `database.py:save_study_group` to prevent `KeyError` exceptions when creating or migrating study groups.

### Fixed
- **Repository Hygiene & Static Analysis Traps (Architect Audit)**:
  - Fixed `.gitignore` corrupted wildcard spacing (`* . s q l i t e` -> `*.sqlite` and `scratch_*.py`), which caused Git to treat `*` as a global ignore wildcard and blinded version control to all newly created governance and test files.
  - Resolved Mypy static type errors in [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py) (`_get_session` argument type signature) and [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py) (`text_id` attribute lookup), restoring 100% clean type check status (0 errors across 16 files).
  - Resolved unawaited coroutine mock RuntimeWarnings in [`tests/test_new_features.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_new_features.py) by assigning `MagicMock(return_value=False)` to synchronous `interaction.response.is_done`.
  - Pruned unused imports in [`cogs/tasklist.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/tasklist.py) and [`cogs/voice_channels.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/voice_channels.py), and removed trailing whitespace in multiline SQL execution blocks in [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py).
- **Duplicate Slash Commands in Discord UI**:
  - Resolved duplicate slash command entries (`/create_group`, `/create_vc`, `/delete_role`, etc. appearing twice in Discord) caused by simultaneous global command sync (`tree.sync()`) and guild command copying (`copy_global_to()`).
  - Updated [`bot.py:on_ready`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot.py) to execute `tree.clear_commands(guild=guild)` and sync empty guild trees, eliminating guild-scoped duplicates so that only uniquely registered global commands appear in Discord clients.
- **Pomodoro Status Timeout ("The application did not respond")**:
  - Added early interaction deferral in [`cogs/pomodoro.py:pomodoro_status`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py) and across all pomodoro lifecycle commands (`start_pomodoro`, `end_pomodoro`, `pause_pomodoro`, `resume_pomodoro`).
  - Added `_resolve_group` in `Pomodoro` cog to seamlessly detect sessions via user membership, active channel, or server-wide fallback for server owners and moderators.
- **Group Transfer & Lifecycle Locks**:
  - Fixed issue where group owners were locked out of transferring study groups or sessions.
  - Enforced permission validation on study group dashboard callbacks (`end_group_callback`, `rename_group_callback`, `extend_duration_callback`, `transfer_group_callback`).
- **Check-in Session Management by Staff**:
  - Updated `cogs/checkin.py` (`change_owner_callback`, `end_session_callback`, `can_end`) to grant full administrative override to server owners and moderators.

### Changed
- Verified and installed all production and development dependencies from [`requirements-dev.txt`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/requirements-dev.txt) into the Python 3.12 virtual environment.
- Converted class-level permission and validation decorators in `cogs/manager.py` and `cogs/checkin.py` to `@staticmethod` with explicit typing.
- Updated `View` disabling routines to safely construct views from message payloads using `View.from_message`.

### Fixed
- **UI & Message Formatting**:
  - Formatted raw Unix timestamp in [`cogs/study_groups.py:extend_duration_callback`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py) to use Discord timestamp tags `<t:{end_timestamp}:F> (<t:{end_timestamp}:R>)` instead of printing raw epoch floats.
- **Resolved Discord "The application did not respond" & Interaction Responded Failures**:
  - Global `on_app_command_error` in [`bot.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot.py) now unwraps `error.original`, handles `CheckFailure` with user-friendly messages, and safely catches `discord.InteractionResponded` to fall back to `interaction.followup.send`.
  - Fixed button callbacks in [`cogs/checkin.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/checkin.py) (`mark_present_callback`, `start_break_callback`, `leave_session_callback`, `new_owner_callback`) to use `interaction.followup.send` after deferral rather than attempting secondary `send_message` calls.
  - Implemented dual-path response handling (`is_done()` branching with `send_message` / `followup.send`) across [`cogs/voice_channels.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/voice_channels.py), [`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py), and [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py).
- **Startup & Pre-Login Stability**:
  - Replaced `bot.fetch_guild()` with `bot.get_guild()` in `cogs/checkin.py:load_active_sessions_from_db` to avoid `_MissingSentinel` gateway lock crashes prior to bot connection.
- **Database & Parameter Binding**:
  - Sanitized `MemberStatus` enum binding in `database.py:add_or_update_checkin_member` using `.value` / `str()` extraction, fixing `sqlite3.InterfaceError: Error binding parameter 3: type 'MemberStatus' is not supported`.
- **Validation & Mentions**:
  - Upgraded `utils.py:parse_mentions` to use robust regular expression extraction (`<@&(\d+)>`, `<@!?(\d+)>`), resolving `ValueError` on comma-separated or mixed mention strings.
  - Updated category channel validation in `utils.py:validate_parameters` to match against channel snowflake IDs rather than object identity.
- **Concurrency & Permission Architecture**:
  - Refactored `cogs/pomodoro.py:run_timer` loop from a parameterized singleton to an in-memory session iterator, eliminating `RuntimeError: Task is already launched`.
  - Removed conflicting stacked `@app_is_manager()` check on `cogs/voice_channels.py` commands while granting bot developers and guild managers transparent access via `utils.py:is_group_creator`.
  - Added auto-initialization of default `CheckinGuildSettings` on unconfigured servers in `cogs/checkin.py:checkin_command_permissions`, preventing false-positive permission denials.
- **Resolved all 220 `mypy` static type checking errors** across all 16 repository source files (`mypy .` now reports 0 errors).
- Fixed latent `AttributeError` in `cogs/study_groups.py` where `StudyGroup` accessed non-existent `self.study_group.name` instead of `self.name`.
- Fixed invalid `await self.disable_buttons()` invocation on a synchronous method in `cogs/study_groups.py`.
- Fixed raw `Component` item additions to `discord.ui.View` during reminder and session cleanup.
- Fixed parameter type discrepancy between `utils.parse_mentions` and `utils.validate_parameters`.
- Fixed button type definitions replacing raw `discord.Button` with `discord.ui.Button[Any]`.
- **Database & SQL Schema Alignment**:
  - Fixed `update_group_roles` and `get_group_roles` in `database.py` referencing non-existent `admin_role_id`/`session_role_id` columns; mapped to `group_role_id`.
  - Fixed `update_voice_channel` in `database.py` referencing non-existent `voice_channel_id` column; mapped to `vc_id`.
  - Fixed `get_vc_logs` ambiguous `creator_id` column by prefixing with table qualifier `study_groups.creator_id`.
  - Implemented missing `get_study_group(guild_id: int)` in `database.py`.
  - Made `save_study_group` idempotent using `INSERT OR REPLACE INTO study_groups`.
  - Sanitized `last_reminder_message_id` parameter binding in `database.py:update_checkin_session`.
  - Upgraded `get_user_group` in `database.py` to support `text_id`, `vc_id`, and active-group fallbacks.
- **Permission & Access Control**:
  - Converted `PermissionLevel` in `cogs/manager.py` to `IntEnum` for robust integer comparisons and SQLite parameter binding.
  - Aligned `/set_permission_level` with 5-tier architecture (0: Regular User, 1: Group Member, 2: Group Owner, 3: Guild Manager, 4: Bot Developer).
  - Fixed `utils.py:is_group_creator` which mistakenly compared `group[2]` (name string) instead of `creator_id`.
  - Added superuser bypass for `bot_developer_id` in `utils.py:check_manager` and `is_group_creator`.
- **Voice Channels & Pomodoro**:
  - Fixed `cogs/voice_channels.py` brittle tuple index access by switching to dictionary keys (`vc_id`, `group_role_id`, `text_id`).
  - Fixed `cogs/voice_channels.py:delete_text_channel` erroneously calling `update_voice_channel`.
  - Initialized `PomodoroSession.timer = focus * 60` and safeguarded `timedelta` calculation in `cogs/pomodoro.py:pomodoro_status`.
- **Event Loop & Startup**:
  - Replaced deprecated `bot.loop.create_task` in `cogs/checkin.py` and `cogs/study_groups.py` with `asyncio.create_task` and added `cog_load()` hooks.
  - Fixed `cogs/checkin.py:load_active_sessions_from_db` attempting to read `'text_channel_id'` instead of `'text_id'` from SQLite.
  - Replaced blocking `await asyncio.sleep` in `load_active_sessions_from_db` with a non-blocking background task wrapper.
  - Streamlined `bot.py` command registration: removed redundant `tree.sync()` inside `on_ready()` to prevent connection-time Discord API rate limits.
- **End-to-End Test Suite**:
  - Implemented [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py) to simulate dummy requests under server `885134444992806962` and user `534168986149978112` for all 16 slash commands and interactive button callbacks with rate limit safety.

### Planned
- MongoDB aggregation pipeline for global cross-guild analytics.
- Voice channel auto-deafening during Pomodoro deep focus intervals.
- Webhook alert integrations for study group milestones.

---

## [1.0.0] - 2026-09-04

### Added
- **AI Agent Readiness & Autonomous Tooling**:
  - Created [`AGENTS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/AGENTS.md) with detailed conventions, async SQLite rules, and offline mock testing patterns.
  - Created [`GEMINI.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/GEMINI.md) and [`.agents/rules/cpo_development_rules.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.agents/rules/cpo_development_rules.md) establishing agent constraints and workflows.
  - Created [`docs/LOGGING_STANDARDS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/docs/LOGGING_STANDARDS.md) mandating structured logging and audit standards across all modules.
- **System Architecture & Visual Documentation**:
  - Created comprehensive [`ARCHITECTURE.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/ARCHITECTURE.md) with C4 Container Diagrams, State Machines, Data Pipelines, and Security Maps.
  - Created [`KNOWLEDGE_GRAPH.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWLEDGE_GRAPH.md) documenting system nodes, database entity relationships, and command mappings.
  - Created machine-readable [`knowledge_graph.json`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/knowledge_graph.json) for LLM and RAG indexing.
- **Packaging & Testing Infrastructure**:
  - Added [`pyproject.toml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/pyproject.toml) supporting `pytest`, `pytest-asyncio`, `ruff`, and `mypy`.
  - Added [`requirements-dev.txt`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/requirements-dev.txt) for testing and code quality tools.
  - Added [`.env.example`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.env.example) configuration template.
  - Added unit test suites in [`tests/`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/):
    - [`test_database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_database.py) (In-memory SQLite CRUD and concurrency tests)
    - [`test_utils.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_utils.py) (Duration parsers, time formatting, and productivity calculations)
    - [`test_tasklist.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_tasklist.py) (Mock interaction tests for task addition and completion)
- **Core Bot Cogs & Feature Modules**:
  - `CheckinCog` ([`cogs/checkin.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/checkin.py)): Automated standup check-in loops, status tracking buttons (`Present`, `Break`, `Exit`), and strike counts.
  - `StudyGroupCog` ([`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py)): Study group lifecycle, category creation, role binding, capacity management.
  - `Pomodoro` ([`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py)): Focus and break state machines with voice channel routing.
  - `Manager` ([`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py)): 5-tier permission hierarchy and session limit enforcement.
  - `TaskList` ([`cogs/tasklist.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/tasklist.py)): Personal to-do list tracking.
  - `ProductivityTracker` ([`cogs/productivity_tracker.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/productivity_tracker.py)): Metric calculations and embed views.
  - `VoiceChannels` ([`cogs/voice_channels.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/voice_channels.py)): Temporary voice channel lifecycle management.

### Changed
- Cleaned [`requirements.txt`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/requirements.txt) by removing duplicate packages and invalid standard library entries (`asyncio`, `datetime`).

---

### Agent Protocol for Updating This Changelog
Whenever you modify this codebase:
1. Add new items under the `## [Unreleased]` section.
2. Group modifications under standard categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
3. Provide clickable file links and concise rationale for changes.
