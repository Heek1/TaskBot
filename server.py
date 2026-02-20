from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json, os, uvicorn

app = FastAPI()
DATA_FILE = "tasks.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {"tasks": [], "next_id": 1}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class TaskCreate(BaseModel):
    title: str
    user_id: int

class TaskUpdate(BaseModel):
    status: str

@app.get("/tasks/{user_id}")
def get_tasks(user_id: int):
    data = load()
    return [t for t in data["tasks"] if t["user_id"] == user_id]

@app.post("/tasks")
def create_task(task: TaskCreate):
    data = load()
    new_task = {"id": data["next_id"], "title": task.title, "status": "pending", "user_id": task.user_id}
    data["tasks"].append(new_task)
    data["next_id"] += 1
    save(data)
    return new_task

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    data = load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = update.status
            save(data)
            return t
    raise HTTPException(status_code=404, detail="Задачу не знайдено")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    data = load()
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    save(data)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)