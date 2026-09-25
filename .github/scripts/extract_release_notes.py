#!/usr/bin/env python3
"""
Extract release notes for a specified tag/version from CHANGELOG.md.
"""
import os
import re
import sys


def extract_notes(tag: str) -> str:
    changelog_path = "CHANGELOG.md"
    if not os.path.exists(changelog_path):
        return "Automated distribution release for Chief Productivity Officer."

    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()

    version = tag.lstrip("v").strip()
    if version:
        pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Fallback: find first release heading that is not [Unreleased]
    pattern = r"## \[(?!Unreleased)[^\]]+\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    return "Automated distribution release for Chief Productivity Officer."


def main() -> None:
    tag = os.environ.get("RELEASE_TAG", "")
    if not tag and len(sys.argv) > 1:
        tag = sys.argv[1]

    notes = extract_notes(tag)
    with open("RELEASE_NOTES.md", "w", encoding="utf-8") as f:
        f.write(notes + "\n")
    print(f"Extracted {len(notes)} bytes of release notes for tag '{tag}' into RELEASE_NOTES.md")


if __name__ == "__main__":
    main()
