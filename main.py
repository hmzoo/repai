#!/usr/bin/env python3
"""
RepaI - Recursive Evolutionary Programming Agent
Main orchestrator for self-improving application
"""

import os
import sys
import json
import time
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
        self.file_mgr = FileManager()
        self.start_time = datetime.now()

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
        elif iteration_data["mode"] == "llm_error":
            print(f"⚠️  LLM call failed: {iteration_data['llm_error']}")
        else:
            print(f"ℹ️  Running in dry-run mode: {iteration_data['llm_error']}")
        
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

---
"""
        self.file_mgr.append_markdown("iteration_log.md", log_entry)
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
