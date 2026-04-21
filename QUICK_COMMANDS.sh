#!/usr/bin/env bash
# Quick Command Reference for RepaI Project
# Copy-paste commands to get started quickly

# ============================================================================
# INSTALLATION & SETUP
# ============================================================================

# 1. Automated setup (recommended)
cd /home/mrpink/perso/repai && bash install.sh

# 2. Manual setup
cd /home/mrpink/perso/repai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ============================================================================
# BASIC EXECUTION
# ============================================================================

# 1. Quick test (2 min, 3 iterations)
python3 example.py

# 2. Full run
python3 main.py

# 3. Validate project integrity
python3 validate.py

# 4. Reset project to initial tagged state
bash reset.sh

# 5. Reset project to a specific git ref
bash reset.sh v1.0-base-gemini-logging

# ============================================================================
# MONITORING & INSPECTION
# ============================================================================

# 1. Watch iteration log in real-time
tail -f iteration_log.md

# 2. View iteration log (entire history)
cat iteration_log.md

# 3. Current system prompt
cat system_prompt.md

# 4. Current tasks
cat todo.md

# 5. Available tools
cat tools.md

# ============================================================================
# DOCUMENTATION NAVIGATION
# ============================================================================

# 1. Start here (main guide)
less README.md

# 2. Project overview
less SYNTHESE.md

# 3. Technical architecture
less ARCHITECTURE.md

# 4. Detailed action plan
less ITERATION_1_PLAN.md

# 5. Advanced strategies
less PROPOSITIONS.md

# 6. Navigation & search
less INDEX.md

# 7. Project structure
less TREE.txt

# ============================================================================
# DEVELOPMENT
# ============================================================================

# 1. Check Python syntax
python3 -m py_compile main.py tools/task_executor.py tools/api_caller.py

# 2. List project files
ls -lah

# 3. Count lines of code
find . -name "*.py" -exec wc -l {} +

# 4. Count lines of documentation
find . -name "*.md" -exec wc -l {} +

# 5. Check configuration
cat config.yaml

# ============================================================================
# GIT COMMANDS (optional)
# ============================================================================

# 1. Initialize repo (if not done)
git init
git add .
git commit -m "Initial RepaI project setup"

# 2. View changes
git status

# 3. Commit current state
git add .
git commit -m "Iteration N complete"

# 4. View history
git log --oneline

# 5. Return to initial project state
bash reset.sh

# ============================================================================
# USEFUL FUNCTIONS (Add to .bashrc)
# ============================================================================

# # Start RepaI
# function repai-start() {
#   cd /home/mrpink/perso/repai
#   python3 main.py
# }

# # Monitor logs
# function repai-watch() {
#   cd /home/mrpink/perso/repai
#   tail -f iteration_log.md
# }

# # Quick test
# function repai-test() {
#   cd /home/mrpink/perso/repai
#   python3 example.py
# }

# # View docs
# function repai-docs() {
#   cd /home/mrpink/perso/repai
#   less README.md
# }

# Usage: repai-start, repai-watch, repai-test, repai-docs

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

# Set Google Gemini API key (optional, for LLM-enabled iterations)
export GOOGLE_API_KEY="your-google-api-key-here"

# Or add to .env file
echo "GOOGLE_API_KEY=your-google-api-key-here" > .env

# Source .env if exists
if [ -f .env ]; then source .env; fi

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# 1. No module named 'yaml'
pip install pyyaml

# 2. No module named 'requests'
pip install requests

# 3. Python version check
python3 --version  # Should be 3.8+

# 4. Check all dependencies
pip list | grep -E "pyyaml|requests"

# 5. Reinstall requirements
pip install -r requirements.txt --force-reinstall

# ============================================================================
# USEFUL INFO
# ============================================================================

# Project location
# /home/mrpink/perso/repai

# Main entry point
# main.py (EvolutionaryAgent class)

# Configuration file
# config.yaml

# Output log
# iteration_log.md

# Documentation
# README.md (start here)
# SYNTHESE.md (overview)
# ARCHITECTURE.md (technical)

# Tools
# tools/task_executor.py
# tools/api_caller.py

# Support
# INDEX.md - navigation guide
# ITERATION_1_PLAN.md - action plan
# PROPOSITIONS.md - ideas

# ============================================================================
# QUICK FAQs
# ============================================================================

# Q: How to run the agent?
# A: python3 example.py (quick test) or python3 main.py (full run)

# Q: How to monitor execution?
# A: tail -f iteration_log.md

# Q: Where is the documentation?
# A: Start with README.md, then SYNTHESE.md

# Q: How to modify configuration?
# A: Edit config.yaml (YAML format)

# Q: How to add new tasks?
# A: Edit todo.md (markdown list format)

# Q: Can it really improve itself?
# A: Yes, if GOOGLE_API_KEY is configured and the Gemini call succeeds.

# Q: How to add new tools?
# A: Create tools/my_tool.py, document in tools.md

# Q: What's the plan?
# A: Read ITERATION_1_PLAN.md for detailed action plan

# ============================================================================
# SUCCESS CHECKLIST
# ============================================================================

# After installation:
[ ] bash install.sh completed
[ ] python3 example.py runs without errors
[ ] iteration_log.md contains iteration data
[ ] All documentation readable

# After reading docs:
[ ] README.md read (understand concept)
[ ] ITERATION_1_PLAN.md read (know action plan)
[ ] ARCHITECTURE.md read (understand design)

# Ready for iteration 1:
[ ] Application structure validated
[ ] Tools working correctly
[ ] Logs capturing results
[ ] Documentation complete

# ============================================================================

echo "RepaI Quick Commands Ready!"
echo "Start with: cd /home/mrpink/perso/repai && python3 example.py"
