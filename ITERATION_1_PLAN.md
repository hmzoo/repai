# Itération 1 - Plan Détaillé

## Vue d'ensemble

La première itération établit les **fondations stabiles** du projet. L'objectif est de créer une boucle de récursion fonctionnelle simple, sans complexité inutile.

---

## État Attendu après Itération 1

### ✅ Ce que l'agent aura accomplir:

```
Fondations
├─ Architecture stable et lisible ✓
├─ Boucle de récursion limitée ✓
├─ Logging détaillé ✓
├─ Gestion d'erreurs ✓
└─ Documentation complète ✓

Outils de Base
├─ task_executor (shell + Python) ✓
├─ file_manager (markdown) ✓
└─ api_caller (HTTP générique) ✓

Integration Minimale
├─ Config.yaml chargé ✓
├─ Pas d'API externe requise (fallback) ✓
└─ Prêt pour OpenAI dans itération 2 ✓
```

---

## Tâches Détaillées - Itération 1

### 🔴 CRITICAL - À accomplir absolument

#### Task 1.1: Valider l'architecture main.py
**Critères de succès:**
- [ ] `EvolutionaryAgent` classe instantiable
- [ ] `execute_iteration()` complète sans erreur
- [ ] Boucle teste avec `max_iterations = 3`
- [ ] Pas de timeout (< 5s par itération)

**Exécution:**
```python
# Dans example.py:
agent = EvolutionaryAgent(config)
assert agent.iteration == 1
agent.run()  # Should complete 3 iterations
assert agent.iteration == 4
```

#### Task 1.2: Tester les outils de base
**Critères de succès:**
- [ ] `task_executor.execute_task("test_shell", "shell", "echo test")` retourne succès
- [ ] `task_executor.execute_python_code("print('test')")` fonctionne
- [ ] Timeouts fonctionnent (test avec sleep 1000)
- [ ] Erreurs capturées correctement

**Exécution:**
```bash
python -m tools.task_executor  # Si un test basic existe
```

#### Task 1.3: Setup logging complet
**Critères de succès:**
- [ ] `iteration_log.md` se remplit à chaque itération
- [ ] Format markdown cohérent
- [ ] Timestamps UTC
- [ ] Archive automatique (optionnel pour v1)

**Résultat:**
```markdown
### Itération 1
**Timestamp** : 2026-04-21T10:30:00  
**Status** : completed  
**Durée** : 1.23s  
**Tâches** : 3 / 3 complétées  

✅ Résultats OK
```

#### Task 1.4: Documenter le système prompt de base
**Critères de succès:**
- [ ] `system_prompt.md` clair et complet
- [ ] Instructions comprises par l'agent
- [ ] Pas d'ambiguïtés sur les limites
- [ ] Version = "1" au démarrage

**Contenu:**
```markdown
# System Prompt - RepaI 

Tu es un assistant Python qui:
1. Lis todo.md
2. Exécute tâches avec les outils disponibles
3. Logs les résultats
4. Génère la prochaine version de toi-même

Limites:
- Max 10 itérations
- Timeout 5 min par itération
- Pas d'appels API avant itération 2
```

### 🟡 IMPORTANT - À faire de préférence

#### Task 1.5: Setup configuration validation
**Critères de succès:**
- [ ] `config.yaml` charge sans erreurs
- [ ] Valeurs par défaut sensées
- [ ] Env vars optionnelles supportées
- [ ] Config merge (global + env)

**Test:**
```python
config = Config()
assert config.get("llm")["temperature"] == 0.7
```

#### Task 1.6: Créer tests unitaires basiques
**Critères de succès:**
- [ ] `pytest tests/test_agent.py` passe
- [ ] Au minimum 5 tests
- [ ] Coverage > 50%

**Tests suggérés:**
```python
def test_agent_initialization()
def test_load_system_prompt()
def test_load_todos_parsing()
def test_task_executor_success()
def test_task_executor_timeout()
```

#### Task 1.7: Documentation README complète (v1)
**Critères de succès:**
- [ ] Setup instructions claires
- [ ] Exemple rapide fonctionnel
- [ ] Lien vers autres docs
- [ ] Pas d'erreurs grammaticales

### 🟢 BONUS - Si temps disponible

#### Task 1.8: Performance metrics collection
- [ ] Ajouter timing granulaire par tâche
- [ ] Tracker utilisation mémoire
- [ ] Exporter stats JSON

#### Task 1.9: CLI arguments pour main.py
```bash
python main.py --iterations 5 --debug
python main.py --config custom.yaml
python main.py --no-recursion  # Mode test
```

#### Task 1.10: Webhook/notification stub
- [ ] Placeholder pour futures notifications
- [ ] Structure prête pour Slack/Discord

---

## Fichiers Créés/Modifiés

