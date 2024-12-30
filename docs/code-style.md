## Code Style Guide for [Bot Name]

This guide outlines the coding conventions and style guidelines for the [Bot Name] Discord bot project. Adhering to these standards will help us maintain a clean, consistent, and readable codebase.

### 1. General Principles

-   **Readability:**  Prioritize code readability over cleverness or brevity. Code should be easy to understand and maintain.
-   **Consistency:**  Be consistent in your coding style throughout the project. Follow the conventions outlined in this guide.
-   **Pythonic Code:**  Write code that follows Python's best practices and idioms. Refer to the  [PEP 8 style guide](https://www.python.org/dev/peps/pep-0008/)  for general Python style guidelines.

### 2. Naming Conventions

-   **Variables and Functions:**  Use lowercase with underscores to separate words (e.g.,  `user_name`,  `send_message`).
-   **Classes:**  Use CamelCase (e.g.,  `StudyGroup`,  `CheckinSession`).
-   **Constants:**  Use uppercase with underscores to separate words (e.g.,  `MAX_MEMBERS`,  `DEFAULT_DURATION`).
-   **Modules and Files:**  Use lowercase with underscores (e.g.,  `study_groups.py`,  `utils.py`).

### 3. Code Formatting

-   **Indentation:**  Use 4 spaces for indentation. Do not use tabs.
-   **Line Length:**  Keep lines under 80 characters whenever possible. Break long lines using parentheses or backslashes.
-   **Blank Lines:**  Use blank lines to separate logical blocks of code and improve readability.
-   **Whitespace:**  Use spaces around operators and after commas (e.g.,  `x = y + 1`,  `my_list = [1, 2, 3]`).

### 4. Docstrings

-   **Use Docstrings:**  Write docstrings for all modules, classes, functions, and methods.
-   **Docstring Style:**  Use the Google style for docstrings. Refer to the  [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)  for examples.

**Example:**

```python
def parse_duration(duration_str: str) -> int:
    """Parses a duration string into seconds.

    Args:
        duration_str: The duration string (e.g., "2h 30m").

    Returns:
        The duration in seconds.
    """
    # ... (implementation)
```

### 5. Comments

-   **Use Comments Sparingly:**  Write comments only when necessary to explain complex logic or non-obvious code.
-   **Clear and Concise:**  Keep comments clear, concise, and to the point.
-   **Comment Style:**  Use inline comments (`# comment`) for short explanations. Use block comments (`""" comment """`) for longer explanations or multi-line comments.

### 6. Imports

-   **Organize Imports:**  Group imports into standard library imports, third-party imports, and local imports.
-   **One Import per Line:**  Import one module per line.
-   **Avoid Wildcard Imports:**  Do not use wildcard imports (`from module import *`).

**Example:**

```python
import os
import logging

import discord
from discord import app_commands

from .utils import parse_duration
```

### 7. Error Handling

-   **Catch Specific Exceptions:**  Catch specific exception types to handle different error scenarios gracefully.
-   **Log Errors:**  Log errors with sufficient context (e.g., the query being executed, the user ID) to aid in debugging.
-   **User-Friendly Messages:**  Provide user-friendly error messages that explain the issue and potential solutions.

### 8. Asynchronous Programming

-   **Use  `async`/`await`:**  Use  `async`  and  `await`  keywords for asynchronous operations (e.g., database interactions, network requests).
-   **Avoid Blocking Operations:**  Ensure that long-running operations do not block the bot's event loop.

### 9. Database Interactions

-   **Asynchronous Operations:**  Use Motor's asynchronous methods for database interactions.
-   **Connection Pooling:**  Rely on Motor's automatic connection pooling.
-   **Data Integrity:**  Validate data before saving it to the database and use unique constraints to prevent duplicates.

### 10. Code Reviews

-   **Get Code Reviews:**  Request code reviews from other team members before merging changes.
-   **Constructive Feedback:**  Provide constructive feedback during code reviews to improve code quality and maintain consistency.
