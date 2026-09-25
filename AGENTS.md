# AGENTS.md — Autonomous Operations Manual & Developer Playbook

> **Repository**: Chief Productivity Officer (CPO)  
> **Tech Stack**: Python 3.12, Discord.py 2.4.x, SQLite 3 (async DAL wrapper), Pytest, Ruff, Mypy  
> **Core Purpose**: Discord Productivity, Study Group Orchestration, Dynamic Pomodoro Timer & Standup Check-in Bot

---

## 1. Toolchain Directives

Copy-pasteable terminal commands for environment setup, verification, testing, and formatting.

### Environment & Installation
```bash
# Using uv (Recommended for ultra-fast setup)
uv venv --python 3.12 .venv
.venv\Scripts\activate       # Windows PowerShell / CMD
# source .venv/bin/activate  # Unix / macOS
uv pip install -r requirements-dev.txt

# Alternative: Standard Python venv & pip
python -m venv .venv
.venv\Scripts\activate       # Windows PowerShell / CMD
# source .venv/bin/activate  # Unix / macOS
pip install -r requirements-dev.txt
```

### Running the Application
```bash
# Copy and configure environment variables
cp .env.example .env

# Launch the Discord bot
python bot.py
# Or directly via venv binary
.venv\Scripts\python.exe bot.py
```

### Packaging & Build
```bash
# Build standard Python wheel and sdist distributions
python -m build
# Or directly via venv binary
.venv\Scripts\python.exe -m build
```

### Testing Directives
```bash
# Run entire test suite (mock-safe, offline, zero token required)
.venv\Scripts\python.exe -m pytest

# Run with verbose output and test names
.venv\Scripts\python.exe -m pytest -v

# Run a single test file
.venv\Scripts\python.exe -m pytest tests/test_new_features.py
.venv\Scripts\python.exe -m pytest tests/test_productivity_tracker.py

# Run a single test case / method
.venv\Scripts\python.exe -m pytest tests/test_new_features.py -k "test_ratio_calculations"
.venv\Scripts\python.exe -m pytest tests/test_tasklist.py -k "test_add_task"

# Run tests with coverage report
.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing
```

### Linting, Formatting & Type Checking
```bash
# Static type checking across all active source files (enforce zero errors)
.venv\Scripts\mypy.exe bot.py database.py utils.py cogs/ tests/

# Fast linting with Ruff
.venv\Scripts\ruff.exe check bot.py database.py utils.py cogs/ tests/

# Automatically apply safe lint fixes
.venv\Scripts\ruff.exe check --fix bot.py database.py utils.py cogs/ tests/

# Check code formatting (black-compatible)
.venv\Scripts\ruff.exe format --check bot.py database.py utils.py cogs/ tests/

# Format codebase in-place
.venv\Scripts\ruff.exe format bot.py database.py utils.py cogs/ tests/
```

---

## 2. Three-Tier Guardrails

### Always Do (Non-Negotiables)
- **Always Run Verification Tests**: Run `.venv\Scripts\python.exe -m pytest` and target single-file test runs on any modified module prior to declaring completion.
- **Always Verify Type Safety**: Run `.venv\Scripts\mypy.exe bot.py database.py utils.py cogs/ tests/` and maintain 0 errors across all source files.
- **Always Use Parameterized SQL**: Every query in `database.py` MUST use `?` placeholders (e.g. `SELECT * FROM study_groups WHERE guild_id = ?`).
- **Always Acquire the Database Lock**: Wrap all SQLite calls inside `async with self.lock:` in `database.py`.
- **Always Acknowledge Discord Interactions**: Within 3 seconds, call `await interaction.response.defer(...)` or `await interaction.response.send_message(...)`.
- **Always Use Structured Logging**: Use `logger = logging.getLogger(__name__)` and provide contextual IDs (`guild_id`, `user_id`, `group_id`, `session_id`). Never use raw `print()` statements.
- **Always Clean Up Transient State**: When terminating a group or session, purge Discord resources (channels, roles), update DB active status to `0`, and remove memory references from session dictionaries.
- **Always Synchronize Governance Artifacts**: Update `CHANGELOG.md` under `## [Unreleased]`, `KNOWN_ISSUES.md`, and `TODO.md` upon modifying features or encountering new constraints.

### Ask First (Guarded Actions)
- **Modifying Database Schema**: Adding, modifying, or renaming columns in `database.py` requires confirmation and backwards-compatible `ALTER TABLE` / `IF NOT EXISTS` logic.
- **Changing Public Slash Command Signatures**: Altering command names, required parameters, or option choices consumed by Discord users.
- **Adding New Dependencies**: Introducing third-party libraries into `requirements.txt` or `pyproject.toml`.
- **Deleting Discord Resources in Production**: Purging channels, roles, or server categories in live guild environments.
- **Altering the 5-Tier Permission Hierarchy**: Modifying the permission evaluation logic in `cogs/manager.py` or `utils.py`.

