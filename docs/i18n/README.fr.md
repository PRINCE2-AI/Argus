# Argus

**Un petit harnais d'agent Python, inspectable, pour un travail réel dans un seul répertoire.**

[English](../../README.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · **Français**

Argus relie un modèle de langage à un ensemble restreint d'outils de l'espace de
travail, maintient chaque action dans une limite de chemins, enregistre des
sessions durables et transforme les décisions de sécurité en code lisible. Il
prend en charge six fournisseurs de modèles, quatre langues d'interface et
n'a aucune dépendance d'exécution.

## Pourquoi Argus

- **Surface réduite.** Chaque frontière — fournisseur, boucle, outils, politique,
  sessions, compactage — tient dans un module lisible.
- **Sécurité explicite.** Liste de commandes refusées, confinement des chemins,
  approbation interactive, masquage des secrets et revue sémantique optionnelle
  qui échoue en mode fermé.
- **Sessions robustes.** Les lignes JSONL incomplètes, les appels d'outils
  interrompus et les redémarrages sont réparés au chargement.
- **Indépendant du fournisseur.** Gemini, Anthropic, OpenAI, OpenRouter, Groq et
  Ollama local partagent un format de messages neutre.
- **Zéro dépendance d'exécution.** Uniquement la bibliothèque standard de
  Python 3.10+.

## Démarrage rapide

Prérequis : Python 3.10 ou supérieur et une clé API, ou un modèle Ollama local.

```bash
git clone https://github.com/PRINCE2-AI/Argus.git
cd Argus
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env             # Windows : copy .env.example .env
```

Ajoutez une clé dans `.env` :

```dotenv
GEMINI_API_KEY=votre-cle
```

Lancez une tâche :

```bash
argus                                                  # interactif
argus --prompt "Crée hello.py, exécute-le et rapporte la sortie" --yes
argus --prompt "Résume ce dépôt" --mode read-only
argus --resume                                         # session la plus récente
argus --list-sessions
argus --lang fr
```

## Fournisseurs

| Fournisseur | `--provider` | Clé API |
| --- | --- | --- |
| Google Gemini | `gemini` | `GEMINI_API_KEY` ou `ARGUS_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` ou `ARGUS_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` ou `ARGUS_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` ou `ARGUS_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` ou `ARGUS_API_KEY` |
| Ollama local | `ollama` | aucune |

Utilisez `--model` ou `ARGUS_MODEL` pour changer de modèle. Ollama ignore
volontairement `ARGUS_API_KEY` afin de ne jamais envoyer une clé cloud à
localhost.

## API Python

```python
from argus import Harness, Policy

harness = Harness(
    workdir=".",
    provider="gemini",
    model="gemini-3.1-flash-lite",
    policy=Policy("safe"),
)
print(harness.run("Crée un fichier d'état et vérifie-le."))
```

Ajoutez vos propres outils avec `@tool`, puis passez-les via `extra_tools`.

## Modèle de sécurité

| Mode | Comportement |
| --- | --- |
| `read-only` | Uniquement les outils de lecture. |
| `safe` (par défaut) | Les outils de modification demandent une approbation interactive. |
| `yolo` | Exécution automatique, mais la liste de refus s'applique toujours. |

Les chemins sont résolus à l'intérieur de l'espace de travail ; `.env`, `.git` et
`.argus` sont protégés. Les commandes destructrices, l'escalade de privilèges,
les shells inverses et les opérations Git forcées sont bloqués. En mode sans
interface, `safe` refuse les modifications sauf avec `--yes`.

**Argus n'est pas un bac à sable système.** Pour du travail non fiable, utilisez
un conteneur ou une machine virtuelle.

## Documentation

- [Architecture](../ARCHITECTURE.md)
- [Notes de portfolio](../PORTFOLIO.md)
- [Contribuer](../../CONTRIBUTING.md)
- [Sécurité](../../SECURITY.md)
- [Journal des modifications](../../CHANGELOG.md)

## Licence

MIT. Voir [LICENSE](../../LICENSE).
