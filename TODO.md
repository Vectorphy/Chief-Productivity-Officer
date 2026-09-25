# TODO.md — Prioritized Engineering & Governance Backlog

> **Repository**: Chief Productivity Officer (CPO)  
> **Standard**: Prioritized Action Ledger (P0 / P1 / P2 / Backlog)  
> **Last Synchronized**: September 2026  

This backlog categorizes findings and technical debt discovered during the Systems Architect audit. Autonomous agents must consult this list when selecting tasks and check off items as they are implemented and verified.

---

## P0: Critical Blockers, Broken Workflows & Security Vulnerabilities

- [x] **AD-01: Fix Corrupted `.gitignore` Wildcard Spacing**  
  *Context*: `.gitignore:52` had `* . s q l i t e`, which Git parsed as a root `*` wildcard, excluding all newly created files from version control.  
  *Affected Files*: [`.gitignore`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/.gitignore)  
  *Status*: Completed during Lead Systems Architect audit.
- [ ] **SEC-01: Guard Against Dummy `BOT_DEVELOPER_ID` in Production Boot**  
  *Context*: Prevent bot from booting or issuing developer privileges if `BOT_DEVELOPER_ID` in `.env` is unconfigured or set to dummy placeholder `"123456789012345678"`.  
  *Affected Files*: [`bot.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot.py), [`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py)
- [ ] **SEC-02: Add Timeout Wrappers on Discord API Mutations**  
  *Context*: Wrap Discord resource creation calls (`create_role`, `create_text_channel`, `create_voice_channel`) in `asyncio.wait_for(..., timeout=10.0)` to eliminate hung coroutines during Gateway degradation.  
  *Affected Files*: [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py), [`cogs/checkin.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/checkin.py)

---

## P1: Known Bugs, Performance Issues & Missing Test Coverage

- [x] **AD-04: Resolve Mypy Type Argument Discrepancies**  
  *Context*: Fixed incompatible types in `cogs/pomodoro.py:_get_session` (`Optional[Dict[str, Any]]`) and `cogs/study_groups.py` (`text_id` getattr check). Mypy now reports 0 errors across 16 files.  
  *Affected Files*: [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py), [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py)  
  *Status*: Completed during Lead Systems Architect audit.
- [x] **AD-05: Eliminate Coroutine Mock RuntimeWarnings in Pytest**  
  *Context*: Switched mock `interaction.response.is_done` from default AsyncMock to `MagicMock(return_value=False)`. All 20 tests pass with zero warnings.  
  *Affected Files*: [`tests/test_new_features.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests/test_new_features.py)  
  *Status*: Completed during Lead Systems Architect audit.
- [ ] **AD-02: Isolate Standalone Test Database State in `test_file.py`**  
  *Context*: `test_file.py` accesses `bot_database.sqlite` directly. Preexisting channel IDs collide with `cogs/tasklist.py:add_task`, causing assertion failure in `test_task_add_standard`.  
  *Affected Files*: [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py)  
  *Action*: Rebind database connection to an ephemeral in-memory database (`sqlite3.connect(':memory:')`) or transient test SQLite file.
- [ ] **ARC-04: Unify Test Suites Under `tests/`**  
  *Context*: Migrate 54 test flows from root `test_file.py` into `tests/test_e2e_commands.py` so standard `pytest` discovers and executes all 74 tests in CI.  
  *Affected Files*: [`test_file.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/test_file.py), [`tests/`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/tests)
- [ ] **ARC-01: Non-Blocking Asynchronous Database Driver Migration**  
  *Context*: Replace synchronous `sqlite3` driver with `aiosqlite` or wrap queries in `asyncio.to_thread` to prevent thread-blocking I/O inside the Discord asyncio event loop.  
  *Affected Files*: [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py)

---

## P2: Refactoring, Cleanup & Developer Experience

- [x] **Hygiene: Trim Trailing Whitespace in SQL Queries & Docstrings**  
  *Context*: Cleaned multiline SQL whitespace and docstring trailing characters flagged by Ruff in `database.py` and `cogs/study_groups.py`.  
  *Affected Files*: [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py), [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py)  
  *Status*: Completed during Lead Systems Architect audit.
- [ ] **AD-03: Prune Dangling MongoDB Dependencies**  
  *Context*: Remove `pymongo[srv]`, `dnspython`, and `motor` from `requirements.txt` and `pyproject.toml`.  
  *Affected Files*: [`requirements.txt`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/requirements.txt), [`pyproject.toml`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/pyproject.toml)
- [ ] **ARC-03: Purge Dead Code & Organize Root Maintenance Scripts**  
  *Context*: Delete uncompiled duplicate backup file `cogs/study_groups.txt` and relocate `scratch_cleanup.py` into a designated `scripts/` directory.  
  *Affected Files*: `cogs/study_groups.txt`, `scratch_cleanup.py`
- [ ] **ARC-02: Decompose High Cyclomatic Complexity Functions (C901)**  
  *Context*: Decompose monolithic command callbacks exceeding complexity threshold 10 (`study_groups.py:end_group`, `pomodoro.py:start_pomodoro`, `utils.py:validate_parameters`) into specialized helper classes.  
  *Affected Files*: [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py), [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py), [`utils.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/utils.py)

---

## Backlog: Future Enhancements & Planned Features

- [ ] **Automated SQLite Database Snapshots & Periodic Backups**  
  *Context*: Introduce a background task in `bot.py` or `database.py` that generates timestamped SQLite copies into `backups/` every 24 hours.
- [ ] **Python 3.13 Upgrade & Audio Subsystem Validation**  
  *Context*: Validate and integrate `audioop-lts` or upgrade to `discord.py 2.5` once released to resolve the Python 3.13 deprecation of standard library `audioop`.
- [ ] **Prometheus Metrics Exporter for Bot Observability**  
  *Context*: Expose an internal HTTP server publishing active study groups, voice session durations, and command execution latency metrics.
- [ ] **Web Configuration Dashboard for Guild Admins**  
  *Context*: Optional lightweight FastAPI / dashboard service allowing server admins to configure checkin whitelists, voice timeouts, and study categories via web UI.
