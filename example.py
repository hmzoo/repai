#!/usr/bin/env python3
"""
Example: How to run the evolutionary agent

This demonstrates the core concept of RepaI:
- Load system prompt
- Execute tasks
- Analyze results
- Improve itself
- Recurse
"""

import sys
sys.path.insert(0, '/home/mrpink/perso/repai')

from main import Config, EvolutionaryAgent

def main():
    """
    Example execution flow
    """
    
    print("""
    ╔═════════════════════════════════════════╗
    ║          RepaI - Example Run             ║
    ║   Self-Improving Python Agent           ║
    ╚═════════════════════════════════════════╝
    """)
    
    # 1. Load configuration
    print("📖 Loading configuration...")
    config = Config()
    print(f"   Provider: {config.get('llm', {}).get('provider')}")
    print(f"   Model: {config.get('llm', {}).get('model')}")
    print(f"   Max iterations: {config.get('execution', {}).get('max_iterations')}")
    
    # 2. Initialize agent
    print("\n🤖 Initializing agent...")
    agent = EvolutionaryAgent(config)
    
    # 3. Run the loop
    print("\n▶️  Starting recursive execution loop...")
    agent.run()
    
    print("\n✨ Agent execution complete!")
    print("   See 'iteration_log.md' for detailed results")
    print("   See 'system_prompt.md' for evolved instructions")


if __name__ == "__main__":
    main()
