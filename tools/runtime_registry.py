"""
Runtime tool registry for executing TODO tool calls.
"""

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from tools.task_executor import execute_task


class RuntimeToolRegistry:
    """Centralized runtime registry with alias support for tool calls."""

    def __init__(
        self,
        load_system_prompt: Callable[[], str],
        analyze_iteration_log: Callable[[str], str],
        plan_next_iteration: Callable[[str], str],
        strict_mode: bool = True,
    ):
        self.load_system_prompt = load_system_prompt
        self.analyze_iteration_log = analyze_iteration_log
        self.plan_next_iteration = plan_next_iteration
        self.strict_mode = strict_mode
        self.allowed_calls = {
            ("file_manager", "read_file"),
            ("file_manager", "write_file"),
            ("file_manager", "append_file"),
            ("shell_executor", "execute_shell_command"),
            ("analyze_results", "analyze_iteration_log"),
            ("plan_next_iteration", "plan"),
            ("system_prompt_manager", "update_system_prompt"),
            ("tool_registry", "add_tool"),
        }
        self.aliases: Dict[Tuple[str, str], Tuple[str, str]] = {
            ("shell", "run"): ("shell_executor", "execute_shell_command"),
            ("file_manager", "create_file"): ("file_manager", "write_file"),
            ("file_manager", "append_to_file"): ("file_manager", "append_file"),
        }

    def allowed_call_strings(self):
        return sorted(f"{tool}.{method}" for tool, method in self.allowed_calls)

    @staticmethod
    def _resolve_placeholders(value: Any, results: Dict[str, Any]) -> Any:
        if not isinstance(value, str):
            return value

        pattern = re.compile(r"\[RESULTS_FROM_(.+?)\]")

        def replace(match: re.Match) -> str:
            key = match.group(1).strip()
            resolved = results.get(key)
            if resolved is None:
                return ""
            if isinstance(resolved, (dict, list)):
                try:
                    return json.dumps(resolved, ensure_ascii=False)
                except Exception:
                    return str(resolved)
            return str(resolved)

        return pattern.sub(replace, value)

    def normalize_call(self, tool: str, method: str) -> Tuple[str, str]:
        alias_target = self.aliases.get((tool, method))
        if self.strict_mode:
            return (tool, method)
        if alias_target is not None:
            return alias_target
        return (tool, method)

    def execute(self, parsed: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        source_tool = parsed["tool"]
        source_method = parsed["method"]
        tool, method = self.normalize_call(source_tool, source_method)

        alias_target = self.aliases.get((source_tool, source_method))
        if self.strict_mode and alias_target is not None:
            canonical = f"{alias_target[0]}.{alias_target[1]}"
            return {
                "success": False,
                "error": (
                    f"Non-canonical tool call rejected in strict mode: {source_tool}.{source_method}. "
                    f"Use canonical call: {canonical}"
                ),
            }

        if (tool, method) not in self.allowed_calls:
            allowed = ", ".join(self.allowed_call_strings())
            return {
                "success": False,
                "error": (
                    f"Unsupported canonical tool call: {tool}.{method}. "
                    f"Allowed calls: {allowed}"
                ),
            }

        kwargs = {
            key: self._resolve_placeholders(value, results)
            for key, value in parsed.get("kwargs", {}).items()
        }

        try:
            if tool == "file_manager" and method == "read_file":
                path = str(kwargs.get("path", "")).strip()
                if not path:
                    return {"success": False, "error": "Missing path"}
                target = Path(path)
                if not target.exists():
                    return {"success": False, "error": f"File not found: {path}"}
                content = target.read_text(encoding="utf-8")
                return {"success": True, "output": content}

            if tool == "file_manager" and method == "write_file":
                path = str(kwargs.get("path", "")).strip()
                content = str(kwargs.get("content", ""))
                if not path:
                    return {"success": False, "error": "Missing path"}
                target = Path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return {"success": True, "output": f"written:{path}"}

            if tool == "file_manager" and method == "append_file":
                path = str(kwargs.get("path", "")).strip()
                content = str(kwargs.get("content", ""))
                if not path:
                    return {"success": False, "error": "Missing path"}
                target = Path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "a", encoding="utf-8") as handle:
                    handle.write(content)
                return {"success": True, "output": f"appended:{path}"}

            if tool == "shell_executor" and method == "execute_shell_command":
                command = str(kwargs.get("command", "")).strip()
                timeout = int(kwargs.get("timeout", 30))
                if not command:
                    return {"success": False, "error": "Missing command"}
                result = execute_task("todo_shell", "shell", command, timeout=timeout)
                return {
                    "success": result.get("success", False),
                    "output": result.get("output", ""),
                    "error": result.get("error"),
                }

            if tool == "analyze_results" and method == "analyze_iteration_log":
                if "log_path" in kwargs:
                    log_path = Path(str(kwargs.get("log_path", "")))
                    if not log_path.exists():
                        return {"success": False, "error": f"Log file not found: {log_path}"}
                    log_text = log_path.read_text(encoding="utf-8")
                else:
                    log_text = str(kwargs.get("log_content", ""))
                return {"success": True, "output": self.analyze_iteration_log(log_text)}

            if tool == "plan_next_iteration" and method == "plan":
                analysis = str(kwargs.get("analysis_results", ""))
                return {"success": True, "output": self.plan_next_iteration(analysis)}

            if tool == "system_prompt_manager" and method == "update_system_prompt":
                new_content = str(kwargs.get("new_content", "")).strip()
                current_prompt = str(kwargs.get("current_prompt", "")).strip()
                analysis = str(kwargs.get("analysis_results", "")).strip()
                if new_content:
                    return {"success": True, "output": new_content}
                if not current_prompt:
                    current_prompt = self.load_system_prompt()
                update_note = "\n\n## Self-Update Note\n- Prompt reviewed by runtime registry.\n"
                if analysis:
                    update_note += f"- Latest analysis: {analysis[:200]}\n"
                return {"success": True, "output": current_prompt.rstrip() + update_note}

            if tool == "tool_registry" and method == "add_tool":
                tool_name = str(kwargs.get("tool_name", "unknown_tool"))
                return {"success": True, "output": f"registered:{tool_name}"}

            return {"success": False, "error": f"Unsupported tool call: {tool}.{method}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
