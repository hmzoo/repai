#!/usr/bin/env python3
"""
RepaI - Recursive Evolutionary Programming Agent
Main orchestrator for self-improving application
"""

import os
import sys
import json
import time
import shutil
import ast
import argparse
import hashlib
import traceback
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.task_executor import execute_task
from tools.api_caller import create_llm_client
from tools.runtime_registry import RuntimeToolRegistry

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# ============================================================================
# CONFIGURATION & INITIALIZATION
# ============================================================================

class Config:
    """Load and manage configuration"""
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "llm": {"provider": "openai", "model": "gpt-4", "temperature": 0.7},
            "execution": {"max_iterations": 10, "timeout_per_iteration": 300},
            "agent": {"name": "RepaI", "version": "1.0"},
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


# ============================================================================
# FILE MANAGEMENT
# ============================================================================

class FileManager:
    """Manage reading/writing markdown and python files"""
    
    @staticmethod
    def read_markdown(filepath: str) -> str:
        """Read a markdown file"""
        path = Path(filepath)
        if not path.exists():
            return ""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def write_markdown(filepath: str, content: str) -> bool:
        """Write content to markdown file"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False
    
    @staticmethod
    def append_markdown(filepath: str, content: str) -> bool:
        """Append content to markdown file"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error appending to {filepath}: {e}")
            return False


# ============================================================================
# CORE AGENT
# ============================================================================

