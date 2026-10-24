# Argus

**एक ही डायरेक्टरी में वास्तविक काम के लिए एक छोटा, पारदर्शी Python एजेंट हार्नेस।**

[English](../../README.md) · [Español](README.es.md) · **हिन्दी** · [Français](README.fr.md)

Argus एक भाषा मॉडल को सीमित वर्कस्पेस टूल से जोड़ता है, हर क्रिया को पथ सीमा के
अंदर रखता है, टिकाऊ सत्र सहेजता है और सुरक्षा निर्णयों को पढ़ने योग्य कोड में
बदलता है। यह छह मॉडल प्रदाताओं और चार इंटरफ़ेस भाषाओं का समर्थन करता है, तथा
रनटाइम में किसी बाहरी निर्भरता की आवश्यकता नहीं है।

## Argus क्यों

- **छोटा और पारदर्शी:** प्रदाता, लूप, टूल, नीति, सत्र और संकुचन — हर सीमा
  अलग-अलग पढ़ी जा सकती है।
- **स्पष्ट सुरक्षा:** निषिद्ध कमांड सूची, पथ जेल, स्वीकृति प्रवाह, गोपनीय जानकारी
  छिपाना और वैकल्पिक सेमांटिक समीक्षा जो असुरक्षित होने पर ब्लॉक करती है।
- **टिकाऊ सत्र:** अधूरी JSONL पंक्तियाँ, बाधित टूल कॉल और प्रक्रिया पुनःआरंभ
  संभाले जाते हैं।
- **प्रदाता-न्यूट्रल:** Gemini, Anthropic, OpenAI, OpenRouter, Groq और स्थानीय
  Ollama एक ही संदेश प्रारूप साझा करते हैं।
- **शून्य रनटाइम निर्भरताएँ:** केवल Python 3.10+ स्टैंडर्ड लाइब्रेरी।

## त्वरित शुरुआत

Python 3.10 या नया संस्करण और किसी प्रदाता की API कुंजी (या स्थानीय Ollama) चाहिए।

```bash
git clone https://github.com/PRINCE2-AI/Argus.git
cd Argus
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env             # Windows: copy .env.example .env
```

`.env` में एक कुंजी जोड़ें:

```dotenv
GEMINI_API_KEY=आपकी-कुंजी
```

काम चलाएँ:

```bash
argus                                                  # इंटरैक्टिव
argus --prompt "hello.py बनाएँ, चलाएँ और परिणाम बताएँ" --yes
argus --prompt "इस रिपॉज़िटरी का सारांश दें" --mode read-only
argus --resume                                         # नवीनतम सत्र
argus --list-sessions
argus --lang hi
```

## प्रदाता

| प्रदाता | `--provider` | API कुंजी |
| --- | --- | --- |
| Google Gemini | `gemini` | `GEMINI_API_KEY` या `ARGUS_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` या `ARGUS_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` या `ARGUS_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` या `ARGUS_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` या `ARGUS_API_KEY` |
| स्थानीय Ollama | `ollama` | कोई नहीं |

मॉडल बदलने के लिए `--model` या `ARGUS_MODEL` उपयोग करें। Ollama जानबूझकर
`ARGUS_API_KEY` नहीं पढ़ता ताकि क्लाउड कुंजी localhost पर न जाए।

## Python API

```python
from argus import Harness, Policy

harness = Harness(
    workdir=".",
    provider="gemini",
    model="gemini-3.1-flash-lite",
    policy=Policy("safe"),
)
print(harness.run("एक स्टेटस फ़ाइल बनाएँ और सत्यापित करें।"))
```

`@tool` से अपने टूल जोड़कर उन्हें `extra_tools` में दें।

## सुरक्षा मॉडल

| मोड | व्यवहार |
| --- | --- |
| `read-only` | केवल पढ़ने वाले टूल। |
| `safe` (डिफ़ॉल्ट) | बदलाव करने वाले टूल के लिए इंटरैक्टिव स्वीकृति। |
| `yolo` | टूल स्वतः चलते हैं, लेकिन निषिद्ध कमांड सूची लागू रहती है। |

फ़ाइल पथ वर्कस्पेस के अंदर हल किए जाते हैं; `.env`, `.git` और `.argus`
सुरक्षित हैं। विनाशकारी कमांड, विशेषाधिकार वृद्धि, रिवर्स शेल और ज़बरदस्ती Git
संचालन ब्लॉक होते हैं। हेडलेस मोड में `safe` बदलाव अस्वीकार करता है जब तक
`--yes` न दिया जाए।

**Argus ऑपरेटिंग सिस्टम सैंडबॉक्स नहीं है।** अविश्वसनीय काम के लिए कंटेनर या
वर्चुअल मशीन का उपयोग करें।

## दस्तावेज़

- [आर्किटेक्चर](../ARCHITECTURE.md)
- [पोर्टफ़ोलियो नोट्स](../PORTFOLIO.md)
- [योगदान](../../CONTRIBUTING.md)
- [सुरक्षा](../../SECURITY.md)
- [चेंजलॉग](../../CHANGELOG.md)

## लाइसेंस

MIT। [LICENSE](../../LICENSE) देखें।
