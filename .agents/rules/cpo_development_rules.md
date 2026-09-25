# CPO Development Rules for AI Coding Assistants

1. **Stack**: Python 3.10+, discord.py 2.4.0+, SQLite 3.
2. **Commands**: Always register user-facing interactions as slash commands using `@app_commands.command`.
3. **Database Concurrency**: Any database query in `database.py` MUST be guarded by `async with self.lock:` and use parameterized SQL queries with `?`.
4. **Environment**: Never log or hardcode `DISCORD_BOT_TOKEN`. Read from `.env` using `python-dotenv`.
5. **Testing**: Write unit tests in `tests/` using `unittest.mock.AsyncMock` so tests can run offline without network access or bot tokens.
6. **Logging**: Adhere strictly to `docs/LOGGING_STANDARDS.md`. Use `logger = logging.getLogger(__name__)`, include contextual metadata (`user_id`, `guild_id`, `group_id`), and never use `print()`.
7. **Changelog**: Every change MUST be recorded in `CHANGELOG.md` under `## [Unreleased]`.
8. **Documentation**: When adding new commands or modifying schemas, keep `commands.md`, `KNOWLEDGE_GRAPH.md`, `knowledge_graph.json`, and `ARCHITECTURE.md` synchronized.
