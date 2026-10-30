import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

SECRET_PIN = "7777"

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITLE__</title>
    <style>
        :root {
            --bg-color: #070a13;
            --bg-gradient: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            --card-bg: rgba(15, 23, 42, 0.75);
            --border-color: rgba(56, 189, 248, 0.3);
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --input-bg: rgba(15, 23, 42, 0.8);
            --input-border: rgba(100, 116, 139, 0.3);
        }
        [data-theme="light"] {
            --bg-color: #f1f5f9;
            --bg-gradient: radial-gradient(circle at 50% 30%, #e2e8f0 0%, #cbd5e1 100%);
            --card-bg: rgba(255, 255, 255, 0.85);
            --border-color: rgba(2, 132, 199, 0.3);
            --text-color: #0f172a;
            --text-muted: #475569;
            --input-bg: rgba(255, 255, 255, 0.95);
            --input-border: rgba(100, 116, 139, 0.3);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; transition: background 0.3s, color 0.3s; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--bg-color); 
            background-image: var(--bg-gradient);
            color: var(--text-color); 
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            padding: 20px;
            overflow-x: hidden;
        }
        
        /* Интро-анимация (Splash Screen) */
        #intro-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #070a13;
            background-image: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            transition: opacity 0.6s ease, visibility 0.6s ease;
        }
        .intro-content {
            text-align: center;
            animation: riseUpAndFade 1.4s cubic-bezier(0.77, 0, 0.175, 1) forwards;
        }
        .intro-title {
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 10px;
            color: #ffffff;
            text-shadow: 0 0 20px rgba(56, 189, 248, 0.6);
            margin-bottom: 8px;
        }
        .intro-line {
            width: 50px;
            height: 2px;
            background: #38bdf8;
            margin: 0 auto;
            box-shadow: 0 0 10px #38bdf8;
        }

        @keyframes riseUpAndFade {
            0% { transform: translateY(0); opacity: 1; }
            70% { transform: translateY(-30px); opacity: 1; }
            100% { transform: translateY(-60px); opacity: 0; visibility: hidden; }
        }

        .header-title { text-align: center; margin-bottom: 16px; position: relative; width: 100%; max-width: 360px; }
        .header-title h1 { font-size: 18px; letter-spacing: 4px; font-weight: 600; color: #38bdf8; }
        .header-title p { font-size: 11px; letter-spacing: 2px; color: var(--text-muted); margin-top: 4px; }
        
        .theme-toggle {
            position: absolute;
            right: 0;
            top: 0;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 6px 10px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            backdrop-filter: blur(10px);
        }

        .card { 
            background: var(--card-bg); 
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            padding: 24px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 360px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15); 
        }
        .banner-img {
            width: 100%;
            height: 160px;
            object-fit: cover;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: block;
        }
        input { 
            width: 100%; 
            padding: 13px; 
            margin-bottom: 12px;
            border-radius: 10px; 
            border: 1px solid var(--input-border); 
            background: var(--input-bg); 
            color: var(--text-color); 
            font-size: 14px;
            outline: none;
        }
        input:focus { border-color: #38bdf8; box-shadow: 0 0 10px rgba(56, 189, 248, 0.25); }
        button[type="submit"] { 
            width: 100%;
            padding: 13px; 
            margin-top: 4px;
            border-radius: 10px;
            border: none;
            background: linear-gradient(135deg, #0284c7, #0369a1); 
            color: #fff;
            font-size: 15px;
            font-weight: 600; 
            cursor: pointer; 
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }
        .logout { 
            background: rgba(239, 68, 68, 0.15); 
            border: 1px solid rgba(239, 68, 68, 0.3);
            margin-top: 12px; 
            text-align: center; 
            display: block; 
            text-decoration: none; 
            padding: 11px; 
            border-radius: 10px; 
            color: #fca5a5; 
            font-weight: 600; 
            font-size: 14px;
        }
    </style>
</head>
<body data-theme="dark">
    __INTRO__
    
    <div class="header-title">
        <h1>STELLA SYSTEM</h1>
        <p>ACCESS PORTAL</p>
        <button class="theme-toggle" onclick="toggleTheme()">🌓 Тема</button>
    </div>
    
    <div class="card">
        __CONTENT__
    </div>

    <script>
        function toggleTheme() {
            const body = document.body;
            const newTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('stella_theme', newTheme);
        }
        document.body.setAttribute('data-theme', localStorage.getItem('stella_theme') || 'dark');

        // Убираем заставку через 1.3 секунды после загрузки панели
        window.addEventListener('load', () => {
            const intro = document.getElementById('intro-screen');
            if (intro) {
                setTimeout(() => {
                    intro.style.opacity = '0';
                    setTimeout(() => intro.remove(), 600);
                }, 900);
            }
        });
    </script>
</body>
</html>"""

def get_page(content: str, title: str = "STELLA SYSTEM", show_intro: bool = False) -> str:
    intro_html = """
    <div id="intro-screen">
        <div class="intro-content">
            <div class="intro-title">STELLA</div>
            <div class="intro-line"></div>
        </div>
    </div>
    """ if show_intro else ""
    
    return BASE_TEMPLATE.replace("__TITLE__", title).replace("__CONTENT__", content).replace("__INTRO__", intro_html)

@app.get("/", response_class=HTMLResponse)
async def index():
    content = """
        <img src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=800&auto=format&fit=crop" alt="Stella Space" class="banner-img">
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="👤 Логин" required>
            <input type="password" name="password" placeholder="🔒 Пароль" required>
            <button type="submit">Авторизоваться</button>
        </form>
    """
    return get_page(content, "STELLA SYSTEM - LOGIN", show_intro=False)

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    content = """
        <div style="text-align:center; margin-bottom: 16px;">
            <p style="color: #4ade80; font-size: 13px; font-weight: 600;">✔ Панель активна</p>
            <h3 style="margin-top:6px; font-size:16px;">Управление ботами</h3>
        </div>
        <form method="POST" action="/add-bot">
            <input type="text" name="bot_name" placeholder="Имя бота" required>
            <input type="text" name="bot_token" placeholder="Токен бота от BotFather" required>
            <input type="password" name="pin_code" placeholder="ПИН-код (4 цифры)" pattern="[0-9]{4}" maxlength="4" inputmode="numeric" required>
            <button type="submit">Запустить бота</button>
        </form>
        <a href="/" class="logout">Выйти</a>
    """
    # show_intro=True включает анимацию только при переходе на страницу панели!
    return get_page(content, "STELLA SYSTEM - PANEL", show_intro=True)

@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot(bot_name: str = Form(...), bot_token: str = Form(...), pin_code: str = Form(...)):
    if len(pin_code) != 4 or not pin_code.isdigit():
        msg = "<h2 style='color:#ef4444; text-align:center;'>❌ Ошибка!</h2><p style='text-align:center; margin:10px 0;'>ПИН-код должен быть из 4 цифр.</p><a href='/' class='logout'>Назад</a>"
    elif pin_code != SECRET_PIN:
        msg = "<h2 style='color:#ef4444; text-align:center;'>❌ Неверный ПИН-код!</h2><a href='/' class='logout' style='margin-top:20px;'>Назад</a>"
    else:
        msg = f"<h2 style='color:#4ade80; text-align:center;'>🚀 Успех!</h2><p style='text-align:center; margin:10px 0;'>Бот <b>'{bot_name}'</b> запущен в STELLA SYSTEM!</p><a href='/' class='logout' style='margin-top:20px;'>Назад в панель</a>"
    
    return get_page(msg, "STELLA SYSTEM - STATUS", show_intro=False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
