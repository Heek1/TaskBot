# TaskBot

A Telegram bot for a personal to-do list, backed by a small REST API. Each user sees only their own tasks and moves them through three statuses with inline buttons.

The bot speaks Ukrainian.

## How it works

```
Telegram ──► bot (aiogram 3) ──HTTP──► API (FastAPI) ──► tasks.json
```

- **`main.py`** is the bot. Two menu buttons: *Список задач* (task list) and *Нова задача* (new task). Tapping a task opens it with buttons to set its status (*pending*, *in progress*, *done*), delete it or go back. `/cancel` stops adding a task. A tiny health-check server answers on `PORT` (default `10000`), so the bot can run on hosting that expects a web port.
- **`server.py`** is the API the bot calls. Tasks are stored in `tasks.json`, which is created on first use.

| Method | Path | Does |
|---|---|---|
| `GET` | `/tasks/{user_id}` | List a user's tasks |
| `POST` | `/tasks` | Create a task: `{"title": "...", "user_id": 123}` |
| `PATCH` | `/tasks/{task_id}` | Change status: `{"status": "done"}` |
| `DELETE` | `/tasks/{task_id}` | Delete a task |

## Run it

Requires Python 3.10 or newer and a bot token from [@BotFather](https://t.me/BotFather).

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your token into BOT_TOKEN
python server.py            # API on http://localhost:8000
python main.py              # the bot, in a second terminal
```

The API also serves interactive docs at `http://localhost:8000/docs`.

## Stack

Python, aiogram 3, aiohttp, FastAPI, Pydantic, Uvicorn.
