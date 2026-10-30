import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

ADMIN_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CosmoMarket Bot Admin</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: radial-gradient(circle at center, #1e1b4b 0%, #0f172a 70%, #020617 100%); 
            color: #f8fafc; 
            padding: 20px; 
            margin: 0; 
            display: flex; 
            justify-content: center; 
            min-height: 100vh;
            align-items: center;
        }
        .card { 
            background: rgba(30, 41, 59, 0.75); 
            backdrop-filter: blur(12px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 24px; 
            border-radius: 16px; 
            width: 100%; 
            max-width: 400px; 
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.1); 
        }
        .brand-logo {
            text-align: center;
            margin-bottom: 20px;
        }
        .brand-logo h1 {
            font-size: 22px;
            margin: 0;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }
        .brand-logo p {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }
        h2 { text-align: center; font-size: 18px; margin-bottom: 15px; color: #e2e8f0; }
        input, button { 
            width: 100%; 
            padding: 12px; 
            margin-bottom: 14px; 
            border-radius: 8px; 
            border: 1px solid rgba(100, 116, 139, 0.4); 
            background: rgba(15, 23, 42, 0.8); 
            color: #fff; 
            box-sizing: border-box; 
            font-size: 14px;
            transition: all 0.3s ease;
        }
        input:focus {
            border-color: #38bdf8;
            outline: none;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
        }
        button { 
            background: linear-gradient(135deg, #3b82f6, #6366f1); 
            border: none; 
            font-weight: bold; 
            cursor: pointer; 
        }
        button:hover { 
            background: linear-gradient(135deg, #2563eb, #4f46e5); 
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.5);
        }
        .logout { 
            background: rgba(239, 68, 68, 0.2); 
            border: 1px solid rgba(239, 68, 68, 0.4);
            margin-top: 10px; 
            text-align: center; 
            display: block; 
            text-decoration: none; 
            padding: 12px; 
            border-radius: 8px; 
            color: #fca5a5; 
            font-weight: bold; 
            transition: 0.3s;
        }
        .logout:hover {
            background: rgba(239, 68, 68, 0.4);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-logo">
            <h1>🌌 COSMO MARKET</h1>
            <p>Next-Gen Bot Ecosystem</p>
        </div>
        
        <h2>Панель управления ботами</h2>
        <p style="color: #4ade80; font-size: 13px; text-align: center; margin-bottom: 20px;">✔ Система активна</p>
        
        <form method="POST" action="/add-bot">
            <input type="text" name="bot_name" placeholder="Имя бота" required>
            <input type="text" name="bot_token" placeholder="Токен бота от BotFather" required>
            <input type="password" name="pin_code" placeholder="ПИН-код (4 цифры)" pattern="[0-9]{4}" maxlength="4" inputmode="numeric" required>
            <button type="submit">Запустить бота в сеть</button>
        </form>
        
        <a href="/" class="logout">Выйти</a>
    </div>
</body>
</html>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CosmoMarket - Login</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: radial-gradient(circle at center, #1e1b4b 0%, #0f172a 70%, #020617 100%); 
            color: #f8fafc; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
        }
        .card { 
            background: rgba(30, 41, 59, 0.75); 
            backdrop-filter: blur(12px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 24px; 
            border-radius: 16px; 
            width: 100%; 
            max-width: 340px; 
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); 
        }
        .brand-logo {
            text-align: center;
            margin-bottom: 20px;
        }
        .brand-logo h1 {
            font-size: 20px;
            margin: 0;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        h2 { text-align: center; margin-bottom: 20px; font-size: 18px; color: #e2e8f0; }
        input, button { 
            width: 100%; 
            padding: 12px; 
            margin-bottom: 14px; 
            border-radius: 8px; 
            border: 1px solid rgba(100, 116, 139, 0.4); 
            background: rgba(15, 23, 42, 0.8); 
            color: #fff; 
            box-sizing: border-box; 
        }
        input:focus {
            border-color: #38bdf8;
            outline: none;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
        }
        button { 
            background: linear-gradient(135deg, #3b82f6, #6366f1); 
            border: none; 
            font-weight: bold; 
            cursor: pointer; 
        }
        button:hover { 
            background: linear-gradient(135deg, #2563eb, #4f46e5); 
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-logo">
            <h1>🌌 COSMO MARKET</h1>
        </div>
        <h2>Вход в систему</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Авторизоваться</button>
        </form>
    </div>
</body>
</html>
"""

SECRET_PIN = "7777"

@app.get("/", response_class=HTMLResponse)
async def index():
    return LOGIN_PAGE

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    return ADMIN_PANEL

@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot(bot_name: str = Form(...), bot_token: str = Form(...), pin_code: str = Form(...)):
    if len(pin_code) != 4 or not pin_code.isdigit():
        return "<body style='background:#0f172a;color:#fff;text-align:center;padding-top:50px;font-family:sans-serif;'><h2 style='color:#ef4444;'>❌ Ошибка!</h2><p>ПИН-код должен состоять ровно из 4 цифр.</p><a href='/' style='color:#38bdf8;'>Назад</a></body>"
    
    if pin_code != SECRET_PIN:
        return "<body style='background:#0f172a;color:#fff;text-align:center;padding-top:50px;font-family:sans-serif;'><h2 style='color:#ef4444;'>❌ Неверный ПИН-код!</h2><p>Попробуйте снова (подсказка: 7777).</p><a href='/' style='color:#38bdf8;'>Назад</a></body>"
    
    return f"<body style='background:#0f172a;color:#fff;text-align:center;padding-top:50px;font-family:sans-serif;'><h2 style='color:#4ade80;'>🚀 Бот '{bot_name}' запущен в космос!</h2><p>ПИН-код подтвержден успешно.</p><a href='/' style='color:#38bdf8;'>Назад в панель</a></body>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
