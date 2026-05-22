# My-Steelman

Steelman Counter-Argument Generator — AI-driven debate adversary.

Enter any argument. The AI generates the 3 strongest counter-arguments in steelman fashion: it attacks the most defensible version of your claim, not a weak strawman. Find your blind spots before others do.

## Features

- **Steelman Counter-Arguments** — DeepSeek generates the 3 strongest rebuttals against your argument
- **Severity Score (1–100)** — How hard each counter-argument is to defend against
- **Average Severity Gauge** — At-a-glance vulnerability of your overall position
- **Overall Verdict** — Defensibility assessment of your original claim

## Prerequisites

- Python 3.10+
- DeepSeek API key

## Setup

```bash
git clone https://github.com/kernullist/my-steelman.git
cd my-steelman
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and insert your DeepSeek API key:

```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

## Run

```bash
python main.py
```

Open `http://127.0.0.1:8000` in your browser.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | _(required)_ | DeepSeek API key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model ID |
| `PORT` | `8000` | Server port |

## Tech Stack

- **Backend:** FastAPI + DeepSeek API (OpenAI-compatible)
- **Frontend:** Vanilla HTML/CSS/JS (dark theme)
- **Infra:** Python, Uvicorn
