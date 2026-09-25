# Logging & Observability Standards

This document establishes the mandatory logging protocols for the **Chief Productivity Officer (CPO)** bot. All AI agents and human contributors must follow these rules when developing or modifying modules.

---

## 1. Logger Initialization

Every Python module must initialize a module-level logger using Python's standard `logging` library:

```python
import logging

logger = logging.getLogger(__name__)
```

- **DO NOT** use `print()` statements for application events, diagnostics, or debugging.
- **DO NOT** reconfigure root loggers with `logging.basicConfig()` inside cogs or utilities (root logging configuration is reserved exclusively for `bot.py`).

---

## 2. Standard Log Levels & Semantics

| Level | When to Use | Example |
|---|---|---|
| `logger.debug(...)` | Fine-grained diagnostic information, timing calculations, regex evaluation results, internal state dumps. | `logger.debug(f"Parsed duration '{duration_str}' to {result} seconds")` |
| `logger.info(...)` | Normal operational milestones (command execution, session start/end, group created, member joined, table verified). | `logger.info(f"User {user.id} started checkin session '{session_id}'")` |
| `logger.warning(...)` | Recoverable discrepancies, unauthorized attempts, invalid user inputs, rate limits, session caps reached. | `logger.warning(f"User {user.id} attempted to join full study group {group_id}")` |
| `logger.error(...)` | Operation failures that prevent a command or task from succeeding (database write failure, Discord API HTTP errors). | `logger.error(f"Failed to create role for study group '{name}': {e}")` |
| `logger.critical(...)` | Fatal system-level errors that threaten bot stability or database integrity. | `logger.critical(f"Database lock timeout or schema corruption: {e}")` |

---

## 3. Contextual Logging Formatting

Always include relevant entity identifiers in log messages to facilitate debugging across distributed guilds:
- `user_id` / `interaction.user.id`
- `guild_id` / `interaction.guild_id`
- `group_id` / `session_id`
- `channel_id`

```python
# Good: High-context and searchable
logger.info(f"StudyGroup '{self.name}' [ID: {self.group_id}] created by User [{self.creator_id}] in Guild [{self.guild_id}]")

# Bad: Ambiguous and unsearchable
logger.info("Created study group")
```

---

## 4. Exception Handling & Stack Traces

When catching exceptions:
- Use `logger.exception(...)` inside `except` blocks to automatically capture the full traceback.
- Do not catch bare `Exception` without logging it.

```python
try:
    await channel.delete(reason="Study group ended")
except discord.HTTPException as e:
    logger.exception(f"Discord API error while deleting channel {channel.id} for group {group_id}: {e}")
```

---

## 5. Security & Privacy Guardrails

- **NEVER log bot tokens, secrets, or API keys** (`DISCORD_BOT_TOKEN`, passwords, credentials).
- Avoid logging raw user messages that may contain personally identifiable information (PII).
