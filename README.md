# JARVIS 🤖

עוזר אישי חכם (AI Assistant) מודולרי בהשראת JARVIS מסרטי Iron Man — מנוע "מוח" מרובה-ספקים (Gemini + Groq עם fail-over אוטומטי), למעלה מ-60 "יכולות" (Skills) שניתן להרחיב אוטומטית, זיכרון סמנטי מבוסס embeddings, ראייה ממוחשבת, זיהוי פנים וקול, ותצוגת HUD/מעבדה תלת-ממדית בדפדפן.

> ⚠️ **סטטוס הפרויקט**: זהו ריפו בעבודה (work-in-progress). חלק מהקבצים המרכזיים שהקוד הקיים מייבא (`app.py`, `safety_manager.py`, `coder_agent.py`, `filesystem_watcher.py`, `static/style.css`) **לא נמצאים כרגע בריפו**. ראו סעיף [פערים ידועים](#-פערים-ידועים--todo) לפני שאתם מנסים להריץ את המערכת כמכלול.

## 📖 תוכן עניינים

- [סקירה כללית](#-סקירה-כללית)
- [ארכיטקטורה](#-ארכיטקטורה)
- [דרישות מקדימות](#-דרישות-מקדימות)
- [התקנה](#-התקנה)
- [משתני סביבה (.env)](#-משתני-סביבה-env)
- [הרצה](#-הרצה)
- [קטלוג היכולות (Skills)](#-קטלוג-היכולות-skills)
- [יצירת Skill חדש](#-יצירת-skill-חדש)
- [בדיקות (Tests)](#-בדיקות-tests)
- [מבנה הפרויקט](#-מבנה-הפרויקט)
- [פערים ידועים / TODO](#-פערים-ידועים--todo)

## 🔎 סקירה כללית

JARVIS בנוי סביב רעיון של **מוח מרכזי** (`NeuralSwitchboard`) שמדבר עם ספקי LLM שונים (Gemini כברירת מחדל, עם נפילה אוטומטית ל-Groq בעת חריגת מכסה), ו**מרשם יכולות** (`SKILL_REGISTRY`) שמתאר לכל יכולת את השם, התיאור, הפרמטרים ורמת הסיכון שלה — כדי שסוכן ה-AI ידע איזה כלים יש לו ומתי להשתמש בהם.

כל יכולת (Skill) היא קובץ Python עצמאי תחת [skills/](skills/) עם פונקציית `execute(params)` — כך שקל להוסיף יכולות חדשות בלי לגעת בליבת המערכת (וקיים אפילו מנוע לסינתוז יכולות אוטומטי, ראו [skill_synthesis_engine.py](skill_synthesis_engine.py)).

יכולות עיקריות:
- 🧠 **מוח רב-ספקי** — [utils/neural_switchboard.py](utils/neural_switchboard.py): Gemini + Groq, סבב מפתחות (key rotation) אוטומטי, תמיכה בסטרימינג ובתמונות.
- 🗣️ **קול** — האזנה (`speech_recognition`/Vosk) ודיבור (`edge-tts` / ElevenLabs) עם עיבוד טקסט-לדיבור ([speech_formatter.py](speech_formatter.py)) ואימות דובר קולי ([utils/voice_verifier.py](utils/voice_verifier.py)).
- 👁️ **ראייה** — צילום מסך וניתוחו, מצלמה, OCR, זיהוי פנים ([skills/vision.py](skills/vision.py), [skills/screen_analysis.py](skills/screen_analysis.py), [skills/face_rec.py](skills/face_rec.py)).
- 🧩 **זיכרון סמנטי** — [semantic_memory.py](semantic_memory.py) שומר "זכרונות" כווקטורי embedding (Gemini) בקובץ [semantic_index.json](semantic_index.json) ומאפשר חיפוש דמיון סמנטי.
- ⏰ **תזמון ומעקב** — [scheduler_system.py](scheduler_system.py), [system_sentinel.py](system_sentinel.py), [skills/reminders.py](skills/reminders.py), [skills/timer.py](skills/timer.py).
- 🏠 **בית חכם / הודעות** — Home Assistant, WhatsApp (Twilio), Telegram, Discord, Email, iMessage.
- 🌐 **HUD תלת-ממדי בדפדפן** — [templates/index.html](templates/index.html) ו-[templates/lab.html](templates/lab.html) עם Three.js ו-Socket.IO, מוזנים ע"י [topology_engine.py](topology_engine.py) שממפה את גרף הקבצים/הזכרונות של הפרויקט.

## 🏗️ ארכיטקטורה

```
                     ┌─────────────────────┐
                     │   NeuralSwitchboard  │  utils/neural_switchboard.py
                     │  (Gemini ⇄ Groq)      │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   SKILL_REGISTRY      │  utils/skill_registry.py
                     │  (חוזה פרמטרים + risk) │
                     └──────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                        │
 ┌──────▼──────┐        ┌───────▼───────┐        ┌───────▼───────┐
 │ skills/*.py │        │ semantic_memory│        │ scheduler /   │
 │ (60+ יכולות) │        │ (embeddings)   │        │ system_sentinel│
 └─────────────┘        └────────────────┘        └────────────────┘
                                │
                     ┌──────────▼───────────┐
                     │  topology_engine.py   │ → templates/lab.html (HUD תלת-ממדי)
                     └───────────────────────┘
```

כל Skill מקבל מילון `params` (ולעיתים מפתח מיוחד `_chat` — אובייקט שיחה פעיל עם ה-LLM) ומחזיר מחרוזת תשובה שמוקראת/מוצגת למשתמש.

## ✅ דרישות מקדימות

| דרישה | הערות |
|---|---|
| Python 3.11+ (נבדק על 3.13) | |
| Git | |
| מיקרופון + רמקולים | ליכולות הקול |
| [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) מותקן ונגיש דרך PATH | נדרש ל-`pytesseract` ([skills/screen_analysis.py](skills/screen_analysis.py)) |
| מפתח API ל-Gemini (חובה) ו/או Groq | ראו [משתני סביבה](#-משתני-סביבה-env) |
| macOS | חלק ניכר מהיכולות (`smart_action`, `spotify`, `messenger`/iMessage, `shortcuts`, `browser` דרך AppleScript) מניחות macOS. תחת Windows הן פשוט ייכשלו בעדינות. |

## 📦 התקנה

```bash
# 1. שכפול הריפו
git clone <repo-url> jarvis
cd jarvis

# 2. יצירת סביבה וירטואלית
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. התקנת תלויות
pip install -r requirements.txt

# 4. הגדרת משתני סביבה
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
# ולאחר מכן לערוך את .env ולמלא מפתחות API

# 5. (אופציונלי) הורדת מודל Vosk לזיהוי דיבור אופליין
python setup_vosk.py
```

> קובץ `.env.example` אינו קיים עדיין בריפו — יש ליצור אותו (או קובץ `.env` ישירות) בהתאם לטבלה שבסעיף הבא.

## 🔑 משתני סביבה (.env)

| משתנה | חובה? | שימוש |
|---|---|---|
| `GEMINI_API_KEYS` | **כן** | מפתח/י Gemini, מופרדים בפסיק/רווח — מאפשר סבב אוטומטי בין כמה מפתחות |
| `GEMINI_MODEL` | לא (ברירת מחדל `gemini-2.0-flash`) | מודל Gemini לשימוש |
| `GROQ_API_KEY` | לא | Fail-over כאשר Gemini חורג ממכסה |
| `OPENWEATHER_API_KEY` | לא | [skills/weather.py](skills/weather.py) |
| `JARVIS_CITY` | לא | עיר ברירת מחדל למזג האוויר |
| `NEWS_API_KEY` | לא | [skills/news.py](skills/news.py) |
| `EMAIL_USER` / `EMAIL_PASS` | לא | שליחת מיילים ([skills/email_sender.py](skills/email_sender.py)) |
| `TELEGRAM_BOT_TOKEN` | לא | [skills/messenger.py](skills/messenger.py) |
| `DISCORD_WEBHOOK_URL` | לא | [skills/messenger.py](skills/messenger.py) |
| `TWILIO_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` | לא | שליחת WhatsApp ([skills/send_whatsapp_message.py](skills/send_whatsapp_message.py)) |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | לא | קול איכותי יותר ([skills/speak.py](skills/speak.py)), נופל חזרה ל-`edge-tts` |
| `HA_URL` / `HA_TOKEN` | לא | Home Assistant ([skills/smart_home.py](skills/smart_home.py)) |
| `JARVIS_VAULT_MASTER` | לא | סיסמת מאסטר לאחסון סודות מוצפן ([skills/vault.py](skills/vault.py)) |
| `JARVIS_VOICE_THRESHOLD` | לא (ברירת מחדל `0.78`) | סף אימות טביעת קול ([utils/voice_verifier.py](utils/voice_verifier.py)) |

## ▶️ הרצה

אין כרגע נקודת כניסה מרכזית (`app.py`/`main.py`) בריפו — ראו [פערים ידועים](#-פערים-ידועים--todo). ניתן כן להריץ ולבדוק רכיבים בודדים:

```bash
# בדיקת תקינות חיבור ל-Gemini/Groq + מצלמה + TTS
python test_jarvis.py

# בדיקת מנוע ה"מוח" (fail-over בין Gemini ל-Groq)
python test_switchboard.py

# הפקת גרף הטופולוגיה של הפרויקט (JSON) — מוזן ל-HUD התלת-ממדי
python topology_engine.py
```

## 🧠 קטלוג היכולות (Skills)

הרשימה המלאה, כולל תיאור, פרמטרים ורמת סיכון לכל יכולת, מוגדרת ב-[utils/skill_registry.py](utils/skill_registry.py). דוגמאות עיקריות לפי קטגוריה:

| קטגוריה | יכולות לדוגמה |
|---|---|
| שיחה ומידע | `web_search`, `weather`, `news`, `translate`, `summarize`, `calculator`, `convert` |
| מערכת ואוטומציה | `smart_action`, `open_app`, `shell_execution`, `file_management`, `run_script`, `system_monitor`, `volume` |
| קלט/פלט פיזי | `mouse_control`, `keyboard_control`, `camera`, `vision`, `screen_capture`, `screen_analysis`, `ocr` |
| תקשורת | `email_sender`, `send_whatsapp_message`, `messenger` (iMessage/Telegram/Discord) |
| ניהול אישי | `calendar`, `reminders`, `notes`, `timer`, `health`, `mood`, `daily_briefing` |
| זיכרון וידע | `learn`, `recall_memory`, `knowledge_base`, `synthesize_skill` |
| בית חכם ומדיה | `smart_home`, `spotify`, `notifications` |
| אבטחה | `vault` (אחסון סודות מוצפן), `face_rec` |

## 🛠️ יצירת Skill חדש

1. ליצור קובץ חדש תחת [skills/](skills/), למשל `skills/my_skill.py`, עם פונקציה:
   ```python
   def execute(params):
       ...
       return "תשובה למשתמש"
   ```
2. לרשום את היכולת במילון `SKILL_REGISTRY` ב-[utils/skill_registry.py](utils/skill_registry.py) — שם, תיאור, פרמטרים ורמת סיכון (`risk`: 0 רגיל, 1 מסוכן/דורש אישור).
3. ניתן גם להיעזר בכלי הבדיקה [skills/test_skill.py](skills/test_skill.py) או במנוע הסינתזה האוטומטי ([skill_synthesis_engine.py](skill_synthesis_engine.py)) שיוצר, בודק ומתקן יכולת חדשה אוטומטית באמצעות ה-AI (דורש את `coder_agent.py` שחסר כרגע — ראו למטה).

## 🧪 בדיקות (Tests)

| קובץ | מטרה |
|---|---|
| [test_jarvis.py](test_jarvis.py) | בדיקת חיבור AI, מצלמה ו-TTS |
| [test_switchboard.py](test_switchboard.py) | בדיקת ה-`NeuralSwitchboard` (Gemini/Groq) |
| [test_brain.py](test_brain.py) | בדיקת חיבור בסיסי ל-Gemini |
| [test_embeddings.py](test_embeddings.py) | בדיקת חילוץ embeddings |
| [test_groq_direct.py](test_groq_direct.py) | בדיקת חיבור ישיר ל-Groq |
| [test_all_skills.py](test_all_skills.py) | טעינת כל קבצי ה-skills ובדיקת תקינות ה-imports |
| [test_skills.py](test_skills.py) | הרצת מספר יכולות מדגמיות |

## 📁 מבנה הפרויקט

```
jarvis/
├── skills/                  # 60+ יכולות פלאגין (execute(params) בכל קובץ)
├── utils/
│   ├── neural_switchboard.py   # ה"מוח" — Gemini/Groq עם fail-over
│   ├── skill_registry.py       # קטלוג היכולות + חוזה פרמטרים
│   ├── audio_manager.py        # ניהול נגינת/הקלטת אודיו
│   ├── voice_verifier.py       # אימות טביעת קול (MFCC)
│   ├── system_discovery.py     # זיהוי סביבת המערכת
│   └── speech_formatter.py     # ניקוי טקסט להקראה
├── templates/                # HUD בדפדפן (index.html, lab.html) — Three.js + Socket.IO
├── static/                   # CSS/JS ל-HUD
├── semantic_memory.py         # זיכרון סמנטי מבוסס embeddings
├── semantic_index.json        # אחסון הזכרונות בפועל
├── scheduler_system.py        # מתזמן משימות ברקע
├── system_sentinel.py         # ניטור מערכת מתמשך
├── skill_synthesis_engine.py  # יצירת יכולות חדשות אוטומטית ע"י AI
├── topology_engine.py         # מיפוי גרף קבצים/זכרונות לצורך ה-HUD
├── speech_formatter.py        # פורמט טקסט לדיבור
├── visual_observer.py         # צפייה מתמשכת במסך
├── setup_vosk*.py             # הורדת מודלים ל-STT אופליין (Vosk)
├── requirements.txt
└── test_*.py                  # סקריפטי בדיקה עצמאיים
```

## ⚠️ פערים ידועים / TODO

בסריקת הקוד נמצאו ייבואים (`import`) לקבצים שאינם קיימים בריפו הנוכחי — כנראה נשכחו מההעלאה. יש להוסיף אותם (או להסיר את התלות בהם) כדי שהמערכת תרוץ כמכלול:

- **`app.py`** — לא קיימת נקודת כניסה ראשית (שרת Flask/Socket.IO שמגיש את [templates/index.html](templates/index.html) ואת ה-HUD). ה-templates מפנים ל-`static/style.css` שגם הוא חסר.
- **`safety_manager.py`** — מיובא ע"י כ-20 קבצי skills (`shell_execution`, `file_management`, `browser`, `mouse_control`, `keyboard_control` ועוד) לצורך `audit_log` ובקרת סיכונים. חסר לגמרי.
- **`coder_agent.py`** — נדרש ל-[skill_synthesis_engine.py](skill_synthesis_engine.py) (יצירת יכולות חדשות אוטומטית ע"י AI).
- **`filesystem_watcher.py`** — נדרש ל-[system_sentinel.py](system_sentinel.py).
- אין קובץ `.gitignore` — מומלץ להוסיף אחד שמתעלם מ-`.venv/`, `__pycache__/`, `.env`, `*.pyc`, `model/` (תיקיית מודל Vosk).
- קבצי בדיקה זמניים (`test_output.txt`, `test_watch.txt`, `tmp_replace.py`) נמצאים בריפו — כדאי לבדוק אם עדיין נחוצים.
