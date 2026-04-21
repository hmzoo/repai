# Tools Documentation

## Outils Disponibles

### 1. `task_executor`
**Localisation** : `tools/task_executor.py`

**Description** : Exécute une tâche simple (bash, Python script, etc.)

**Signature**
```python
def execute_task(task_name: str, command: str) -> dict
```

**Paramètres**
- `task_name` (str) : Identifiant unique de la tâche
- `command` (str) : Commande à exécuter

**Retour**
```python
{
    "success": bool,
    "output": str,
    "error": str | None,
    "execution_time": float
}
```

**Exemple d'usage**
```python
from tools.task_executor import execute_task
result = execute_task("test_import", "python -c 'import sys; print(sys.version)'")
```

---

### 2. `file_manager`
**Localisation** : `tools/file_manager.py`

**Description** : Lit/écrit/modifie fichiers markdown et Python

**Signature**
```python
def read_file(filepath: str) -> str
def write_file(filepath: str, content: str) -> bool
def append_file(filepath: str, content: str) -> bool
```

---

## API Integrations

### OpenAI (À implémenter)
- Endpoint : `https://api.openai.com/v1/chat/completions`
- Authentification : Clé API
- Utilisation : Appels au modèle LLM principal

---

## Créer un Nouvel Outil

1. Créer `tools/my_tool.py`
2. Documenter ici avec Signature + Exemple
3. Mentionner dans `todo.md` si nouvelle dépendance

---

**Nombre d'outils** : 0 (à implémenter)
