"""File operations module for AI-driven file management.

Provides safe file operations (create, read, modify, move, delete)
within user-approved workspace folders. The AI can request these
operations via structured tool-call JSON blocks in its response.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FileOperationError(Exception):
    """Raised when a file operation fails or is not allowed."""
    pass


class WorkspaceManager:
    """Manages allowed workspace folders and performs safe file operations."""

    def __init__(self, allowed_folders: Optional[List[str]] = None):
        self._allowed_folders: List[Path] = []
        if allowed_folders:
            for f in allowed_folders:
                self.add_folder(f)

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------
    def add_folder(self, folder_path: str) -> bool:
        """Add a folder to the allowed workspace list."""
        p = Path(folder_path).resolve()
        if not p.is_dir():
            return False
        if p not in self._allowed_folders:
            self._allowed_folders.append(p)
        return True

    def remove_folder(self, folder_path: str) -> bool:
        p = Path(folder_path).resolve()
        if p in self._allowed_folders:
            self._allowed_folders.remove(p)
            return True
        return False

    @property
    def allowed_folders(self) -> List[str]:
        return [str(f) for f in self._allowed_folders]

    def is_path_allowed(self, target: str) -> bool:
        """Check whether *target* is inside one of the allowed folders."""
        t = Path(target).resolve()
        return any(self._is_subpath(t, f) for f in self._allowed_folders)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def read_file(self, path: str) -> str:
        self._assert_allowed(path)
        p = Path(path)
        if not p.is_file():
            raise FileOperationError(f"File not found: {path}")
        return p.read_text(encoding="utf-8", errors="replace")

    def create_file(self, path: str, content: str = "") -> str:
        self._assert_allowed(path)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Created: {path}"

    def modify_file(self, path: str, content: str) -> str:
        self._assert_allowed(path)
        p = Path(path)
        if not p.is_file():
            raise FileOperationError(f"File not found: {path}")
        p.write_text(content, encoding="utf-8")
        return f"Modified: {path}"

    def delete_file(self, path: str) -> str:
        self._assert_allowed(path)
        p = Path(path)
        if p.is_file():
            p.unlink()
            return f"Deleted file: {path}"
        elif p.is_dir():
            shutil.rmtree(p)
            return f"Deleted folder: {path}"
        raise FileOperationError(f"Not found: {path}")

    def move_file(self, src: str, dst: str) -> str:
        self._assert_allowed(src)
        self._assert_allowed(dst)
        s = Path(src)
        d = Path(dst)
        if not s.exists():
            raise FileOperationError(f"Source not found: {src}")
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return f"Moved: {src} → {dst}"

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        self._assert_allowed(path)
        p = Path(path)
        if not p.is_dir():
            raise FileOperationError(f"Not a directory: {path}")
        entries = []
        for item in sorted(p.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return entries

    def create_directory(self, path: str) -> str:
        self._assert_allowed(path)
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Directory created: {path}"

    # ------------------------------------------------------------------
    # Tool-call execution
    # ------------------------------------------------------------------
    def execute_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """Execute a single tool call from the AI response.

        Expected format::

            {"tool": "create_file", "path": "...", "content": "..."}
            {"tool": "modify_file", "path": "...", "content": "..."}
            {"tool": "delete_file", "path": "..."}
            {"tool": "move_file", "src": "...", "dst": "..."}
            {"tool": "read_file", "path": "..."}
            {"tool": "list_directory", "path": "..."}
            {"tool": "create_directory", "path": "..."}
        """
        tool = tool_call.get("tool", "").lower()
        try:
            if tool == "create_file":
                return self.create_file(tool_call["path"], tool_call.get("content", ""))
            elif tool == "modify_file":
                return self.modify_file(tool_call["path"], tool_call["content"])
            elif tool == "delete_file":
                return self.delete_file(tool_call["path"])
            elif tool == "move_file":
                return self.move_file(tool_call["src"], tool_call["dst"])
            elif tool == "read_file":
                content = self.read_file(tool_call["path"])
                return f"Content of {tool_call['path']}:\n{content}"
            elif tool == "list_directory":
                entries = self.list_directory(tool_call["path"])
                return json.dumps(entries, indent=2)
            elif tool == "create_directory":
                return self.create_directory(tool_call["path"])
            else:
                return f"Unknown tool: {tool}"
        except (FileOperationError, KeyError, OSError) as exc:
            return f"Error: {exc}"

    # ------------------------------------------------------------------
    # Parse AI response for tool calls
    # ------------------------------------------------------------------
    @staticmethod
    def parse_tool_calls(response_text: str) -> List[Dict[str, Any]]:
        """Extract ``<tool_call>...</tool_call>`` JSON blocks from AI text."""
        pattern = r"<tool_call>\s*(\{.*?\})\s*</tool_call>"
        matches = re.findall(pattern, response_text, re.DOTALL)
        calls = []
        for m in matches:
            try:
                calls.append(json.loads(m))
            except json.JSONDecodeError:
                continue
        return calls

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_subpath(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def _assert_allowed(self, path: str) -> None:
        if not self.is_path_allowed(path):
            raise FileOperationError(
                f"Access denied: '{path}' is outside of the allowed workspace folders."
            )

    # ------------------------------------------------------------------
    # System prompt fragment
    # ------------------------------------------------------------------
    def build_system_prompt_fragment(self) -> str:
        """Return the system-prompt section that teaches the AI how to use file tools."""
        if not self._allowed_folders:
            return ""

        folders_str = "\n".join(f"  - {f}" for f in self._allowed_folders)
        return f"""

