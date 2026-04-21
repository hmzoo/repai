# Architecture & Design Patterns

## Diagramme d'Exécution

```
┌─────────────────────────────────────────────────────────┐
│          RepaI - Evolutionary Agent Loop                │
└─────────────────────────────────────────────────────────┘

START
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ [1] INITIALIZATION                                      │
│ • Load config.yaml                                      │
│ • Initialize EvolutionaryAgent()                        │
│ • Set iteration counter = 1                             │
└─────────────────────────────────────────────────────────┘
  │
  └──────────────────┬──────────────────┐
                     │                  │
                     ▼                  │
            ┌─────────────────┐         │
            │ MAX_ITERATIONS? │         │
            │ YES: continue   │         │
            │ NO: END         │─────────┘
            └─────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ [2] LOAD AGENT STATE                                    │
│ • Read system_prompt.md (constitution)                  │
│ • Parse todo.md (tasks)                                 │
│ • Read tools.md (available tools)                       │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ [3] EXECUTE TASKS                                       │
│ • For each task in todo.md:                             │
│   - Parse task instructions                             │
│   - Select appropriate tool                             │
│   - Execute with timeout protection                     │
│   - Capture output/errors                               │
│   - Log results                                         │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ [4] LLM ANALYSIS (if API configured)                    │
│ • Send to OpenAI/Claude:                                │
│   - Results from iteration                              │
│   - Current system_prompt.md                            │
│   - What could be improved?                             │
│ • Receive:                                              │
│   - Improved system_prompt                              │
│   - New tasks for next iteration                        │
│   - Analysis & feedback                                 │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ [5] EVOLUTION & UPDATE                                  │
│ • Write new system_prompt.md                            │
│ • Update todo.md with fresh tasks                       │
│ • Archive old versions (prompt_v1, v2, etc.)            │
│ • Log iteration in iteration_log.md                     │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ [6] RECURSE                                             │
│ • iteration_counter += 1                                │
│ • Go back to [1] LOAD AGENT STATE                       │
└─────────────────────────────────────────────────────────┘
  │
  └──────────────────► (loop back to MAX_ITERATIONS check)
```

---

## Modèle de Données

### system_prompt.md Structure
```markdown
# System Prompt - RepaI Agent

## Rôle et Identité
[Description of agent personality/purpose]

## Directives Principales
[Main instructions and constraints]

## Feedback Loop
[How agent improves itself]

## Constraints
[Safety limits and boundaries]

**Itération courante** : N
**Dernière mise à jour** : [timestamp]
```

### todo.md Structure
```markdown
# TODO - RepaI Task Backlog

## Itération N - [Theme]

### Niveau Critical
- [ ] Task with clear success criteria
- [ ] Task with dependencies

### Niveau Important
- [ ] Secondary tasks

### Niveau Bonus
- [ ] Nice-to-have improvements

---
**Itération courante** : N
```

### iteration_log.md Structure
```markdown
# Iteration Log

### Itération N
**Timestamp** : 2026-04-21T10:30:00  
**Status** : completed | failed | timeout  
**Tâches traitées** : X / Y  
**Temps d'exécution** : 45.2s  

**Résultats clés**:
- ✅ [Success]
- ⚠️  [Warning]
- ❌ [Failure]

**Améliorations pour itération N+1**:
- [Generated improvements from LLM]

---
```

---

## Stack Technique

### Core
- **Python 3.8+**
- **PyYAML** - Configuration
- **Requests** - HTTP calls

### LLM Integration
- **OpenAI API** - Recommandé
- **Anthropic API** - Alternative

### Tools Framework
- **subprocess** - Command execution
- **tempfile** - Temporary files
- **json/yaml** - Data serialization

### Optional
- **LangChain** - LLM abstractions
- **Redis** - Caching (future)
- **Datadog** - Monitoring (future)

---

## Safety Boundaries

### Execution Limits
```python
MAX_ITERATIONS = 10          # Prevent runaway
TIMEOUT_PER_ITERATION = 300  # 5 minutes per cycle
MAX_TOOL_EXECUTION = 60      # 1 minute per tool
```

### Tool Restrictions
```
✅ ALLOWED:
   • Read own files (markdown, python)
   • Write own files (.md, .py in specific dirs)
   • Execute Python code (user-sandbox)
   • Call APIs

❌ BLOCKED:
   • System commands (rm, dd, etc.)
   • Network access (unless API configured)
   • Writing outside project directory
   • Deleting project files
```

### Circuit Breaker
```
IF consecutive_failures > 3:
    • Log all context
    • Revert to last known-good state
    • Alert human
    • Pause recursion
```

---

## Data Flow Diagram

```
┌────────────────────────────────────────────────────────┐
│               EXTERNAL APIs                             │
│     (OpenAI GPT-4, Anthropic Claude, etc.)             │
└────────────────────────────────────────────────────────┘
         ▲                                    │
         │                                    │
         │ [System Prompt + Results]          │ [Improvements]
         │                                    │
         └────────────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │   EVOLUTIONARY AGENT         │
         │  (EvolutionaryAgent class)   │
         └──────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    ┌────────┐   ┌───────────┐   ┌──────────┐
    │ TOOLS  │   │  CONFIG   │   │ LOG      │
    │        │   │           │   │ FILES    │
    └────────┘   └───────────┘   └──────────┘
         │              │              │
    • execute       • yaml load    • md write
    • api_call      • refresh      • archive
    • file_ops      • validate
```

---

## Evolution Strategies

### Strategy 1: Guided Self-Improvement
```
Agent Reads Own Results
       ↓
Identifies Pain Points
       ↓
Asks LLM for Improvements
       ↓
Updates Its Own Code/Docs
       ↓
Better Next Iteration
```

### Strategy 2: Progressive Specialization
```
Iteration 1-3: Generalist (learn basics)
Iteration 4-6: Pick a specialization
Iteration 7+:  Deep expertise in domain
```

### Strategy 3: Collaborative Evolution
```
Multiple Agents
       ↓
Each Improves Independently
       ↓
Exchange Results via Files
       ↓
Consensus on Major Changes
```

---

## Performance Optimization

### Future Improvements
1. **Caching Layer**
   - Cache API responses
   - Cache tool execution results
   - Invalidate on changes

2. **Async Execution**
   - Run independent tools in parallel
   - LLM calls while tasks execute

3. **Intelligent Scheduling**
   - Prioritize critical tasks
   - Skip completed work
   - Batch similar operations

---

## State Machine

```
    ┌──────────────┐
    │   INIT       │
    │   state=new  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   RUNNING    │──────────┐
    │   state=busy │          │
    └──────┬───────┘          │
           │                   │ TIMEOUT
           ├──► SUCCESS ─┐    │
           │              │   │
           └──► FAILED    │   │
                           │   │
                           ▼   ▼
                      ┌──────────────┐
                      │  COMPLETE    │
                      │  state=done  │
                      └──────────────┘
                           │
                           ▼
                      ┌──────────────┐
                      │  ANALYZE &   │
                      │  RECURSE     │
                      └──────────────┘
```

---

## Configuration Validation

```yaml
config_schema:
  llm:
    provider: str  # openai | anthropic | local
    model: str
    temperature: float  # 0.0 - 1.0
    max_tokens: int
    api_key: str

  execution:
    max_iterations: int  # 1 - 100
    timeout_per_iteration: int  # 30 - 3600s
    debug_mode: bool

  agent:
    name: str
    auto_tool_creation: bool
    recursive_calls: bool
```

---

*Generated: April 21, 2026*
