# 🤖 RepaI - Recursive Evolutionary Programming Agent

Une **application Python auto-générative** qui s'améliore continuellement en boucle récursive.

## 🎯 Concept Core

RepaI est un agent LLM autonome qui:
- 📋 **Exécute des tâches** récursivement depuis `todo.md`
- 🧠 **S'améliore** en rééécrivant son propre system prompt
- 🛠️ **Crée ses outils** dynamiquement en Python
- 🔗 **Intègre des APIs** externes au besoin
- 📊 **Trace son évolution** complet dans `iteration_log.md`

### La Boucle Récursive

```
[Itération N]
  ├─ Charger system_prompt.md (constitution de l'agent)
  ├─ Charger todo.md (tâches à accomplir)
  ├─ Exécuter tâches via outils disponibles
  ├─ Analyser résultats et erreurs
  ├─ Générer améliorations
  ├─ Réécrire system_prompt.md (v+1)
  ├─ Réécrire todo.md (v+1)
  └─ → Itération N+1
```

---

## 📁 Structure du Projet

```
repai/
├── main.py                    # Point d'entrée - Orchestrateur principal
├── system_prompt.md           # Instructions LLM (mis à jour auto)
├── todo.md                    # Backlog de tâches (dynamique)
├── tools.md                   # Documentation des outils disponibles
├── config.yaml                # Configuration (API keys, paramètres)
├── iteration_log.md           # Historique détaillé de chaque itération
├── example.py                 # Exemple d'utilisation
├── PROPOSITIONS.md            # Stratégies d'amélioration suggérées
├── requirements.txt           # Dépendances Python
├── tools/                     # Outils Python exécutables
│   ├── __init__.py
│   ├── task_executor.py       # Exécute commands/Python code
│   └── api_caller.py          # Appelle les APIs externes
└── README.md                  # Ce fichier
```

---

## 🚀 Démarrage Rapide

### 1. Clone et Setup
```bash
cd /home/mrpink/perso/repai
pip install -r requirements.txt
```

### 2. Configuration
Éditer `config.yaml`:
```yaml
llm:
  api_key: "${OPENAI_API_KEY}"  # ou export OPENAI_API_KEY=sk-...
  model: "gpt-4"                # ou "gpt-3.5-turbo"
  temperature: 0.7
```

### 3. Lancer l'Agent
```bash
python main.py
```

L'agent s'exécutera récursivement jusqu'à `max_iterations` (configurable).

### 3bis. Revenir à l'état initial
```bash
bash reset.sh
```

Par défaut, le script restaure le dépôt sur le tag `v1.0-base-evolution`, supprime les fichiers non suivis et conserve les fichiers ignorés comme `.env`.

### 4. Suivre l'Évolution
- **Résultats détaillés** → `iteration_log.md`
- **Prompt actuel** → `system_prompt.md`
- **Tâches** → `todo.md` (mis à jour après chaque itération)

---

## 📊 Architecture Logique

### Classe `EvolutionaryAgent` (main.py)

| Méthode | Rôle |
|---------|------|
| `load_system_prompt()` | Lit la constitution de l'agent |
| `load_todos()` | Parse les tâches depuis `todo.md` |
| `execute_iteration()` | Exécute une itération complète |
| `_log_iteration()` | Enregistre résultats dans `iteration_log.md` |
| `run()` | Boucle récursive principale |

### Outils Disponibles (tools/)

1. **task_executor.py**
   - `execute_shell_command()` - Commandes bash
   - `execute_python_code()` - Code Python
   - `execute_task()` - Interface unifiée

2. **api_caller.py**
   - `APIClient` - Client HTTP générique
   - `OpenAIClient` - Client OpenAI spécialisé

---

## 🔄 Cycle de Vie Détaillé

### Itération 1 (Bootstrap)
- [ ] Implémenter architecture stable
- [ ] Créer 2-3 outils de base
- [ ] Tester la boucle de récursion
- [ ] Mettre en place le logging

### Itération 2+ (Amélioration)
- [ ] Analyser résultats de l'itération précédente
- [ ] Identifier ce qui s'est bien passé / mal passé
- [ ] Générer version améliorée du prompt
- [ ] Créer de nouvelles tâches basées sur feedback
- [ ] Ajouter/modifier des outils si nécessaire

---

## ⚙️ Configuration & Paramètres

### `config.yaml` - Clés Principales