======================================================================
SYSTEM CAPABILITIES & AUTONOMOUS PROGRAMMER PERSONA
======================================================================
You are an expert autonomous software engineer and AI agent. You have 
direct access to the user's local file system workspace. The user has 
granted you read/write permission to the following allowed folders:
{folders_str}

As an autonomous coding agent (similar to Claude Code), your goal is to 
solve the user's programming tasks efficiently, accurately, and without 
requiring constant supervision.

You can perform file operations by including exactly formatted <tool_call> 
JSON blocks in your response. Each block must contain valid JSON.

AVAILABLE TOOLS:
• create_file      — {{"tool": "create_file", "path": "<full_absolute_path>", "content": "<entire_file_content>"}}
• modify_file      — {{"tool": "modify_file", "path": "<full_absolute_path>", "content": "<entire_new_file_content>"}}
• delete_file      — {{"tool": "delete_file", "path": "<full_absolute_path>"}}
• move_file        — {{"tool": "move_file", "src": "<full_absolute_path>", "dst": "<full_absolute_path>"}}
• read_file        — {{"tool": "read_file", "path": "<full_absolute_path>"}}
• list_directory   — {{"tool": "list_directory", "path": "<full_absolute_path>"}}
• create_directory — {{"tool": "create_directory", "path": "<full_absolute_path>"}}

YOUR WORKFLOW:
1. UNDERSTAND & EXPLORE: If the user asks for a change but you don't know the exact file contents, ALWAYS use `list_directory` and `read_file` first to gather context before writing code.
2. PLAN: Think step-by-step about how you will solve the problem.
3. EXECUTE: Use `create_file` or `modify_file` to implement the solution. 
4. REPORT: Briefly explain what you did.

CRITICAL RULES FOR TOOL CALLS:
- ONLY operate inside the allowed folders listed above.
- ALWAYS use FULL, ABSOLUTE paths (e.g., C:/Users/.../folder/file.py or /home/.../folder/file.py).
- When using `modify_file`, you MUST provide the ENTIRE completely rewritten file content in the "content" field. Do not use placeholders or summaries. The existing file will be overwritten with exactly what you provide.
- You can chain multiple <tool_call> blocks in a single response to perform multiple actions at once.
- DO NOT wrap the <tool_call> tags themselves in markdown code blocks. They must be raw text in your response.

Example of exploring:
<tool_call> {{"tool": "list_directory", "path": "{self._allowed_folders[0] if self._allowed_folders else '/YOUR_WORKSPACE_FOLDER'}"}} </tool_call>

Example of modifying code:
<tool_call> {{"tool": "modify_file", "path": "{self._allowed_folders[0] if self._allowed_folders else '/YOUR_WORKSPACE_FOLDER'}/main.py", "content": "print('Hello world!')\\n"}} </tool_call>
"""
