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
        self.file_mgr = FileManager()
        self.start_time = datetime.now()
    
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
            "status": "in_progress"
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
        
        # Here you would:
        # - Call LLM with system_prompt
        # - Execute tasks
        # - Collect results
        # - Generate improvements
        
        iteration_data["status"] = "completed"
        iteration_data["execution_time"] = (datetime.now() - self.start_time).total_seconds()
        
        self._log_iteration(iteration_data)
        
        return iteration_data
    
    def _log_iteration(self, data: Dict[str, Any]):
        """Log iteration results"""
        log_entry = f"""
### Itération {data['iteration']}
**Timestamp** : {data['timestamp']}  
**Status** : {data['status']}  
**Temps d'exécution** : {data.get('execution_time', 0):.2f}s  
**Tâches traitées** : {len(data.get('todos', []))}  

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