```yaml
# Modèle LLM
llm:
  provider: "openai"              # openai | anthropic | local
  model: "gpt-4"                  # Modèle à utiliser
  temperature: 0.7                # Créativité (0.0-1.0)
  max_tokens: 2000                # Long max de réponse
  api_key: "${OPENAI_API_KEY}"   # Variable d'env

# Limites de récursion
execution:
  max_iterations: 10              # Nombre max d'itérations
  timeout_per_iteration: 300      # Timeout (secondes)
  debug_mode: true                # Logs verbeux

# Agent
agent:
  name: "RepaI"
  auto_tool_creation: true        # Génère outils auto
  recursive_calls: true           # Permet récursion
```

---

## 🛠️ Exemple : Créer un Nouvel Outil

1. **Créer le fichier** `tools/my_tool.py`:
```python
def my_function(param: str) -> Dict[str, Any]:
    """Doc de la fonction"""
    return {"success": True, "result": param}
```

2. **Documenter dans** `tools.md`:
```markdown
### my_tool
**Signature** : my_function(param: str) -> Dict
**Usage** : [exemple d'utilisation]
```

3. **Utiliser dans les TODO**:
```markdown
- [ ] Appeler my_tool pour faire X
```

---

## 📈 Monitoring & Métriques

Chaque itération enregistre:
- ✅ Tâches complétées / totales
- ⏱️ Temps d'exécution
- 📞 Nombre d'appels API
- 📝 Nouvelles lignes de code
- 🔄 Changements du prompt (%)
- 💪 Score de santé (0-100)

Consultable dans `iteration_log.md`.

---

## 🔐 Sécurité & Limites

### Protections Intégrées
- ⏱️ **Timeout** par itération
- 🔄 **Limite de profondeur** de récursion
- 🛡️ **Circuit breaker** en cas d'erreurs répétées
- 📋 **Version control** des prompts (rollback possible)
- 🔒 **Isolation** des outils (pas d'accès système complet)

---

## 💡 Patterns de Conception

### Pattern 1 : Auto-Amélioration Incrémentale
```
Itération 1 : Architecture de base + tests
Itération 2 : Optimisations + nouvelles features
Itération 3 : Refactoring + amélioration du prompt
```

### Pattern 2 : Multi-Agent (Futur)
```
Agent Principal (Orchestration)
├── Agent Code (Programmation)
├── Agent Tests (QA)
├── Agent Docs (Documentation)
└── Agent Ops (DevOps)
```

---

## 📚 Documentation Supplémentaire

- **[PROPOSITIONS.md](PROPOSITIONS.md)** - Stratégies avancées & recommandations
- **[system_prompt.md](system_prompt.md)** - Constitution courante de l'agent
- **[todo.md](todo.md)** - Tâches à accomplir
- **[tools.md](tools.md)** - Référence des outils
- **[iteration_log.md](iteration_log.md)** - Historique complet
- **[example.py](example.py)** - Exemple d'exécution

---

## 🔗 Intégrations API

### Actuellees (Tierées)
- ✅ **OpenAI GPT** - LLM principal (recommandé)

### À Venir (Phase 2)
- ⏳ **Anthropic Claude** - Alternative LLM
- ⏳ **GitHub** - Version control
- ⏳ **Slack** - Notifications
- ⏳ **Datadog** - Monitoring

---

## 🧪 Testing

```bash
# Lancer les tests (à implémenter)
pytest tests/

# Lint le code
pylint tools/ main.py

# Format le code
black .
```

---

## 🎓 Principes Fondamentaux

1. **Simplicité** 📖 - Code lisible et maintenable
2. **Modularité** 🧩 - Outils découplés
3. **Traçabilité** 📝 - Chaque changement documenté
4. **Robustesse** 💪 - Gestion d'erreurs et timeouts
5. **Évolution** 📈 - Amélioration automatique

---

## 🤝 Contribution

Pour améliorer RepaI:
1. Ajouter des outils dans `tools/`
2. Documenter dans `tools.md`
3. Tester via `example.py`
4. Suggérer dans `PROPOSITIONS.md`

---

## 📝 Notes

- **Première exécution** : Agent génère tâches initiales basées sur `system_prompt.md`
- **Itérations suivantes** : Agent améliore son propre prompt et backlog
- **Archive** : Versions anciennes de prompt sauvegardées automatiquement
- **Fallback** : Peut revenir à version antérieure si dégradation

---

## 📄 License

[À définir]

---

**Dernière mise à jour** : April 21, 2026  
**Version** : 1.0-Alpha