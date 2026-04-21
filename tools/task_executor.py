"""
Task executor tool - runs commands and Python code
"""

import subprocess
import time
from typing import Dict, Any, Optional
import traceback


def execute_shell_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a shell command
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds
    
    Returns:
        {
            "success": bool,
            "output": str,
            "error": str | None,
            "execution_time": float,
            "return_code": int
        }
    """
    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        execution_time = time.time() - start_time
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "execution_time": execution_time,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Command timeout after {timeout}s",
            "execution_time": time.time() - start_time,
            "return_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "return_code": -1
        }


def execute_python_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python code in a subprocess
    
    Args:
        code: Python code to execute
        timeout: Timeout in seconds
    
    Returns:
        {
            "success": bool,
            "output": str,
            "error": str | None,
            "execution_time": float,
            "return_code": int
        }
    """
    # Write code to temp file and execute
    import tempfile
    import os
    
    start_time = time.time()
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        os.unlink(temp_file)
        execution_time = time.time() - start_time
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "execution_time": execution_time,
            "return_code": result.returncode
        }
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "execution_time": execution_time,
            "return_code": -1
        }


def execute_task(task_name: str, task_type: str, content: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a task (shell command or Python code)
    
    Args:
        task_name: Identifier for the task
        task_type: "shell" or "python"
        content: Command or code to execute
        timeout: Timeout in seconds
    
    Returns:
        Execution result with metadata
    """
    result = None
    
    if task_type == "shell":
        result = execute_shell_command(content, timeout)
    elif task_type == "python":
        result = execute_python_code(content, timeout)
    else:
        return {
            "success": False,
            "error": f"Unknown task type: {task_type}",
            "task_name": task_name
        }
    
    result["task_name"] = task_name
    result["task_type"] = task_type
    
    return result
