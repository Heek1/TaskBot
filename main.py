import asyncio
import os

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from dotenv import load_dotenv
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_http, daemon=True).start()
load_dotenv()

API_Token = os.getenv("BOT_TOKEN")
if not API_Token:
    print("token was not found")
else:
    print("Token found")

API_BASE  = "http://localhost:8000"

mybot = Bot(token=API_Token)
disp  = Dispatcher()

waiting_for_task = {}

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Список задач"), KeyboardButton(text="Нова задача")]
    ],
    resize_keyboard=True
)

async def api_get_tasks(user_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/tasks/{user_id}") as r:
                return await r.json()
    except aiohttp.ClientError:
        return None

async def api_add_task(user_id, title):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_BASE}/tasks", json={"title": title, "user_id": user_id}) as r:
                return await r.json()
    except aiohttp.ClientError:
        return None

async def api_update_task(task_id, status):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_BASE}/tasks/{task_id}", json={"status": status}) as r:
                return await r.json()
    except aiohttp.ClientError:
        return None

async def api_delete_task(task_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{API_BASE}/tasks/{task_id}") as r:
                return await r.json()
    except aiohttp.ClientError:
        return None


@disp.message(CommandStart())
async def start(msg: Message):
    await msg.answer("Привіт! Я бот для задач", reply_markup=main_kb)


@disp.message(F.text == "Список задач")
async def show_tasks(msg: Message):
    tasks = await api_get_tasks(msg.from_user.id)

    if tasks is None:
        await msg.answer("Помилка підключення до сервера.")
        return

    if not tasks:
        await msg.answer("У вас ще немає задач.")
        return

    buttons = []
    for t in tasks:
        status_label = {"pending": "Очікує", "in_progress": "В роботі", "done": "Виконано"}.get(t["status"], t["status"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{t['title']} [{status_label}]",
                callback_data=f"open:{t['id']}"
            )
        ])

    await msg.answer("Ваші задачі:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@disp.message(F.text == "Нова задача")
async def new_task(msg: Message):
    waiting_for_task[msg.from_user.id] = True
    await msg.answer("Введіть назву нової задачі:")


@disp.message(Command("cancel"))
async def cancel(msg: Message):
    waiting_for_task.pop(msg.from_user.id, None)
    await msg.answer("Скасовано.", reply_markup=main_kb)


@disp.message()
async def handle_text(msg: Message):
    if waiting_for_task.get(msg.from_user.id):
        waiting_for_task.pop(msg.from_user.id)
        task = await api_add_task(msg.from_user.id, msg.text)
        if task is None:
            await msg.answer("Помилка підключення до сервера.", reply_markup=main_kb)
            return
        await msg.answer(f"Задачу додано: {task['title']}", reply_markup=main_kb)
    else:
        await msg.answer("Скористайтесь кнопками меню.", reply_markup=main_kb)


@disp.callback_query(F.data.startswith("open:"))
async def open_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])

    tasks = await api_get_tasks(callback.from_user.id)

    if tasks is None:
        await callback.answer("Помилка підключення до сервера.", show_alert=True)
        return

    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        await callback.answer("Задачу не знайдено", show_alert=True)
        return

    status_labels = {"pending": "Очікує", "in_progress": "В роботі", "done": "Виконано"}
    text = f"{task['title']}\nСтатус: {status_labels.get(task['status'], task['status'])}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Очікує",   callback_data=f"status:{task_id}:pending"),
            InlineKeyboardButton(text="В роботі", callback_data=f"status:{task_id}:in_progress"),
            InlineKeyboardButton(text="Виконано", callback_data=f"status:{task_id}:done"),
        ],
        [InlineKeyboardButton(text="Видалити", callback_data=f"delete:{task_id}")],
        [InlineKeyboardButton(text="Назад",    callback_data="back")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@disp.callback_query(F.data.startswith("status:"))
async def change_status(callback: CallbackQuery):
    _, task_id, new_status = callback.data.split(":")
    result = await api_update_task(int(task_id), new_status)
    if result is None:
        await callback.answer("Помилка підключення до сервера.", show_alert=True)
        return
    await callback.answer("Статус оновлено")
    await open_task(callback)


@disp.callback_query(F.data.startswith("delete:"))
async def delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    result = await api_delete_task(task_id)
    if result is None:
        await callback.answer("Помилка підключення до сервера.", show_alert=True)
        return
    await callback.message.edit_text("Задачу видалено.")
    await callback.answer()


@disp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    tasks = await api_get_tasks(callback.from_user.id)

    if tasks is None:
        await callback.answer("Помилка підключення до сервера.", show_alert=True)
        return

    if not tasks:
        await callback.message.edit_text("У вас немає задач.")
        await callback.answer()
        return

    buttons = []
    for t in tasks:
        status_label = {"pending": "Очікує", "in_progress": "В роботі", "done": "Виконано"}.get(t["status"], t["status"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{t['title']} [{status_label}]",
                callback_data=f"open:{t['id']}"
            )
        ])

    await callback.message.edit_text("Ваші задачі:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


async def startBot():
    await disp.start_polling(mybot)

asyncio.run(startBot())