### Never Do (Hard Stops)
- **NEVER Commit Secrets**: Never hardcode or print bot tokens (`DISCORD_BOT_TOKEN`), user credentials, or API keys.
- **NEVER Execute Raw Formatted SQL**: Never use f-strings or string concatenation for database queries (`f"SELECT * FROM {table} WHERE id = '{user_input}'"` is strictly forbidden).
- **NEVER Drop Production Tables**: Never execute unprompted `DROP TABLE` statements on production databases without explicit user consent.
- **NEVER Commit Database or Cache Artifacts**: Never commit `.sqlite`, `.sqlite3`, `.db`, `.pytest_cache`, `.mypy_cache`, or `.ruff_cache` files into version control.
- **NEVER Introduce Blocking Synchronous Calls in Async Loops**: Never invoke blocking network requests (`requests.get`) or heavy CPU-bound disk operations directly without `asyncio.to_thread`.
- **NEVER Swallow Exceptions Silently**: Never write bare `except: pass` without structured logging or reporting.

---

## 3. Architecture Invariants

Conventions and rules not fully enforceable by compiler syntax alone:

1. **5-Tier Authorization Model (`cogs/manager.py`)**:
   - `BOT_DEVELOPER` (Tier 4): Superuser defined in `.env` / `BOT_DEVELOPER_ID`. Full global override.
   - `GUILD_MANAGER` (Tier 3): Server owner (`guild.owner_id`) or members with administrator / manage guild privileges.
   - `GROUP_OWNER` (Tier 2): Creator or assigned owner of a study group / check-in session.
   - `GROUP_MEMBER` (Tier 1): Verified member inside a study group / check-in roster.
   - `REGULAR_USER` (Tier 0): Baseline server participant.
2. **Channel-Contextual Scoping**:
   - Commands like `/task_add`, `/task_list`, `/start_pomodoro`, and `/end_group` detect active channel context via `get_study_group_by_channel(channel_id)` to isolate group resources from global bleed.
3. **5:1:3 Automatic Pomodoro Ratio**:
   - A single focus duration input automatically computes `(focus, focus // 5, focus * 3 // 5)` (e.g. 50m Focus -> 10m Short Break -> 30m Long Break).
4. **Discord Embed Field Limits**:
   - Embeds must not exceed 25 fields or 6,000 total characters to prevent Discord HTTP 400 Bad Request errors.
5. **In-Memory & Persistent State Synchronization**:
   - In-memory representations (e.g. `StudyGroupCog.sessions`, `Pomodoro.sessions`, `CheckinCog.active_sessions`) must strictly mirror SQLite records (`active = 1`). On bot reboot, active sessions are hydrated from the database via `load_active_sessions_from_db`.

---

## 4. Mandatory Operating Contract

Every AI agent touching this repository must adhere to the following contract:

```markdown
## Agent Operating Contract
Every AI agent touching this repository must:
1. **Read Context First:** Ingest `AGENTS.md`, `KNOWLEDGE_GRAPH.md`, and `KNOWN_ISSUES.md` before taking action.
2. **Respect Guardrails:** Strictly follow Always / Ask First / Never rules.
3. **Verify Locally:** Run relevant lint and test commands before declaring work complete.
4. **Synchronize Documentation:**
   - Architecture or flow changes -> update `KNOWLEDGE_GRAPH.md`.
   - Discovered or resolved bugs -> update `KNOWN_ISSUES.md`.
   - Completed or newly surfaced tasks -> update `TODO.md`.
   - Functional or breaking changes -> append to `CHANGELOG.md`.
5. **Leave Zero Residue:** Clean up temporary files, scripts, and unverified state before finishing.
```

---

## 5. Offline Testing & Mocking Standard

Agents can verify 100% of command handlers, callbacks, and database transactions without a live Discord bot token using `unittest.mock.AsyncMock`:

```python
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import discord

class TestFeatureExample(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.db = AsyncMock()
        self.bot.bot_developer_id = 534168986149978112

    def test_command_execution(self):
        async def run_test():
            interaction = AsyncMock(spec=discord.Interaction)
            interaction.response.is_done = MagicMock(return_value=False)
            interaction.guild_id = 885134444992806962
            interaction.user.id = 12345
            interaction.user.display_name = "ProductiveCoder"
            
            # Execute command callback
            # await cog.my_command.callback(cog, interaction, ...)
            
            # Verify response was sent
            interaction.response.send_message.assert_called_once()
        asyncio.run(run_test())
```

---

## 6. How to Implement a New Feature / Cog

When asked to implement a new feature or command:
1. **Model / Database**: Add required tables and async CRUD methods in [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py).
2. **Business Logic / Utilities**: Put pure calculations, parsing, or formatting helpers in [`utils.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/utils.py).
3. **Cog Implementation**: Create a new class subclassing `commands.Cog` in `cogs/<new_module>.py` with a top-level `async def setup(bot): await bot.add_cog(NewCog(bot))`.
4. **Command Registration**: Use `@app_commands.command()` with parameter decorators and `@app_commands.default_permissions(...)` for privileged operations.
5. **Logging**: Add structured `logger.info`, `logger.warning`, and `logger.exception` calls per [`docs/LOGGING_STANDARDS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/docs/LOGGING_STANDARDS.md).
6. **Testing**: Add a corresponding unit test in `tests/test_<new_module>.py` mocking `discord.Interaction` and `DBHandler`.
7. **Documentation & Changelog**: Update [`commands.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/commands.md), [`KNOWLEDGE_GRAPH.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWLEDGE_GRAPH.md), [`ARCHITECTURE.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/ARCHITECTURE.md), and append to [`CHANGELOG.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/CHANGELOG.md).
