"""Tiny dependency-free internationalization for the Argus CLI."""

import os

LANGUAGES = {
    "en": "English",
    "es": "Español",
    "hi": "हिन्दी",
    "fr": "Français",
}

TRANSLATIONS = {
    "en": {
        "cli_description": "Argus agent harness",
        "help_prompt": "run one headless task",
        "help_workdir": "workspace directory",
        "help_model": "model name",
        "help_provider": "model provider (gemini, openai, openrouter, groq, ollama, anthropic)",
        "help_mode": "safety mode",
        "help_resume": "resume the newest session",
        "help_session": "resume a specific session file",
        "help_list_sessions": "list saved sessions and exit",
        "help_yes": "auto-approve tool calls in safe mode (headless automation)",
        "help_fleet": "run a JSON fleet file and exit",
        "help_workers": "fleet concurrency",
        "help_max_turns": "maximum model turns per task",
        "help_budget": "context token budget before compaction",
        "help_lang": "interface language",
        "help_version": "print the Argus version",
        "banner": "Argus {version} | {provider}/{model} | mode={mode} | workspace={workdir}",
        "prompt": "argus> ",
        "approval": "{name} {args}\nAllow? [y/N] ",
        "no_session": "No saved Argus session found.",
        "session_loaded": "Resumed session: {path}",
        "headless_warning": "No approver in headless mode; mutating tools are denied. Use --yes or --mode yolo.",
        "bye": "Bye.",
        "help_body": (
            "Commands: /help  /mode <safe|yolo|read-only>  /session  /tokens  "
            "/lang <en|es|hi|fr>  /exit"
        ),
        "tool_call": "[tool] {name} {args}",
        "blocked": "BLOCKED: {reason}",
        "error": "ERROR: {error}",
        "no_sessions": "No saved sessions.",
        "tokens": "tokens: {input} in / {output} out",
        "mode_set": "Safety mode: {mode}",
        "lang_set": "Language: {language}",
        "unknown_command": "Unknown command: {command}. Type /help.",
        "interrupted": "Session log is safe; use --resume to continue it.",
        "session_path": "Session: {path}",
        "fleet_start": "Fleet: {count} job(s), {workers} worker(s)",
        "fleet_line": "[{index}/{count}] {name}: {status} ({seconds:.1f}s)",
        "fleet_done": "Fleet finished.",
        "list_sessions_header": "Sessions for {workdir}",
        "status_ok": "ok",
        "status_failed": "failed",
        "turn_limit": "Turn limit reached.",
    },
    "es": {
        "cli_description": "Arnés de agente Argus",
        "help_prompt": "ejecutar una tarea sin interfaz interactiva",
        "help_workdir": "directorio de trabajo",
        "help_model": "nombre del modelo",
        "help_provider": "proveedor de modelo (gemini, openai, openrouter, groq, ollama, anthropic)",
        "help_mode": "modo de seguridad",
        "help_resume": "reanudar la sesión más reciente",
        "help_session": "reanudar un archivo de sesión específico",
        "help_list_sessions": "listar sesiones guardadas y salir",
        "help_yes": "aprobar automáticamente herramientas en modo seguro",
        "help_fleet": "ejecutar un archivo JSON de flota y salir",
        "help_workers": "concurrencia de la flota",
        "help_max_turns": "máximo de turnos del modelo por tarea",
        "help_budget": "presupuesto de tokens antes de compactar",
        "help_lang": "idioma de la interfaz",
        "help_version": "mostrar la versión de Argus",
        "banner": "Argus {version} | {provider}/{model} | modo={mode} | espacio={workdir}",
        "prompt": "argus> ",
        "approval": "{name} {args}\n¿Permitir? [s/N] ",
        "no_session": "No se encontró ninguna sesión guardada de Argus.",
        "session_loaded": "Sesión reanudada: {path}",
        "headless_warning": "Sin aprobador en modo headless; las herramientas mutantes están bloqueadas. Usa --yes o --mode yolo.",
        "bye": "Adiós.",
        "help_body": (
            "Comandos: /help  /mode <safe|yolo|read-only>  /session  /tokens  "
            "/lang <en|es|hi|fr>  /exit"
        ),
        "tool_call": "[herramienta] {name} {args}",
        "blocked": "BLOQUEADO: {reason}",
        "error": "ERROR: {error}",
        "no_sessions": "No hay sesiones guardadas.",
        "tokens": "tokens: {input} entrada / {output} salida",
        "mode_set": "Modo de seguridad: {mode}",
        "lang_set": "Idioma: {language}",
        "unknown_command": "Comando desconocido: {command}. Escribe /help.",
        "interrupted": "El registro de la sesión está a salvo; usa --resume para continuarla.",
        "session_path": "Sesión: {path}",
        "fleet_start": "Flota: {count} tarea(s), {workers} trabajador(es)",
        "fleet_line": "[{index}/{count}] {name}: {status} ({seconds:.1f}s)",
        "fleet_done": "Flota terminada.",
        "list_sessions_header": "Sesiones en {workdir}",
        "status_ok": "ok",
        "status_failed": "falló",
        "turn_limit": "Se alcanzó el límite de turnos.",
    },
    "hi": {
        "cli_description": "Argus एजेंट हार्नेस",
        "help_prompt": "एक हेडलेस कार्य चलाएँ",
        "help_workdir": "कार्यक्षेत्र निर्देशिका",
        "help_model": "मॉडल का नाम",
        "help_provider": "मॉडल प्रदाता (gemini, openai, openrouter, groq, ollama, anthropic)",
        "help_mode": "सुरक्षा मोड",
        "help_resume": "नवीनतम सत्र फिर से शुरू करें",
        "help_session": "एक विशिष्ट सत्र फ़ाइल फिर से शुरू करें",
        "help_list_sessions": "सहेजे गए सत्रों की सूची दिखाएँ और बाहर निकलें",
        "help_yes": "सुरक्षित मोड में टूल कॉल अपने आप स्वीकार करें",
        "help_fleet": "JSON फ़्लीट फ़ाइल चलाएँ और बाहर निकलें",
        "help_workers": "फ़्लीट समवर्तीता",
        "help_max_turns": "प्रति कार्य अधिकतम मॉडल टर्न",
        "help_budget": "संकुचन से पहले संदर्भ टोकन बजट",
        "help_lang": "इंटरफ़ेस भाषा",
        "help_version": "Argus संस्करण दिखाएँ",
        "banner": "Argus {version} | {provider}/{model} | मोड={mode} | कार्यक्षेत्र={workdir}",
        "prompt": "argus> ",
        "approval": "{name} {args}\nअनुमति दें? [y/N] ",
        "no_session": "कोई सहेजा गया Argus सत्र नहीं मिला।",
        "session_loaded": "सत्र फिर से शुरू: {path}",
        "headless_warning": "हेडलेस मोड में कोई अनुमोदक नहीं है; बदलाव करने वाले टूल अस्वीकृत हैं। --yes या --mode yolo का उपयोग करें।",
        "bye": "अलविदा।",
        "help_body": (
            "कमांड: /help  /mode <safe|yolo|read-only>  /session  /tokens  "
            "/lang <en|es|hi|fr>  /exit"
        ),
        "tool_call": "[टूल] {name} {args}",
        "blocked": "अवरुद्ध: {reason}",
        "error": "त्रुटि: {error}",
        "no_sessions": "कोई सहेजा गया सत्र नहीं है।",
        "tokens": "टोकन: {input} इनपुट / {output} आउटपुट",
        "mode_set": "सुरक्षा मोड: {mode}",
        "lang_set": "भाषा: {language}",
        "unknown_command": "अज्ञात कमांड: {command}। /help लिखें।",
        "interrupted": "सत्र लॉग सुरक्षित है; जारी रखने के लिए --resume का उपयोग करें।",
        "session_path": "सत्र: {path}",
        "fleet_start": "फ़्लीट: {count} कार्य, {workers} वर्कर",
        "fleet_line": "[{index}/{count}] {name}: {status} ({seconds:.1f}से)",
        "fleet_done": "फ़्लीट पूरा हुआ।",
        "list_sessions_header": "{workdir} के सत्र",
        "status_ok": "ठीक",
        "status_failed": "विफल",
        "turn_limit": "टर्न की सीमा पूरी हुई।",
    },
    "fr": {
        "cli_description": "Harnais d'agent Argus",
        "help_prompt": "exécuter une tâche sans interface interactive",
        "help_workdir": "répertoire de travail",
        "help_model": "nom du modèle",
        "help_provider": "fournisseur de modèle (gemini, openai, openrouter, groq, ollama, anthropic)",
        "help_mode": "mode de sécurité",
        "help_resume": "reprendre la session la plus récente",
        "help_session": "reprendre un fichier de session précis",
        "help_list_sessions": "lister les sessions enregistrées et quitter",
        "help_yes": "approuver automatiquement les outils en mode sécurisé",
        "help_fleet": "exécuter un fichier JSON de flotte et quitter",
        "help_workers": "concurrence de la flotte",
        "help_max_turns": "nombre maximal de tours du modèle par tâche",
        "help_budget": "budget de jetons avant compactage",
        "help_lang": "langue de l'interface",
        "help_version": "afficher la version d'Argus",
        "banner": "Argus {version} | {provider}/{model} | mode={mode} | espace={workdir}",
        "prompt": "argus> ",
        "approval": "{name} {args}\nAutoriser ? [o/N] ",
        "no_session": "Aucune session Argus enregistrée.",
        "session_loaded": "Session reprise : {path}",
        "headless_warning": "Aucun approbateur en mode headless ; les outils de modification sont refusés. Utilisez --yes ou --mode yolo.",
        "bye": "Au revoir.",
        "help_body": (
            "Commandes : /help  /mode <safe|yolo|read-only>  /session  /tokens  "
            "/lang <en|es|hi|fr>  /exit"
        ),
        "tool_call": "[outil] {name} {args}",
        "blocked": "BLOQUÉ : {reason}",
        "error": "ERREUR : {error}",
        "no_sessions": "Aucune session enregistrée.",
        "tokens": "jetons : {input} entrée / {output} sortie",
        "mode_set": "Mode de sécurité : {mode}",
        "lang_set": "Langue : {language}",
        "unknown_command": "Commande inconnue : {command}. Tapez /help.",
        "interrupted": "Le journal de session est intact ; utilisez --resume pour continuer.",
        "session_path": "Session : {path}",
        "fleet_start": "Flotte : {count} tâche(s), {workers} travailleur(s)",
        "fleet_line": "[{index}/{count}] {name} : {status} ({seconds:.1f}s)",
        "fleet_done": "Flotte terminée.",
        "list_sessions_header": "Sessions dans {workdir}",
        "status_ok": "ok",
        "status_failed": "échec",
        "turn_limit": "Limite de tours atteinte.",
    },
}


def resolve_lang(explicit=None):
    """Resolve the interface language from a flag, environment, or locale."""
    if explicit in LANGUAGES:
        return explicit
    for variable in ("ARGUS_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable, "")
        code = value.split(".")[0].split("_")[0].split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


def t(key, lang=None, **values):
    """Translate a key, falling back to English and then to the key itself."""
    code = resolve_lang(lang)
    template = TRANSLATIONS.get(code, {}).get(key)
    if template is None:
        template = TRANSLATIONS["en"].get(key, key)
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template


def available_languages():
    """Return language codes and their display names."""
    return dict(LANGUAGES)
