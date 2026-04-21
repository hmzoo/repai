# 🔐 Environment Variables - RepaI Configuration

## 📋 Fichiers de Configuration

### `.env` (Secret - Ne pas commiter)
```
.env
├─ Contient les VRAIES clés API
├─ Variables sensibles
├─ Exclu du git (.gitignore)
└─ À créer localement par chaque développeur
```

**Actions:**
1. Créer une copie : `cp .env.example .env`
2. Remplir avec vos clés API réelles
3. Ne JAMAIS commiter ce fichier!

### `.env.example` (Template - À commiter)
```
.env.example
├─ Template des variables disponibles
├─ Contenu NON sensible
├─ Inclus dans git
└─ Utilisé pour documentation
```

**Usage:**
- Reference pour les développeurs
- Documentation des variables disponibles
- Base pour créer `.env` localement

---

## 🔧 Configuration Minimale

### Pour Iteration 1 (sans OpenAI)
```bash
# Aucune variable requise
# Le projet fonctionne sans .env
```

### Pour Iteration 2+ (avec OpenAI)
```bash
# Créer .env et ajouter:
OPENAI_API_KEY=sk-your-api-key-here
```

---

## 🚀 Comment Utiliser

### Option 1: Charger .env Automatiquement
```python
# Dans main.py (déjà implémenté):
from dotenv import load_dotenv
load_dotenv()  # Charge .env automatiquement
```

### Option 2: Charger Manuellement
```bash
# Dans votre terminal:
source .env

# Puis lancer:
python3 main.py
```

### Option 3: Shell Export
```bash
export OPENAI_API_KEY="sk-..."
python3 main.py
```

---

## 📝 Variables Disponibles

### ✅ Requises (pour Iteration 2+)
| Variable | Type | Description |
|----------|------|------------|
| `OPENAI_API_KEY` | string | Clé API OpenAI (format: `sk-...`) |

### 🟡 Optionnelles (futures)
| Variable | Type | Description |
|----------|------|------------|
| `ANTHROPIC_API_KEY` | string | Clé API Anthropic Claude |
| `GOOGLE_API_KEY` | string | Clé API Google Gemini |
| `LOG_LEVEL` | string | DEBUG \| INFO \| WARNING \| ERROR |
| `DEBUG_MODE` | string | true \| false |
| `SLACK_WEBHOOK_URL` | string | Webhook Slack pour notifications |
| `GITHUB_TOKEN` | string | Token GitHub pour version control |

---

## 🛠️ Setup Initial

### Étape 1: Copier le Template
```bash
cd /home/mrpink/perso/repai
cp .env.example .env
```

### Étape 2: Éditer pour Votre Environnement
```bash
# Ouvrir dans votre éditeur:
nano .env
# ou
code .env

# Remplir vos valeurs (au minimum):
# OPENAI_API_KEY=sk-...
```

### Étape 3: Vérifier la Configuration
```bash
# Tester que les variables sont accessibles:
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Config OK' if os.getenv('OPENAI_API_KEY') else '⚠️  No API Key')"
```

---

## ✅ Checklist - Git Configuration

- [x] `.env` dans `.gitignore` ✅ (ligne 138)
- [x] `.env.example` créé ✅ (safe à commiter)
- [x] `.env` local créé ✅ (pour secrets)
- [x] `python-dotenv` dans requirements.txt ✅
- [ ] `python3 -c "import dotenv; print('✓')"` (après install)

---

## 🔒 Bonnes Pratiques

### ✅ Faire
```bash
# ✓ Charger depuis .env
echo "OPENAI_API_KEY=sk-..." > .env

# ✓ Dans .gitignore
.env

# ✓ Commiter le template
.env.example

# ✓ Documenter les variables
# Voir .env.example
```

### ❌ Ne Pas Faire
```bash
# ✗ Commiter .env avec clés
git add .env  # DANGER!

# ✗ Hardcoder les clés dans le code
api_key = "sk-..."  # DANGER!

# ✗ Mettre clés dans config.yaml public
api_key: sk-...  # DANGER!

# ✗ Passer en ligne de commande visible
python3 main.py --api-key sk-...  # DANGER!
```

---

## 🔍 Vérifications de Sécurité

### Vérifier que .env n'est pas commité
```bash
git status
# Ne doit PAS montrer .env
```

### Lister les fichiers qui seront committés
```bash
git diff --cached
# Ne doit PAS montrer de clés API
```

### Vérifier .gitignore
```bash
cat .gitignore | grep "\.env"
# Doit afficher: .env
```

---

## 📊 Priorité de Chargement

```
Priority 1: Variables d'env shell (déjà exportées)
            $ export OPENAI_API_KEY=sk-...
            $ python3 main.py

Priority 2: Fichier .env local
            python-dotenv charge automatiquement .env

Priority 3: Valeurs dans config.yaml
            Pour fallback/defaults

Priority 4: Hardcoded dans le code
            Dernière option (mauvais!)
```

**Python accède via:**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Charge .env
api_key = os.getenv("OPENAI_API_KEY")  # Récupère valeur
```

---

## 🚨 Dépannage

### "ModuleNotFoundError: No module named 'dotenv'"
```bash
pip install python-dotenv
```

### "OPENAI_API_KEY is None/empty"
```bash
# Vérifier que .env existe
ls -la .env

# Vérifier le contenu
cat .env | grep OPENAI

# Recharger shell
source .env
echo $OPENAI_API_KEY
```

### ".env n'est pas chargé"
```bash
# Option 1: Charger manuellement
source .env

# Option 2: Verifier que les noms matchent (case-sensitive)
# OPENAI_API_KEY vs openai_api_key (différent!)

# Option 3: Fermer/rouvrir terminal
exit
# puis nouveau terminal
```

---

## 📚 Ressources

### Créer des Clés API
- **OpenAI:** https://platform.openai.com/api-keys
- **Anthropic:** https://console.anthropic.com/
- **Google:** https://console.cloud.google.com/
- **GitHub:** https://github.com/settings/tokens

### Documentation
- **python-dotenv:** https://github.com/theskumar/python-dotenv
- **Environment Variables:** https://en.wikipedia.org/wiki/Environment_variable

---

## 🎯 Résumé

| Fichier | Scope | Git | Contenu | Usage |
|---------|-------|-----|---------|-------|
| `.env` | Secret | ❌ Ignore | Clés réelles | Runtime |
| `.env.example` | Public | ✅ Include | Template | Référence |
| `config.yaml` | Public | ✅ Include | Config général | Defaults |

**Flux Recommandé:**
```
1. cp .env.example → .env (local)
2. Remplir .env avec vos secrets
3. source .env (charger variables)
4. python3 main.py (exécuter)
5. git commit (sans .env!) ✅
```

---

**Created:** April 21, 2026  
**Updated for:** Environment Management Best Practices
