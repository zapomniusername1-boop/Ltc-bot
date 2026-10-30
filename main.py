import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Простая HTML-страница входа для админки, адаптированная под телефон
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Bot Admin</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; width: 100%; max-width: 320px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h2 { text-align: center; margin-bottom: 20px; font-size: 20px; }
        input { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #3b82f6; border: none; border-radius: 6px; color: #fff; font-weight: bold; cursor: pointer; }
        button:hover { background: #2563eb; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Вход в админку</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return LOGIN_PAGE

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    # Тестовая проверка (потом заменим на базу данных)
    if username == "admin" and password == "12345":
        return "<h2>Добро пожаловать в твою панель управления! Вход выполнен успешно.</h2><a href='/'>Назад</a>"
    return "<h2>Неверный логин или пароль!</h2><a href='/'>Попробовать снова</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