### ✅ Créés en Itération 1
```
main.py                 # 250 lignes, classe EvolutionaryAgent
tools/__init__.py       # Module tools
tools/task_executor.py  # 150 lignes
tools/api_caller.py     # 200 lignes
config.yaml             # Configuration de base
example.py              # Script de démo
requirements.txt        # Dépendances
system_prompt.md        # Constitution v1
todo.md                 # Tâches v1
tools.md                # Doc des outils v1
iteration_log.md        # Logs vides (sera rempli au runtime)
README.md               # Documentation complète
ARCHITECTURE.md         # Design patterns
PROPOSITIONS.md         # Suggestions futures
```

### 🔄 À Modifier selon Résultats
- `system_prompt.md` → Version 2 si améliorations identifiées
- `todo.md` → Tâches v2 pour itération 2
- `tools.md` → Ajouter outils créés dynamiquement

---

## Script de Validation - Itération 1

```bash
#!/bin/bash
# validate_iter1.sh

echo "🔍 Validating Iteration 1..."

# 1. Check files exist
echo "📁 Checking files..."
files=(main.py system_prompt.md todo.md tools.md config.yaml)
for f in "${files[@]}"; do
    [ -f "$f" ] && echo "  ✓ $f" || echo "  ✗ $f MISSING"
done

# 2. Check Python syntax
echo "🐍 Checking Python syntax..."
python -m py_compile main.py && echo "  ✓ main.py" || echo "  ✗ main.py SYNTAX ERROR"

# 3. Test imports
echo "📦 Testing imports..."
python -c "from main import Config, EvolutionaryAgent; print('  ✓ Imports OK')" 2>&1

# 4. Quick run (max 1 iteration, no API)
echo "⚙️  Testing minimal run..."
python -c "
from main import Config, EvolutionaryAgent
config = Config()
config.data['execution']['max_iterations'] = 1
agent = EvolutionaryAgent(config)
agent.run()
print('  ✓ Run completed')
" 2>&1

# 5. Check iteration_log
echo "📋 Checking iteration log..."
[ -f "iteration_log.md" ] && grep -q "Itération 1" iteration_log.md && echo "  ✓ Log recorded" || echo "  ✗ Log not found"

echo "✨ Validation complete!"
```

---

## Timeline Estimé - Itération 1

| Tâche | Estimé | Dépendances |
|-------|--------|-------------|
| 1.1 Valider architecture | 30 min | (foundational) |
| 1.2 Tester outils | 20 min | 1.1 ✓ |
| 1.3 Setup logging | 15 min | 1.1 ✓ |
| 1.4 Documenter prompt | 10 min | parallel |
| 1.5 Config validation | 15 min | parallel |
| 1.6 Tests unitaires | 30 min | 1.1-1.3 ✓ |
| 1.7 README (v1) | 20 min | parallel |
| **TOTAL (Critical/Important)** | **~2h30** | |
| 1.8-1.10 Bonus | 30-45 min | if time |

**Objectif:** Itération 1 complétée en **3 heures maximum** (incluant testing)

---

## Sortie Attendue en Console

```
╔═════════════════════════════════════════╗
║          RepaI - Example Run             ║
║   Self-Improving Python Agent           ║
╚═════════════════════════════════════════╝

📖 Loading configuration...
   Provider: openai
   Model: gpt-4
   Max iterations: 3

🤖 Initializing agent...

▶️  Starting recursive execution loop...

============================================================
ITERATION 1
============================================================

📋 Loaded 3 tasks
   1. Implémenter la classe EvolutionaryAgent...
   2. Créer l'outil task_executor pour exécuter...
   3. Mettre en place la boucle de récursion...

✅ Iteration 1 logged

============================================================
ITERATION 2
============================================================

📋 Loaded 4 tasks
   ...

✅ Iteration 2 logged

============================================================
ITERATION 3
============================================================

📋 Loaded 5 tasks
   ...

✅ Iteration 3 logged

✨ Agent completed 3 iterations
   Total time: 5.34s
```

---

## Critères de Succès Globaux - Itération 1

✅ **PASS si:**
- Boucle de récursion stable (0 crashes)
- 3 itérations complétées en < 10 secondes
- iteration_log.md rempli correctement
- Tous les fichiers .py syntaxiquement corrects
- README et docs complets
- Tests > 80% passing

❌ **FAIL si:**
- Crashes ou erreurs non capturées
- Timeout ou blocage infini
- Corruption de fichiers markdown
- Imports manquants / dépendances
- Documentation incohérente

---

## Notes pour Itération 2

À commencer après Itération 1:
- [ ] Intégration OpenAI API
- [ ] Auto-amélioration du prompt
- [ ] Création dynamique d'outils
- [ ] Système de scoring/feedback
- [ ] Cache des résultats API
- [ ] Multi-agent framework (optionnel)

---

*Plan généré: April 21, 2026*  
*Prêt pour exécution manuelle ou automatisée*