class EvolutionaryAgent:
    """
    Main agent that executes recursively and improves itself
    """
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.iteration = 1
        self.max_iterations = self.config.get("execution", {}).get("max_iterations", 10)
        self.timeout_per_iteration = self.config.get("execution", {}).get("timeout_per_iteration", 300)
        self.debug_mode = self.config.get("execution", {}).get("debug_mode", False)
        self.logging_config = self.config.get("logging", {})
        self.evolution_config = self.config.get("evolution", {})
        self.registry_config = self.config.get("registry", {})
        self.iteration_log_path = self.logging_config.get("iteration_log", "iteration_log.md")
        self.evolution_enabled = self.evolution_config.get("enabled", True)
        self.max_tasks_per_iteration = self.evolution_config.get("max_tasks_per_iteration", 12)
        self.evolution_interval = max(1, int(self.evolution_config.get("full_update_interval", 2)))
        legacy_evolution_budget = int(self.evolution_config.get("max_tokens", 1200))
        self.evolution_max_tokens_base = max(
            400,
            int(self.evolution_config.get("max_tokens_base", legacy_evolution_budget)),
        )
        self.evolution_max_tokens_with_code = max(
            self.evolution_max_tokens_base,
            int(self.evolution_config.get("max_tokens_with_code", 2400)),
        )
        self.workspace_scan_interval = max(1, int(self.config.get("execution", {}).get("workspace_scan_interval", 5)))
        self.auto_fix_max_attempts = max(1, int(self.config.get("execution", {}).get("auto_fix_max_attempts", 3)))
        self.file_mgr = FileManager()
        self.runtime_registry = RuntimeToolRegistry(
            load_system_prompt=self.load_system_prompt,
            analyze_iteration_log=self._analyze_iteration_log,
            plan_next_iteration=self._plan_next_iteration_from_analysis,
            strict_mode=bool(self.registry_config.get("strict_mode", True)),
        )
        self.error_memory: Dict[str, Dict[str, Any]] = {}
        self.active_blockers: List[Dict[str, str]] = []
        self.todo_fingerprint_history: List[str] = []
        self.start_time = datetime.now()
        self._prepare_iteration_log()

    @staticmethod
    def _needs_code_budget(todos: List[str], llm_summary: str) -> bool:
        """Return True when context suggests code-file generation is likely needed."""
        text = "\n".join(todos + [llm_summary or ""]).lower()
        code_markers = [
            "code_files",
            "tools/",
            "create file",
            "write file",
            "implement",
            "refactor",
            ".py",
            "unit test",
            "generate",
        ]
        return any(marker in text for marker in code_markers)

    @staticmethod
    def _extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON payload from plain text or fenced markdown block.
        
        Uses brace-counting to correctly find the end of the root JSON object,
        even when code_files content contains nested braces.
        """
        if not text:
            return None

        # Direct parse attempt first
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Find start of JSON object
        start = text.find("{")
        if start == -1:
            return None

        # Walk forward counting braces to find the matching closing brace
        depth = 0
        in_string = False
        escape_next = False
        end = -1
        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end == -1:
            return None

        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

        return None

    def _build_todo_content(self, tasks: List[str]) -> str:
        """Build the markdown content for todo.md from task list."""
        cleaned = [task.strip() for task in tasks if task and task.strip()]
        if not cleaned:
            cleaned = ["Review previous iteration results and define next concrete improvement"]

        capped = cleaned[: self.max_tasks_per_iteration]
        task_lines = "\n".join(f"- [ ] {task}" for task in capped)
        return (
            "# TODO - RepaI Task Backlog\n\n"
            f"## Itération {self.iteration + 1} - Auto-generated\n\n"
            "### Priorités\n"
            f"{task_lines}\n\n"
            "---\n\n"
            f"**Itération courante** : {self.iteration + 1}\n"
            "**Généré automatiquement** : yes\n"
        )

    @staticmethod
    def _is_meta_task(task: str) -> bool:
        """Return True when a task is mostly planning/reflection instead of implementation."""
        lowered = task.lower()
        meta_markers = [
            "analyze",
            "analysis",
            "plan",
            "read",
            "review",
            "summar",
            "update system_prompt",
            "write todo",
            "iteration_log",
            "self-reflection",
        ]
        return any(marker in lowered for marker in meta_markers)

    def _normalize_evolution_plan(self, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and rebalance plans that are too meta/repetitive."""
        if not isinstance(plan, dict):
            return None

        next_tasks_raw = plan.get("next_tasks", [])
        if not isinstance(next_tasks_raw, list):
            next_tasks_raw = []

        deduped_tasks: List[str] = []
        for task in next_tasks_raw:
            task_text = str(task).strip()
            if task_text and task_text not in deduped_tasks:
                deduped_tasks.append(task_text)

        code_files = plan.get("code_files")
        valid_code_files = []
        if isinstance(code_files, list):
            for entry in code_files:
                if not isinstance(entry, dict):
                    continue
                path = str(entry.get("path", "")).strip()
                content = entry.get("content")
                if path.endswith(".py") and isinstance(content, str) and content.strip():
                    valid_code_files.append(entry)

        meta_count = sum(1 for task in deduped_tasks if self._is_meta_task(task))
        meta_ratio = (meta_count / len(deduped_tasks)) if deduped_tasks else 1.0
        has_concrete_task = any(not self._is_meta_task(task) for task in deduped_tasks)
        has_code_deliverable = len(valid_code_files) > 0
        executable_ratio = (
            sum(1 for task in deduped_tasks if self._parse_tool_call(task) is not None) / len(deduped_tasks)
            if deduped_tasks else 0.0
        )

        if meta_ratio >= 0.7 and not has_concrete_task and not has_code_deliverable:
            fallback_tasks = [
                "Implement one missing tool module in tools/ and include complete Python code",
                "Add or update at least one unit test covering new or changed tool behavior",
                "Run a local validation command and record concrete pass/fail output in iteration_log.md",
            ]
            deduped_tasks = (fallback_tasks + deduped_tasks)[: self.max_tasks_per_iteration]
            existing_notes = str(plan.get("notes", "")).strip()
            correction = "Auto-corrected meta-heavy plan with concrete implementation tasks."
            plan["notes"] = f"{correction} {existing_notes}".strip()

        if executable_ratio < 0.6:
            executable_fallback = self._default_executable_tasks()
            deduped_tasks = executable_fallback[: self.max_tasks_per_iteration]
            existing_notes = str(plan.get("notes", "")).strip()
            correction = "Auto-corrected non-executable tasks to explicit tool-call format."
            plan["notes"] = f"{correction} {existing_notes}".strip()

        plan["next_tasks"] = deduped_tasks[: self.max_tasks_per_iteration]
        return plan

    def ask_llm_for_evolution_plan(self, system_prompt: str, todos: List[str], llm_summary: str) -> Dict[str, Any]:
        """Ask the LLM for concrete updates to todo.md and system_prompt.md."""
        client = self.get_llm_client()
        if client is None:
            return {
                "success": False,
                "error": "No LLM client configured.",
                "plan": None,
            }

        task_preview = "\n".join(f"- {todo}" for todo in todos[:6]) or "- No pending tasks"
        prompt = (
            "You are evolving a recursive coding agent. Return ONLY valid JSON with this schema:\n"
            "{\n"
            "  \"next_tasks\": [\"task 1\", \"task 2\"],\n"
            "  \"system_prompt_update\": \"full replacement text for system_prompt.md\",\n"
            "  \"code_files\": [\n"
            "    {\"path\": \"tools/my_module.py\", \"content\": \"# full file content\"}\n"
            "  ],\n"
            "  \"notes\": \"short explanation\"\n"
            "}\n"
            "Rules:\n"
            "- next_tasks must contain 5 to 12 concrete tasks.\n"
            "- system_prompt_update must stay concise and actionable.\n"
            "- code_files is optional. Only include it when you are ready to write real, working Python code.\n"
            "- Each path in code_files must be a relative path inside the project (e.g. tools/tool_registry.py). No path traversal.\n"
            "- Only write .py files. content must be the full file content, not a snippet.\n"
            "- At least 30% of next_tasks must be concrete build/test/implementation tasks (not only analysis/planning).\n"
            "- Every item in next_tasks MUST be an explicit tool call string formatted exactly as tool_name.method_name(arg=\"value\").\n"
            "- Only use canonical tool calls from this allow-list: "
            f"{', '.join(self.runtime_registry.allowed_call_strings())}.\n"
            "- Do not include markdown code fences anywhere in the JSON.\n\n"
            f"Current system_prompt.md:\n{system_prompt[:1800]}\n\n"
            f"Current tasks:\n{task_preview}\n\n"
            f"Latest summary:\n{llm_summary[:600]}"
        )

        adaptive_budget = (
            self.evolution_max_tokens_with_code
            if self._needs_code_budget(todos, llm_summary)
            else self.evolution_max_tokens_base
        )

        raw_result = client.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            max_tokens=min(self.config.get("llm", {}).get("max_tokens", 2000), adaptive_budget),
            thinking_budget=0,
            response_schema={
                "type": "object",
                "required": ["next_tasks", "system_prompt_update", "notes"],
                "properties": {
                    "next_tasks": {
                        "type": "array",
                        "minItems": 5,
                        "maxItems": 12,
                        "items": {
                            "type": "string",
                            "pattern": "^[a-z_]+\\.[a-z_]+\\(.*\\)$",
                        },
                    },
                    "system_prompt_update": {"type": "string"},
                    "code_files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "content"],
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    "notes": {"type": "string"},
                },
            },
        )

        if not raw_result.get("success"):
            return {
                "success": False,
                "error": f"{raw_result.get('error', 'Unknown error')} (status={raw_result.get('status_code')})",
                "plan": None,
            }

        try:
            payload_text = raw_result["data"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return {
                "success": False,
                "error": "Could not parse LLM evolution response text.",
                "plan": None,
            }

        parsed = self._extract_json_payload(payload_text)
        if parsed is None:
            return {
                "success": False,
                "error": "LLM evolution response was not valid JSON.",
                "plan": None,
            }

        normalized = self._normalize_evolution_plan(parsed)
        if normalized is None:
            return {
                "success": False,
                "error": "LLM evolution plan was invalid or incomplete.",
                "plan": None,
            }

        return {
            "success": True,
            "error": None,
            "plan": normalized,
        }

    def apply_evolution_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply evolution plan by updating todo.md and system_prompt.md."""
        next_tasks = plan.get("next_tasks")
        system_prompt_update = plan.get("system_prompt_update")
        notes = plan.get("notes", "")

        result = {
            "todo_updated": False,
            "prompt_updated": False,
            "notes": notes,
            "errors": [],
        }

        if isinstance(next_tasks, list):
            todo_content = self._build_todo_content([str(task) for task in next_tasks])
            if self.file_mgr.write_markdown("todo.md", todo_content):
                result["todo_updated"] = True
            else:
                result["errors"].append("Failed to write todo.md")
        else:
            result["errors"].append("Invalid or missing next_tasks in evolution plan")

        if isinstance(system_prompt_update, str) and system_prompt_update.strip():
            if self.file_mgr.write_markdown("system_prompt.md", system_prompt_update.strip() + "\n"):
                result["prompt_updated"] = True
            else:
                result["errors"].append("Failed to write system_prompt.md")
        else:
            result["errors"].append("Invalid or missing system_prompt_update in evolution plan")

        code_files = plan.get("code_files")
        result["code_files_written"] = []
        if isinstance(code_files, list):
            for entry in code_files:
                if not isinstance(entry, dict):
                    continue
                file_path = entry.get("path", "").strip()
                content = entry.get("content", "")
                # Security: reject path traversal and non-.py files
                safe_path = Path(file_path)
                if ".." in safe_path.parts or not file_path.endswith(".py"):
                    result["errors"].append(f"Rejected unsafe/non-py path: {file_path}")
                    continue
                if not isinstance(content, str) or not content.strip():
                    result["errors"].append(f"Empty content for {file_path}, skipped")
                    continue
                try:
                    safe_path.parent.mkdir(parents=True, exist_ok=True)
                    safe_path.write_text(content, encoding="utf-8")
                    result["code_files_written"].append(file_path)
                    print(f"📝  Code file written: {file_path}")
                except Exception as exc:
                    result["errors"].append(f"Failed to write {file_path}: {exc}")

        return result

    def _prepare_iteration_log(self):
        """Prepare the iteration log file at startup based on logging settings."""
        reset_on_start = self.logging_config.get("reset_on_start", True)
        archive_iterations = self.logging_config.get("archive_iterations", True)
        log_path = Path(self.iteration_log_path)

        if not log_path.exists():
            self.file_mgr.write_markdown(self.iteration_log_path, self._build_log_header())
            return

        if not reset_on_start:
            return

        current_content = self.file_mgr.read_markdown(self.iteration_log_path)
        if archive_iterations and current_content.strip():
            archive_dir = Path("logs") / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = archive_dir / f"iteration_log_{timestamp}.md"
            shutil.copyfile(log_path, archive_file)
            print(f"🗂️  Previous log archived to {archive_file}")

        self.file_mgr.write_markdown(self.iteration_log_path, self._build_log_header())

    @staticmethod
    def _build_log_header() -> str:
        """Standard header written when starting a fresh iteration log."""
        return (
            "# Iteration Log\n\n"
            "## Historique d'exécution\n\n"
            "Chaque itération est documentée ci-dessous.\n\n"
            "---\n"
        )

    def get_llm_client(self):
        """Create an LLM client if the provider and API key are configured."""
        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "")
        api_key_ref = llm_config.get("api_key", "")
        api_key = ""

        if isinstance(api_key_ref, str) and api_key_ref.startswith("${") and api_key_ref.endswith("}"):
            env_name = api_key_ref[2:-1]
            api_key = os.getenv(env_name, "")
        elif isinstance(api_key_ref, str):
            api_key = api_key_ref

        if not provider or not api_key:
            return None

        try:
            return create_llm_client(
                provider=provider,
                api_key=api_key,
                model=llm_config.get("model"),
                timeout=self.timeout_per_iteration,
            )
        except Exception:
            return None

    def run_builtin_checks(self, full_scan: bool = True) -> List[Dict[str, Any]]:
        """Execute a small set of real checks so each iteration does visible work."""
        checks = []

        if full_scan:
            file_count = len(list(Path(".").glob("**/*")))
            scan_summary = f"Workspace scan complete: {file_count} paths detected."
        else:
            scan_summary = f"Workspace scan skipped on this iteration (interval={self.workspace_scan_interval})."
        checks.append({
            "name": "workspace_scan",
            "success": True,
            "summary": scan_summary,
        })

        python_check = execute_task(
            task_name="python_version",
            task_type="shell",
            content="python3 --version",
            timeout=10,
        )
        checks.append({
            "name": "python_version",
            "success": python_check.get("success", False),
            "summary": (python_check.get("output") or python_check.get("error") or "").strip(),
        })

        required_files = [
            "main.py",
            "config.yaml",
            "system_prompt.md",
            "todo.md",
            "tools/task_executor.py",
            "tools/api_caller.py",
        ]
        missing_files = [path for path in required_files if not Path(path).exists()]
        checks.append({
            "name": "required_files",
            "success": not missing_files,
            "summary": "All required files are present." if not missing_files else f"Missing files: {', '.join(missing_files)}",
        })

        return checks

    def ask_llm_for_iteration_summary(self, system_prompt: str, todos: List[str]) -> Dict[str, Any]:
        """Ask the configured LLM for a concise summary of what should happen next."""
        client = self.get_llm_client()
        if client is None:
            return {
                "mode": "dry_run",
                "summary": None,
                "error": "No LLM client configured from current environment.",
            }

        task_preview = "\n".join(f"- {todo}" for todo in todos[:4]) or "- No pending tasks"
        messages = [
            {
                "role": "user",
                "content": (
                    "You are summarizing the current iteration of a self-improving coding agent. "
                    "Return 3 short bullet points: 1) what the agent should do now, "
                    "2) the main risk, 3) the next concrete improvement.\n\n"
                    f"System prompt excerpt:\n{system_prompt[:700]}\n\n"
                    f"Pending tasks:\n{task_preview}"
                ),
            }
        ]

        raw_result = client.chat_completion(
            messages,
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            max_tokens=min(self.config.get("llm", {}).get("max_tokens", 2000), 220),
        )

        if not raw_result.get("success"):
            return {
                "mode": "llm_error",
                "summary": None,
                "error": f"{raw_result.get('error', 'Unknown error')} (status={raw_result.get('status_code')})",
            }

        try:
            summary = raw_result["data"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return {
                "mode": "llm_error",
                "summary": None,
                "error": "LLM response could not be parsed.",
            }

        return {
            "mode": "llm_enabled",
            "summary": summary,
            "error": None,
        }
    
    def load_system_prompt(self) -> str:
        """Load system prompt from markdown"""
        return self.file_mgr.read_markdown("system_prompt.md")
    
    def load_todos(self) -> List[str]:
        """Parse TODO tasks from markdown"""
        content = self.file_mgr.read_markdown("todo.md")
        # Simple parsing: extract unchecked items
        todos = []
        for line in content.split('\n'):
            if line.strip().startswith("- [ ]"):
                task = line.replace("- [ ]", "").strip()
                if task:
                    todos.append(task)
        return todos

    @staticmethod
    def _parse_tool_call(task: str) -> Optional[Dict[str, Any]]:
        """Parse a task string in the form tool.method(arg="value")."""
        try:
            node = ast.parse(task, mode="eval")
        except SyntaxError:
            return None

        expr = node.body
        if not isinstance(expr, ast.Call):
            return None
        if not isinstance(expr.func, ast.Attribute):
            return None
        if not isinstance(expr.func.value, ast.Name):
            return None

        tool = expr.func.value.id
        method = expr.func.attr
        kwargs: Dict[str, Any] = {}
        for kw in expr.keywords:
            if kw.arg is None:
                return None
            try:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            except Exception:
                return None

        return {
            "tool": tool,
            "method": method,
            "kwargs": kwargs,
        }

    def _analyze_iteration_log(self, log_text: str) -> str:
        """Create a compact analysis summary from iteration log content."""
        lines = log_text.splitlines()
        total_iterations = sum(1 for line in lines if line.startswith("### Itération"))
        warnings = sum(1 for line in lines if "WARN" in line or "⚠️" in line)
        evol_applied = sum(1 for line in lines if "**Application d'évolution** : applied" in line)
        return (
            f"iterations={total_iterations}; evolution_applied={evol_applied}; "
            f"warnings={warnings}; recommendation=prioritize concrete tool/test implementation"
        )

    def _plan_next_iteration_from_analysis(self, analysis: str) -> str:
        """Generate deterministic concrete tasks from analysis text."""
        tasks = [
            "Implement one concrete Python tool in tools/ with complete function bodies",
            "Add at least one unit test for a changed or new tool",
            "Run a local validation command and record output in iteration_log.md",
            "Update tools.md to document any newly added tool",
            f"Review analysis summary and adjust backlog priorities: {analysis[:100]}",
        ]
        return self._build_todo_content(tasks)

    def _default_executable_tasks(self) -> List[str]:
        """Default executable task chain used as local fallback."""
        return [
            "file_manager.read_file(path=\"iteration_log.md\")",
            "analyze_results.analyze_iteration_log(log_content=\"[RESULTS_FROM_file_manager.read_file(path=\\\"iteration_log.md\\\")]\")",
            "file_manager.read_file(path=\"system_prompt.md\")",
            "system_prompt_manager.update_system_prompt(current_prompt=\"[RESULTS_FROM_file_manager.read_file(path=\\\"system_prompt.md\\\")]\", analysis_results=\"[RESULTS_FROM_analyze_results.analyze_iteration_log]\")",
            "file_manager.write_file(path=\"system_prompt.md\", content=\"[RESULTS_FROM_system_prompt_manager.update_system_prompt]\")",
            "plan_next_iteration.plan(analysis_results=\"[RESULTS_FROM_analyze_results.analyze_iteration_log]\")",
            "file_manager.write_file(path=\"todo.md\", content=\"[RESULTS_FROM_plan_next_iteration.plan]\")",
            "shell_executor.execute_shell_command(command=\"python3 --version\", timeout=15)",
        ]

    @staticmethod
    def _todo_fingerprint(todos: List[str]) -> str:
        normalized = "\n".join(task.strip().lower() for task in todos[:12])
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def _is_stagnating(self, todos: List[str]) -> bool:
        if len(todos) == 0:
            return False
        fp = self._todo_fingerprint(todos)
        recent = self.todo_fingerprint_history[-2:]
        return len(recent) == 2 and recent[0] == fp and recent[1] == fp

    @staticmethod
    def _extract_error_signature(error_text: str) -> str:
        first_line = (error_text or "").strip().splitlines()[0] if error_text else "unknown_error"
        return first_line[:220]

    def _register_error(self, task: str, error_text: str):
        signature = self._extract_error_signature(error_text)
        entry = self.error_memory.get(signature, {"count": 0, "last_task": ""})
        entry["count"] += 1
        entry["last_task"] = task
        self.error_memory[signature] = entry

    def _build_blocker_tasks(self, blockers: List[Dict[str, str]]) -> List[str]:
        tasks = []
        for blocker in blockers[:3]:
            task = blocker.get("task", "")
            error = blocker.get("error", "")
            if "SyntaxError" in error:
                tasks.append("shell_executor.execute_shell_command(command=\"python3 -m unittest tests/test_documentation.py\", timeout=30)")
            if "File not found:" in error:
                missing = error.split("File not found:", 1)[-1].strip()
                tasks.append(f"file_manager.write_file(path=\"{missing}\", content=\"# Auto-created placeholder to unblock execution\\n\")")
            if task.startswith("shell_executor.execute_shell_command"):
                tasks.append(task)

        tasks.append("analyze_results.analyze_iteration_log(log_path=\"iteration_log.md\")")
        deduped = []
        for task in tasks:
            if task and task not in deduped:
                deduped.append(task)
        return deduped[: self.max_tasks_per_iteration]

    @staticmethod
    def _extract_syntax_error_location(error_text: str) -> Optional[Dict[str, Any]]:
        lines = (error_text or "").splitlines()
        file_path = None
        line_no = None
        for line in lines:
            marker = 'File "'
            if marker in line and '", line ' in line:
                try:
                    start = line.index(marker) + len(marker)
                    mid = line.index('", line ', start)
                    file_path = line[start:mid]
                    line_no = int(line[mid + 8:].strip())
                except Exception:
                    continue
        if file_path and line_no:
            return {"path": file_path, "line": line_no}
        return None

    def _auto_fix_task_failure(self, parsed: Dict[str, Any], result: Dict[str, Any]) -> bool:
        error_text = str(result.get("error") or "")
        location = self._extract_syntax_error_location(error_text)
        if not location or "SyntaxError: unmatched ')'" not in error_text:
            return False

        target = Path(location["path"])
        if not target.exists():
            return False
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            idx = location["line"] - 1
            if idx < 0 or idx >= len(lines):
                return False
            line = lines[idx]
            if ")" not in line:
                return False
            lines[idx] = line.replace(")", "", 1) if line.count(")") == 1 else line[::-1].replace(")", "", 1)[::-1]
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
        except Exception:
            return False

    def execute_todos(self, todos: List[str]) -> List[Dict[str, Any]]:
        """Execute tool-call tasks from todo.md and keep a result map for chaining."""
        execution_results: List[Dict[str, Any]] = []
        result_map: Dict[str, Any] = {}

        for task in todos:
            parsed = self._parse_tool_call(task)
            if parsed is None:
                execution_results.append({
                    "task": task,
                    "success": False,
                    "error": "Task is not a parsable tool call (tool.method(...))",
                })
                continue

            result = self.runtime_registry.execute(parsed, result_map)
            if not result.get("success") and parsed.get("tool") == "shell_executor" and parsed.get("method") == "execute_shell_command":
                for _ in range(self.auto_fix_max_attempts):
                    if not self._auto_fix_task_failure(parsed, result):
                        break
                    retry = self.runtime_registry.execute(parsed, result_map)
                    if retry.get("success"):
                        result = retry
                        break
                    result = retry

            call_key = f"{parsed['tool']}.{parsed['method']}"
            output_value = result.get("output") if result.get("success") else result.get("error", "")
            result_map[task] = output_value
            normalized_tool, normalized_method = self.runtime_registry.normalize_call(parsed["tool"], parsed["method"])
            if (normalized_tool, normalized_method) != (parsed["tool"], parsed["method"]):
                result_map[f"{normalized_tool}.{normalized_method}"] = output_value
            result_map[call_key] = output_value

            if not result.get("success"):
                self._register_error(task, str(result.get("error") or ""))

            execution_results.append({
                "task": task,
                "success": result.get("success", False),
                "error": result.get("error"),
                "output_preview": str(output_value)[:160],
            })

        return execution_results
    
    def execute_iteration(self) -> Dict[str, Any]:
        """
        Execute a single iteration:
        1. Load prompt & todos
        2. Prepare task execution
        3. Log results
        4. Prepare evolution for next iteration
        """
        iteration_start = datetime.now()

        print(f"\n{'='*60}")
        print(f"ITERATION {self.iteration}")
        print(f"{'='*60}\n")
        
        iteration_data = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "prompt_version": self.load_system_prompt()[:50],
            "todos": self.load_todos(),
            "status": "in_progress",
            "mode": "dry_run",
            "checks": [],
            "llm_summary": None,
            "llm_error": None,
            "evolution_applied": False,
            "evolution_notes": None,
            "evolution_errors": [],
            "task_results": [],
        }
        
        # Load system prompt
        system_prompt = self.load_system_prompt()
        if not system_prompt:
            print("⚠️  System prompt is empty. Initializing...")
            system_prompt = "Initialize system prompt"
        
        # Load TODOs
        todos = self.load_todos()
        if self.active_blockers:
            blocker_tasks = self._build_blocker_tasks(self.active_blockers)
            if blocker_tasks:
                todos = blocker_tasks + [task for task in todos if task not in blocker_tasks]
                print(f"🚧 Blocker-first mode: injected {len(blocker_tasks)} remediation task(s)")

        if self._is_stagnating(todos):
            todos = self._default_executable_tasks()
            print("♻️  Stagnation detected: switched to corrective default task chain")

        self.todo_fingerprint_history.append(self._todo_fingerprint(todos))
        self.todo_fingerprint_history = self.todo_fingerprint_history[-8:]

        print(f"📋 Loaded {len(todos)} tasks")
        for i, todo in enumerate(todos[:3], 1):  # Show first 3
            print(f"   {i}. {todo[:50]}...")

        iteration_data["task_results"] = self.execute_todos(todos)
        executed_ok = sum(1 for res in iteration_data["task_results"] if res.get("success"))
        executed_total = len(iteration_data["task_results"])
        print(f"🧪 Executed TODO tool calls: {executed_ok}/{executed_total} succeeded")

        blockers = [
            {"task": res.get("task", ""), "error": str(res.get("error") or "")}
            for res in iteration_data["task_results"]
            if not res.get("success")
        ]
        iteration_data["blockers"] = blockers
        self.active_blockers = blockers

        critical_test_tasks = [
            res for res in iteration_data["task_results"]
            if "python -m unittest" in (res.get("task") or "")
        ]
        critical_test_passed = any(res.get("success") for res in critical_test_tasks)
        iteration_data["critical_test_passed"] = critical_test_passed

        do_full_scan = self.iteration == 1 or self.iteration % self.workspace_scan_interval == 0
        iteration_data["checks"] = self.run_builtin_checks(full_scan=do_full_scan)
        print("🔎 Built-in checks:")
        for check in iteration_data["checks"]:
            icon = "✅" if check["success"] else "⚠️"
            print(f"   {icon} {check['name']}: {check['summary']}")

        llm_result = self.ask_llm_for_iteration_summary(system_prompt, todos)
        iteration_data["mode"] = llm_result.get("mode", "dry_run")
        iteration_data["llm_summary"] = llm_result.get("summary")
        iteration_data["llm_error"] = llm_result.get("error")

        if iteration_data["llm_summary"]:
            print("🧠 LLM summary generated for this iteration")
            preview = iteration_data["llm_summary"].replace("\n", " ").strip()
            print(f"   Preview: {preview[:180]}{'...' if len(preview) > 180 else ''}")
            if self.debug_mode:
                print("   Full summary:")
                for line in iteration_data["llm_summary"].splitlines():
                    print(f"     {line}")
        elif iteration_data["mode"] == "llm_error":
            print(f"⚠️  LLM call failed: {iteration_data['llm_error']}")
        else:
            print(f"ℹ️  Running in dry-run mode: {iteration_data['llm_error']}")

        should_run_evolution = (
            self.evolution_enabled
            and iteration_data["llm_summary"]
            and (self.iteration == 1 or self.iteration % self.evolution_interval == 0)
        )
        if should_run_evolution:
            evolution_result = self.ask_llm_for_evolution_plan(system_prompt, todos, iteration_data["llm_summary"])
            if evolution_result["success"]:
                applied = self.apply_evolution_plan(evolution_result["plan"])
                iteration_data["evolution_applied"] = applied["todo_updated"] or applied["prompt_updated"]
                iteration_data["evolution_notes"] = applied.get("notes") or evolution_result["plan"].get("notes")
                iteration_data["evolution_errors"] = applied.get("errors", [])
                if iteration_data["evolution_applied"]:
                    print("🛠️  Evolution applied: updated todo.md and/or system_prompt.md")
                code_written = applied.get("code_files_written", [])
                if code_written:
                    print(f"🧬  Code evolution: {len(code_written)} file(s) written → {', '.join(code_written)}")
                if iteration_data["evolution_errors"]:
                    print(f"⚠️  Evolution issues: {'; '.join(iteration_data['evolution_errors'])}")
            else:
                iteration_data["evolution_errors"] = [evolution_result["error"]]
                print(f"⚠️  Evolution plan generation failed: {evolution_result['error']}")
        elif self.evolution_enabled and iteration_data["llm_summary"]:
            iteration_data["evolution_notes"] = (
                f"Skipped full evolution this iteration to reduce churn "
                f"(full_update_interval={self.evolution_interval})."
            )
            print(
                "⏭️  Evolution skipped this iteration "
                f"(full_update_interval={self.evolution_interval})"
            )
        
        if blockers and not critical_test_passed:
            iteration_data["status"] = "blocked"
        else:
            iteration_data["status"] = "completed"
        iteration_data["execution_time"] = (datetime.now() - iteration_start).total_seconds()
        
        self._log_iteration(iteration_data)
        
        return iteration_data
    
    def _log_iteration(self, data: Dict[str, Any]):
        """Log iteration results"""
        checks_block = "\n".join(
            f"- {'OK' if check['success'] else 'WARN'} {check['name']}: {check['summary']}"
            for check in data.get("checks", [])
        ) or "- No checks executed"

        task_results = data.get("task_results", [])
        tasks_block = "\n".join(
            f"- {'OK' if task.get('success') else 'WARN'} {task.get('task')}: {task.get('output_preview') or task.get('error', '')}"
            for task in task_results[:10]
        ) or "- No tasks executed"

        llm_block = data.get("llm_summary") or f"No LLM summary generated during this iteration. {data.get('llm_error', '')}".strip()
        evolution_errors = data.get("evolution_errors", [])
        evolution_status = "applied" if data.get("evolution_applied") else "not_applied"
        evolution_notes = data.get("evolution_notes") or "No evolution notes provided."
        evolution_error_block = "\n".join(f"- {err}" for err in evolution_errors) if evolution_errors else "- None"
        log_entry = f"""
### Itération {data['iteration']}
**Timestamp** : {data['timestamp']}  
**Status** : {data['status']}  
**Mode** : {data.get('mode', 'unknown')}  
**Temps d'exécution** : {data.get('execution_time', 0):.2f}s  
**Tâches traitées** : {len(data.get('todos', []))}  

**Exécution des tâches TODO** :
{tasks_block}

**Vérifications exécutées** :
{checks_block}

**Résumé LLM / évolution** :
{llm_block}

**Application d'évolution** : {evolution_status}
**Notes d'évolution** : {evolution_notes}
**Erreurs d'évolution** :
{evolution_error_block}

---
"""
        self.file_mgr.append_markdown(self.iteration_log_path, log_entry)
        print(f"✅ Iteration {self.iteration} logged")
    
    def run(self):
        """Main execution loop"""
        print(f"\n🚀 Starting {self.config.get('agent', {}).get('name', 'RepaI')}")
        print(f"   Max iterations: {self.max_iterations}\n")
        
        while self.iteration <= self.max_iterations:
            try:
                self.execute_iteration()
                self.iteration += 1
                
                # Simple sleep to avoid tight loops during dev
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\n⏹️  Agent interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error in iteration {self.iteration}: {e}")
                self.iteration += 1
        
        print(f"\n✨ Agent completed {self.iteration - 1} iterations")
        print(f"   Total time: {(datetime.now() - self.start_time).total_seconds():.2f}s")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Run RepaI evolutionary agent")
    parser.add_argument(
        "iterations",
        nargs="?",
        type=int,
        help="Optional positional override for max iterations",
    )
    parser.add_argument(
        "-n",
        "--iterations",
        dest="iterations_flag",
        type=int,
        help="Override max iterations from config",
    )
    args = parser.parse_args()

    iterations_override = args.iterations_flag if args.iterations_flag is not None else args.iterations
    if iterations_override is not None and iterations_override < 1:
        parser.error("iterations must be >= 1")

    config = Config()
    agent = EvolutionaryAgent(config)
    if iterations_override is not None:
        agent.max_iterations = iterations_override
        print(f"🧮 Max iterations overridden by CLI: {iterations_override}")
    agent.run()


if __name__ == "__main__":
    main()
