# KNOWN_ISSUES.md — Issues & Technical Debt Register

> **Repository**: Chief Productivity Officer (CPO)  
> **Status**: Maintained & Active  
> **Audited**: September 2026 (Lead Systems Architect Overhaul)  

This document serves as the centralized technical debt register and defect log for the CPO bot. Every autonomous agent working on this repository must review these items prior to making architectural decisions and record newly discovered or resolved issues.

---

## 1. Active Defects

### AD-01: `.gitignore` Corrupted Wildcard Spacing Excluding Governance Artifacts
- **Severity**: Critical (P0)
- **Status**: **RESOLVED** (Fixed during audit)
- **Affected File**: [`.gitignore`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.gitignore#L50-L54)
- **Reproduction**:
  1. Inspect lines 51-53 of `.gitignore`: `* . s q l i t e  ` and ` s c r a t c h _ * . p y  `.
  2. Run `git check-ignore -v AGENTS.md`.
  3. Git parsed `*` as an all-file wildcard, causing Git to ignore every newly created file in the repository (`AGENTS.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `KNOWLEDGE_GRAPH.md`, `KNOWN_ISSUES.md`, `TODO.md`, `pyproject.toml`, `requirements-dev.txt`, `tests/test_new_features.py`).
- **Remediation**: Replaced with proper glob patterns `*.sqlite` and `scratch_*.py`, plus added `.pytest_cache/`, `.ruff_cache/`, and `.mypy_cache/`.

### AD-02: Environmental State Bleed in Standalone Test Suite (`test_file.py`)
- **Severity**: High (P1)
- **Status**: **OPEN**
- **Affected Files**: [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py#L244-L253), [`bot_database.sqlite`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot_database.sqlite)
- **Reproduction**:
  1. Populate `bot_database.sqlite` with an active study group containing `text_id = 885134444992806999`.
  2. Execute `.venv\Scripts\python.exe test_file.py`.
  3. In `test_task_add_standard`, `interaction.channel_id` is set to `885134444992806999`.
  4. `cogs/tasklist.py:add_task` checks `self.bot.db.get_study_group_by_channel(channel_id)`.
  5. Because the channel matches the persistent study group in the SQLite file, it formats response as:
     `Task #X added successfully to **Test Group**: ...`
  6. The assertion `assert "Task added successfully" in text` fails with `AssertionError` because `text.split("Task ID: ")` fails.
- **Remediation**: Refactor `test_file.py` to use a dedicated in-memory database (`sqlite3.connect(':memory:')`) or a temporary isolated test database (`test_database.sqlite`) initialized and unlinked per test run.

### AD-03: Dangling Unused MongoDB Dependencies in Manifests
- **Severity**: Low (P2)
- **Status**: **OPEN**
- **Affected Files**: [`requirements.txt`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/requirements.txt#L3-L5), [`pyproject.toml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/pyproject.toml#L14-L16)
- **Reproduction**:
  1. Inspect `requirements.txt`: `pymongo[srv]>=4.6.0`, `dnspython>=2.5.0`, `motor>=3.3.0`.
  2. Grep for `pymongo` or `motor` across the codebase. Zero hits outside dependency manifests.
  3. The bot's persistence architecture is 100% built on SQLite (`database.py`).
- **Remediation**: Remove `pymongo`, `dnspython`, and `motor` from `requirements.txt` and `pyproject.toml`.

### AD-04: Mypy Incompatible Type Argument Inconsistencies
- **Severity**: Medium (P1)
- **Status**: **RESOLVED** (Fixed during audit)
- **Affected Files**: [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py#L174), [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py#L558)
- **Reproduction**:
  1. Run `.venv\Scripts\mypy.exe bot.py database.py utils.py cogs/ tests/`.
  2. Emitted 8 type errors: `_get_session` rejected `Optional[Dict[str, Any]]` from `_resolve_group`, and `getattr(s, 'text_id', 0)` failed type inference.
- **Remediation**: Annotated `_get_session(group: Optional[Dict[str, Any]])` and replaced `getattr(s, 'text_id', 0)` with safe `getattr(s, 'text_id', None)` checks. Mypy now passes with 0 errors across 16 source files.

### AD-05: Unawaited Coroutine Mock Warnings in Pytest
- **Severity**: Low (P2)
- **Status**: **RESOLVED** (Fixed during audit)
- **Affected Files**: [`tests/test_new_features.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_new_features.py#L48)
- **Reproduction**:
  1. Run `.venv\Scripts\python.exe -m pytest`.
  2. Emitted 6 `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` when checking `if not interaction.response.is_done():`.
- **Remediation**: Replaced child mock assignment with `interaction.response.is_done = MagicMock(return_value=False)`. Pytest now passes with 20/20 clean assertions.

---

## 2. Architectural Debt

### ARC-01: Blocking Synchronous SQLite I/O in Async Event Loop
- **Severity**: High (P1)
- **Status**: **OPEN**
- **Affected File**: [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py#L17-L24)
- **Details**:
  `DBHandler` wraps operations with `async with self.lock:`, but uses standard synchronous `sqlite3.connect()`, `cursor.execute()`, and `conn.commit()`. Disk I/O operations block the OS thread executing the asyncio event loop. Under multi-server scale with concurrent standup checkins and study group updates, this blocks Discord Gateway heartbeat tasks, leading to zombie connections or Discord timeout drops.
- **Proposed Solution**: Migrate persistence layer to `aiosqlite` or delegate queries via `await asyncio.to_thread(self._sync_query, ...)`.

### ARC-02: Monolithic Functions with Extreme Cyclomatic Complexity (C901)
- **Severity**: Medium (P2)
- **Status**: **OPEN**
- **Affected Files**:
  - [`cogs/study_groups.py:end_group`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py#L1428) (Complexity: 28 > 10)
  - [`cogs/study_groups.py:setup_group_resources`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py#L72) (Complexity: 11 > 10)
  - [`cogs/study_groups.py:add_member`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py#L210) (Complexity: 12 > 10)
  - [`cogs/pomodoro.py:start_pomodoro`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py#L205) (Complexity: 20 > 10)
  - [`utils.py:validate_parameters`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/utils.py#L91) (Complexity: 19 > 10)
  - [`utils.py:check_manager`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/utils.py#L193) (Complexity: 15 > 10)
  - [`database.py:update_study_group_by_id`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py#L251) (Complexity: 17 > 10)
- **Details**: Ruff flags 20 functions exceeding complexity threshold 10. These monolithic functions intertwine Discord API calls, permission checks, database mutations, and UI embed generation into single blocks.
- **Proposed Solution**: Decompose large command callbacks into dedicated service classes: (1) Permission Validator, (2) Discord Resource Provisioner, (3) Database State Synchronizer.

### ARC-03: Orphaned Scratch Artifacts and Duplicate Backups in Tree
- **Severity**: Low (P2)
- **Status**: **OPEN**
- **Affected Files**:
  - `cogs/study_groups.txt` (15 KB stale text duplicate of older `study_groups.py`)
  - `scratch_cleanup.py` (Ad-hoc cleanup script committed to repository root)
- **Details**: Uncompiled and non-executable artifacts linger in production directories, confusing developers and static analysis tools.
- **Proposed Solution**: Move one-off administrative scripts to a designated `scripts/` or `tools/` folder, and purge `cogs/study_groups.txt`.

### ARC-04: Test Suite Bifurcation (`tests/` vs `test_file.py`)
- **Severity**: Medium (P1)
- **Status**: **OPEN**
- **Affected Files**: [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py), [`tests/`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests)
- **Details**:
  The automated pytest suite in `tests/` executes 20 unit tests, while 54 exhaustive end-to-end slash command flows reside in `test_file.py` outside `tests/`. CI currently only runs `pytest tests/`, leaving the comprehensive matrix unmonitored on commits.
- **Proposed Solution**: Migrate `test_file.py` into `tests/test_e2e_commands.py` compatible with standard `pytest` discovery.

---

## 3. Security & Reliability Risks

### SEC-01: Default Superuser ID in Configuration Template
- **Severity**: Medium (P1)
- **Status**: **OPEN**
- **Affected Files**: [`.env.example`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.env.example#L6), [`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py#L169)
- **Details**: If an operator deploys without setting `BOT_DEVELOPER_ID`, dummy snowflake `"123456789012345678"` might match a real user.
- **Mitigation**: Add runtime check in `bot.py:setup_hook` to log a critical warning if `BOT_DEVELOPER_ID` matches the placeholder or is missing.

### SEC-02: Missing Timeout Wrappers on Discord API Calls
- **Severity**: Medium (P1)
- **Status**: **OPEN**
- **Affected Files**: [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py), [`cogs/checkin.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/checkin.py)
- **Details**: Resource provisioning calls (`guild.create_role`, `guild.create_text_channel`, `channel.send`) lack explicit `asyncio.wait_for(..., timeout=10.0)` guards. Discord API outages could cause coroutines to hang indefinitely.
- **Mitigation**: Wrap critical Discord mutation calls in standardized timeout helper.

### SEC-03: SQLite Single-File Reliability in Containerized Environments
- **Severity**: Medium (P2)
- **Status**: **OPEN**
- **Affected Files**: [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py), [`bot_database.sqlite`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot_database.sqlite)
- **Details**: SQLite works well for single-node deployments, but lacks automated backups, point-in-time recovery, or multi-process concurrency safety. If container storage is ephemeral, state is lost on restart.
- **Mitigation**: Implement automated periodic SQLite snapshot/backup routine into `backups/` and document volume mounting requirements.

### SEC-04: Upstream Python 3.13 `audioop` Deprecation
- **Severity**: Low (P2)
- **Status**: **OPEN**
- **Affected File**: `.venv/Lib/site-packages/discord/player.py:30`
- **Details**: Python 3.13 deprecates `audioop`. Running on Python 3.13+ will cause Discord voice playback to crash unless patched.
- **Mitigation**: Track discord.py 2.5 release or install standalone `audioop-lts` package when upgrading Python runtime.
