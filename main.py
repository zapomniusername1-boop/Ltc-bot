import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

SECRET_PIN = "7777"

# Загружаем HTML из отдельных файлов или сдаём встроенный безопасный формат
def render_login_page():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STELLA SYSTEM - ACCESS PORTAL</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: #070a13; 
            background-image: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            color: #f8fafc; 
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            padding: 20px;
        }
        .header-title { text-align: center; margin-bottom: 20px; }
        .header-title h1 { font-size: 16px; letter-spacing: 4px; color: #e2e8f0; font-weight: 500; }
        .header-title p { font-size: 10px; letter-spacing: 2px; color: #64748b; margin-top: 4px; }
        .card { 
            background: rgba(15, 23, 42, 0.65); 
            backdrop-filter: blur(16px);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 20px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 360px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15); 
        }
        .banner-container {
            width: 100%;
            height: 180px;
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop') center/cover no-repeat;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .banner-title {
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 6px;
            color: #ffffff;
            text-shadow: 0 0 20px rgba(56, 189, 248, 0.8), 0 0 10px rgba(0, 0, 0, 0.8);
        }
        .input-group { position: relative; margin-bottom: 14px; }
        input { 
            width: 100%; 
            padding: 14px 14px 14px 16px; 
            border-radius: 10px; 
            border: 1px solid rgba(148, 163, 184, 0.2); 
            background: rgba(15, 23, 42, 0.8); 
            color: #fff; 
            font-size: 15px;
            outline: none;
        }
        input:focus { border-color: #38bdf8; box-shadow: 0 0 12px rgba(56, 189, 248, 0.25); }
        button { 
            width: 100%;
            padding: 14px; 
            margin-top: 6px;
            border-radius: 10px;
            border: none;
            background: linear-gradient(135deg, #0284c7, #0369a1); 
            color: #fff;
            font-size: 15px;
            font-weight: 600; 
            cursor: pointer; 
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }
        .forgot-pass {
            display: block;
            text-align: center;
            margin-top: 18px;
            color: #94a3b8;
            font-size: 13px;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header-title">
        <h1>STELLA SYSTEM</h1>
        <p>ACCESS PORTAL</p>
    </div>

    <div class="card">
        <div class="banner-container">
            <div class="banner-title">STELLA</div>
        </div>

        <form method="POST" action="/login">
            <div class="input-group">
                <input type="text" name="username" placeholder="👤 Логин" required>
            </div>
            
            <div class="input-group">
                <input type="password" name="password" placeholder="🔒 Пароль" required>
            </div>
            
            <button type="submit">Авторизоваться</button>
        </form>

        <a href="#" class="forgot-pass" onclick="alert('Обратитесь к администратору системы.')">Забыли пароль?</a>
    </div>
</body>
</html>"""

def render_admin_page():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STELLA SYSTEM - PANEL</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: #070a13; 
            background-image: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            color: #f8fafc; 
            padding: 20px; 
            margin: 0; 
            display: flex; 
            justify-content: center; 
            align-items: center;
            min-height: 100vh;
        }
        .card { 
            background: rgba(15, 23, 42, 0.75); 
            backdrop-filter: blur(16px);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 24px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 400px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15); 
        }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { font-size: 20px; letter-spacing: 2px; color: #38bdf8; }
        h2 { text-align: center; font-size: 16px; margin-bottom: 15px; color: #cbd5e1; }
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
        }
        button { 
            background: linear-gradient(135deg, #0284c7, #0369a1); 
            border: none; 
            font-weight: bold; 
            cursor: pointer; 
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
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>STELLA SYSTEM</h1>
            <p style="color: #4ade80; font-size: 13px; margin-top: 6px;">✔ Панель активна</p>
        </div>
        
        <h2>Управление ботами</h2>
        <form method="POST" action="/add-bot">
            <input type="text" name="bot_name" placeholder="Имя бота" required>
            <input type="text" name="bot_token" placeholder="Токен бота от BotFather" required>
            <input type="password" name="pin_code" placeholder="ПИН-код (4 цифры)" pattern="[0-9]{4}" maxlength="4" inputmode="numeric" required>
            <button type="submit">Запустить бота</button>
        </form>
        
        <a href="/" class="logout">Выйти</a>
    </div>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return render_login_page()

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    return render_admin_page()

@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot(bot_name: str = Form(...), bot_token: str = Form(...), pin_code: str = Form(...)):
    if len(pin_code) != 4 or not pin_code.isdigit():
        return "<body style='background:#070a13;color:#fff;text-align:center;padding-top:50px;'><h2 style='color:#ef4444;'>❌ Ошибка! ПИН-код должен быть из 4 цифр.</h2><a href='/' style='color:#38bdf8;'>Назад</a></body>"
    
    if pin_code != SECRET_PIN:
        return "<body style='background:#070a13;color:#fff;text-align:center;padding-top:50px;'><h2 style='color:#ef4444;'>❌ Неверный ПИН-код!</h2><a href='/' style='color:#38bdf8;'>Назад</a></body>"
    
    return f"<body style='background:#070a13;color:#fff;text-align:center;padding-top:50px;'><h2 style='color:#4ade80;'>🚀 Бот '{bot_name}' запущен в STELLA SYSTEM!</h2><a href='/' style='color:#38bdf8;'>Назад в панель</a></body>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
