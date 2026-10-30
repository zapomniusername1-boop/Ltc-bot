 import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Память для хранения твоих личных данных
credentials = {
    "username": "",
    "password": "",
    "pin": ""
}

# 1. Страница регистрации (если данные еще не заданы)
SETUP_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Создание доступа</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; width: 100%; max-width: 320px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h2 { text-align: center; margin-bottom: 20px; font-size: 18px; color: #38bdf8; }
        input, button { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
        button { background: #3b82f6; border: none; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Придумай свои данные</h2>
        <form method="POST" action="/setup">
            <input type="text" name="new_user" placeholder="Твой логин" required>
            <input type="password" name="new_pass" placeholder="Твой пароль" required>
            <input type="password" name="new_pin" placeholder="ПИН-код для ботов" required>
            <button type="submit">Сохранить</button>
        </form>
    </div>
</body>
</html>
"""

# 2. Страница входа
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; width: 100%; max-width: 320px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h2 { text-align: center; margin-bottom: 20px; font-size: 20px; }
        input, button { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
        button { background: #3b82f6; border: none; font-weight: bold; cursor: pointer; }
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

# 3. Сама админка
ADMIN_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Bot Admin</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #fff; padding: 20px; margin: 0; display: flex; justify-content: center; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: 40px; }
        h2 { text-align: center; font-size: 20px; margin-bottom: 20px; }
        input, button { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
        button { background: #3b82f6; border: none; font-weight: bold; cursor: pointer; }
        .logout { background: #ef4444; margin-top: 10px; text-align: center; display: block; text-decoration: none; padding: 12px; border-radius: 6px; color: #fff; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Панель управления ботами</h2>
        <p style="color: #4ade80; font-size: 14px; text-align: center;">✔ Успешный вход</p>
        
        <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
        
        <h3 style="font-size: 16px;">Добавить нового бота</h3>
        <form method="POST" action="/add-bot">
            <input type="text" name="bot_name" placeholder="Имя бота" required>
            <input type="text" name="bot_token" placeholder="Токен бота от BotFather" required>
            <input type="password" name="pin_code" placeholder="Твой ПИН-код" required>
            <button type="submit">Запустить бота</button>
        </form>
        
        <a href="/" class="logout">Выйти</a>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    # Если логин еще не придуман — показываем экран создания
    if not credentials["username"]:
        return SETUP_PAGE
    return LOGIN_PAGE

@app.post("/setup", response_class=HTMLResponse)
async def setup(new_user: str = Form(...), new_pass: str = Form(...), new_pin: str = Form(...)):
    credentials["username"] = new_user
    credentials["password"] = new_pass
    credentials["pin"] = new_pin
    return "<h2 style='color:#4ade80;'>Данные успешно созданы!</h2><p>Теперь зайди на сайт снова.</p><a href='/'>На главную</a>"

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    if username == credentials["username"] and password == credentials["password"]:
        return ADMIN_PANEL
    return "<h2 style='color:red;'>Неверный логин или пароль!</h2><a href='/'>Попробовать снова</a>"

@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot(bot_name: str = Form(...), bot_token: str = Form(...), pin_code: str = Form(...)):
    if pin_code != credentials["pin"]:
        return "<h2 style='color:red;'>Неверный ПИН-код!</h2><a href='/'>Назад</a>"
    
    return f"<h2 style='color:#4ade80;'>ПИН-код верный!</h2><p>Бот '{bot_name}' принят.</p><a href='/'>Назад</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)