# Chief Productivity Officer (CPO) — AI Assistant Context

Welcome! This repository houses the **Chief Productivity Officer (CPO)** Discord Bot.

### Essential Entry Points
- Knowledge Graph & Architecture: [KNOWLEDGE_GRAPH.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWLEDGE_GRAPH.md)
- Machine-Readable Knowledge Graph: [knowledge_graph.json](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/knowledge_graph.json)
- Full Agent Playbook & Instructions: [AGENTS.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/AGENTS.md)
- System Architecture & Visual Diagrams: [ARCHITECTURE.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/ARCHITECTURE.md)
- Changelog Ledger: [CHANGELOG.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/CHANGELOG.md)
- Logging Standards: [docs/LOGGING_STANDARDS.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/docs/LOGGING_STANDARDS.md)
- Command Reference: [commands.md](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/commands.md)

### Agent Directives
1. Always log events using `logger = logging.getLogger(__name__)` as outlined in `docs/LOGGING_STANDARDS.md`.
2. Always record updates in `CHANGELOG.md` under `## [Unreleased]`.
3. Verify all changes with `pytest` before finalizing tasks.
4. Always document any newly discovered bugs, technical debt, or unresolved type/linter issues in `KNOWN_ISSUES.md`.

### Development Commands
- Run Tests: `pytest` or `python -m unittest discover tests`
- Run Bot: `python bot.py`
- Setup Environment: `uv pip install -r requirements-dev.txt`
