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
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.task_executor import execute_task
from tools.api_caller import create_llm_client

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
        self.iteration_log_path = self.logging_config.get("iteration_log", "iteration_log.md")
        self.evolution_enabled = self.evolution_config.get("enabled", True)
        self.max_tasks_per_iteration = self.evolution_config.get("max_tasks_per_iteration", 12)
        self.file_mgr = FileManager()
        self.start_time = datetime.now()
        self._prepare_iteration_log()

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

    def ask_llm_for_evolution_plan(self, system_prompt: str, todos: List[str], llm_summary: str) -> Dict[str, Any]:
        """Ask the LLM for concrete updates to todo.md and system_prompt.md."""
        client = self.get_llm_client()
        if client is None:
            return {
                "success": False,
                "error": "No LLM client configured.",
                "plan": None,
            }

        task_preview = "\n".join(f"- {todo}" for todo in todos[:8]) or "- No pending tasks"
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
            "- Do not include markdown code fences anywhere in the JSON.\n\n"
            f"Current system_prompt.md:\n{system_prompt[:3500]}\n\n"
            f"Current tasks:\n{task_preview}\n\n"
            f"Latest summary:\n{llm_summary[:1200]}"
        )

        raw_result = client.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            max_tokens=min(self.config.get("llm", {}).get("max_tokens", 8000), 8000),
            thinking_budget=0,
            response_schema={
                "type": "object",
                "required": ["next_tasks", "system_prompt_update", "notes"],
                "properties": {
                    "next_tasks": {
                        "type": "array",
                        "minItems": 5,
                        "maxItems": 12,
                        "items": {"type": "string"},
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

        return {
            "success": True,
            "error": None,
            "plan": parsed,
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

    def run_builtin_checks(self) -> List[Dict[str, Any]]:
        """Execute a small set of real checks so each iteration does visible work."""
        checks = []

        file_count = len(list(Path(".").glob("**/*")))
        checks.append({
            "name": "workspace_scan",
            "success": True,
            "summary": f"Workspace scan complete: {file_count} paths detected.",
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

        task_preview = "\n".join(f"- {todo}" for todo in todos[:5]) or "- No pending tasks"
        messages = [
            {
                "role": "user",
                "content": (
                    "You are summarizing the current iteration of a self-improving coding agent. "
                    "Return 3 short bullet points: 1) what the agent should do now, "
                    "2) the main risk, 3) the next concrete improvement.\n\n"
                    f"System prompt excerpt:\n{system_prompt[:1200]}\n\n"
                    f"Pending tasks:\n{task_preview}"
                ),
            }
        ]

        raw_result = client.chat_completion(
            messages,
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            max_tokens=min(self.config.get("llm", {}).get("max_tokens", 2000), 300),
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
    
    def execute_iteration(self) -> Dict[str, Any]:
        """
        Execute a single iteration:
        1. Load prompt & todos
        2. Prepare task execution
        3. Log results
        4. Prepare evolution for next iteration
        """
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
        }
        
        # Load system prompt
        system_prompt = self.load_system_prompt()
        if not system_prompt:
            print("⚠️  System prompt is empty. Initializing...")
            system_prompt = "Initialize system prompt"
        
        # Load TODOs
        todos = self.load_todos()
        print(f"📋 Loaded {len(todos)} tasks")
        for i, todo in enumerate(todos[:3], 1):  # Show first 3
            print(f"   {i}. {todo[:50]}...")

        iteration_data["checks"] = self.run_builtin_checks()
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

        if self.evolution_enabled and iteration_data["llm_summary"]:
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
        
        iteration_data["status"] = "completed"
        iteration_data["execution_time"] = (datetime.now() - self.start_time).total_seconds()
        
        self._log_iteration(iteration_data)
        
        return iteration_data
    
    def _log_iteration(self, data: Dict[str, Any]):
        """Log iteration results"""
        checks_block = "\n".join(
            f"- {'OK' if check['success'] else 'WARN'} {check['name']}: {check['summary']}"
            for check in data.get("checks", [])
        ) or "- No checks executed"

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
    config = Config()
    agent = EvolutionaryAgent(config)
    agent.run()


if __name__ == "__main__":
    main()
