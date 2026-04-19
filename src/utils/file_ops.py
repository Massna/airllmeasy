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
        """Add a folder or file to the allowed workspace list."""
        p = Path(folder_path).resolve()
        if not p.exists():
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

    def clear_folders(self):
        """Clear all allowed folders/files."""
        self._allowed_folders = []

    @property
    def allowed_folders(self) -> List[str]:
        return [str(f) for f in self._allowed_folders]

    def is_path_allowed(self, target: str) -> bool:
        """Check whether *target* is inside one of the allowed folders, or matches an allowed file.
        
        For files that don't exist yet (create_file), we check if their
        parent directory is inside an allowed folder.
        """
        t = Path(target).resolve()
        for f in self._allowed_folders:
            if f.is_file() and t == f:
                return True
            if f.is_dir() and self._is_subpath(t, f):
                return True
        # For new files: check if the parent is inside an allowed folder
        parent = t.parent
        for f in self._allowed_folders:
            if f.is_dir() and self._is_subpath(parent, f):
                return True
            # Also allow creating sibling files next to an allowed file
            if f.is_file() and parent == f.parent:
                return True
        return False

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
            # Auto-create if it doesn't exist yet
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Created (via modify): {path}"
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
        calls = []
        # Pattern 1: <tool_call> ... </tool_call>
        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        for m in matches:
            m = m.strip()
            # Clean markdown code blocks if the AI inserted them inside the tag
            if m.lower().startswith("```json"):
                m = m[7:]
            elif m.startswith("```"):
                m = m[3:]
            if m.endswith("```"):
                m = m[:-3]
            m = m.strip()
            
            try:
                calls.append(json.loads(m))
            except json.JSONDecodeError:
                continue
                
        # Pattern 2: Fallback to just grabbing floating JSON blocks if tags failed
        if not calls:
            json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE)
            for jb in json_blocks:
                try:
                    parsed = json.loads(jb)
                    if isinstance(parsed, dict) and "tool" in parsed:
                        calls.append(parsed)
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
        example_path = Path(self._allowed_folders[0])
        example_dir = str(example_path.parent if example_path.is_file() else example_path).replace("\\", "/")
        example_file = str(example_path).replace("\\", "/")

        prompt = f"""

SYSTEM CAPABILITIES: AUTONOMOUS FILE SYSTEM ACCESS
======================================================================
You are an expert autonomous software engineer. You have DIRECT access to 
the user's local file system. 

ALLOWED WORKSPACE PATHS:
{folders_str}

TOOLS FOR AUTONOMOUS OPERATION:
"""
        prompt += '• create_file      — {"tool": "create_file", "path": "<abs_path>", "content": "<content>"}\n'
        prompt += '• modify_file      — {"tool": "modify_file", "path": "<abs_path>", "content": "<full_new_content>"}\n'
        prompt += '• delete_file      — {"tool": "delete_file", "path": "<abs_path>"}\n'
        prompt += '• read_file        — {"tool": "read_file", "path": "<abs_path>"}\n'
        prompt += '• list_directory   — {"tool": "list_directory", "path": "<abs_path>"}\n'
        prompt += """
CRITICAL RULES:
1. ALWAYS use <tool_call> tags and JSON blocks to perform actions. 
2. DONT JUST TALK. If you say you are going to edit a file, you MUST include the <tool_call> block in that same response.
3. ALWAYS use FULL ABSOLUTE PATHS.
4. For modify_file, the "content" field must contain the ENTIRE file content.
5. NO REPETITION: Do NOT quote or repeat the file content in your conversational response. Just execute the edits.
6. CONCISE: Be extremely concise in your verbal explanation. Focus on the tool calls.

Example of exploring:
<tool_call>
"""
        prompt += '{"tool": "list_directory", "path": "' + example_dir + '"}\n'
        prompt += """</tool_call>

Example of editing:
<tool_call>
"""
        prompt += '{"tool": "modify_file", "path": "' + example_file + '", "content": "..."}\n'
        prompt += "</tool_call>\n"
        return prompt
