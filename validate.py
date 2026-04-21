#!/usr/bin/env python3
"""
Quick validation script for RepaI project
Checks that everything is working before full run
"""

import sys
import os

def check_file_exists(filepath):
    """Check if file exists"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"  {status} {filepath}")
    return exists

def check_python_syntax(filepath):
    """Check Python file syntax"""
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        print(f"  ✅ {filepath} (syntax OK)")
        return True
    except SyntaxError as e:
        print(f"  ❌ {filepath} (syntax error: {e})")
        return False
    except Exception as e:
        print(f"  ⚠️  {filepath} ({e})")
        return True  # Not a syntax issue

def check_imports():
    """Check if imports work"""
    try:
        sys.path.insert(0, '/home/mrpink/perso/repai')
        from main import Config, EvolutionaryAgent, FileManager
        print("  ✅ Core imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def check_config():
    """Check if config loads"""
    try:
        sys.path.insert(0, '/home/mrpink/perso/repai')
        from main import Config
        config = Config()
        print(f"  ✅ Config loaded (llm provider: {config.get('llm', {}).get('provider', 'N/A')})")
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False

def check_agent_init():
    """Check if agent initializes"""
    try:
        sys.path.insert(0, '/home/mrpink/perso/repai')
        from main import Config, EvolutionaryAgent
        config = Config()
        # Limit iterations for test
        config.data['execution']['max_iterations'] = 1
        agent = EvolutionaryAgent(config)
        print(f"  ✅ Agent initialized (max_iterations=1 for test)")
        return True
    except Exception as e:
        print(f"  ❌ Agent init error: {e}")
        return False

def check_file_operations():
    """Check file read/write"""
    try:
        sys.path.insert(0, '/home/mrpink/perso/repai')
        from main import FileManager
        fm = FileManager()
        
        # Test read
        content = fm.read_markdown("system_prompt.md")
        if content:
            print(f"  ✅ File read works ({len(content)} bytes)")
        else:
            print(f"  ⚠️  File read returned empty")
        return True
    except Exception as e:
        print(f"  ❌ File operation error: {e}")
        return False

def check_tools():
    """Check if tools load"""
    try:
        sys.path.insert(0, '/home/mrpink/perso/repai')
        from tools.task_executor import execute_task
        from tools.api_caller import APIClient
        print(f"  ✅ Tools import successful")
        return True
    except Exception as e:
        print(f"  ❌ Tools error: {e}")
        return False

def main():
    """Run all checks"""
    print("""
    ╔════════════════════════════════════════╗
    ║   RepaI Project - Validation Suite     ║
    ║   Checking everything is ready...      ║
    ╚════════════════════════════════════════╝
    """)
    
    all_pass = True
    checks = []
    
    # File structure checks
    print("\n📁 Checking File Structure...")
    required_files = [
        "main.py",
        "config.yaml",
        "system_prompt.md",
        "todo.md",
        "tools.md",
        "example.py",
        "tools/__init__.py",
        "tools/task_executor.py",
        "tools/api_caller.py",
        "README.md",
        "SYNTHESE.md",
        "ARCHITECTURE.md",
        "PROPOSITIONS.md",
        "ITERATION_1_PLAN.md",
    ]
    
    for file in required_files:
        filepath = f"/home/mrpink/perso/repai/{file}"
        if not check_file_exists(filepath):
            all_pass = False
    
    # Python syntax checks
    print("\n🐍 Checking Python Syntax...")
    python_files = [
        "/home/mrpink/perso/repai/main.py",
        "/home/mrpink/perso/repai/example.py",
        "/home/mrpink/perso/repai/tools/__init__.py",
        "/home/mrpink/perso/repai/tools/task_executor.py",
        "/home/mrpink/perso/repai/tools/api_caller.py",
    ]
    
    for file in python_files:
        if not check_python_syntax(file):
            all_pass = False
    
    # Import checks
    print("\n📦 Checking Imports...")
    if not check_imports():
        all_pass = False
    
    # Config check
    print("\n⚙️  Checking Configuration...")
    if not check_config():
        all_pass = False
    
    # Agent initialization
    print("\n🤖 Checking Agent Initialization...")
    if not check_agent_init():
        all_pass = False
    
    # File operations
    print("\n📝 Checking File Operations...")
    if not check_file_operations():
        all_pass = False
    
    # Tools
    print("\n🛠️  Checking Tools...")
    if not check_tools():
        all_pass = False
    
    # Summary
    print("\n" + "="*40)
    if all_pass:
        print("✅ ALL CHECKS PASSED!")
        print("\n🚀 Project is ready! Run with:")
        print("   python main.py")
        print("   or")
        print("   python example.py")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n⚠️  Fix issues above before running")
        return 1

if __name__ == "__main__":
    sys.exit(main())
