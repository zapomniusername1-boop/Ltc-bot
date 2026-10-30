import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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
            transition: opacity 0.8s ease, visibility 0.8s ease;
        }
        .intro-content {
            text-align: center;
            animation: riseUpAndFade 3s cubic-bezier(0.77, 0, 0.175, 1) forwards;
        }
        .intro-title {
            font-size: 34px;
            font-weight: 700;
            letter-spacing: 12px;
            color: #ffffff;
            text-shadow: 0 0 25px rgba(56, 189, 248, 0.8);
            margin-bottom: 8px;
        }
        .intro-line {
            width: 60px;
            height: 2px;
            background: #38bdf8;
            margin: 0 auto;
            box-shadow: 0 0 12px #38bdf8;
        }

        @keyframes riseUpAndFade {
            0% { transform: translateY(0); opacity: 1; }
            75% { transform: translateY(0); opacity: 1; }
            100% { transform: translateY(-40px); opacity: 0; visibility: hidden; }
        }

        .header-container {
            width: 100%;
            max-width: 420px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .header-title h1 { font-size: 16px; letter-spacing: 3px; font-weight: 600; color: #38bdf8; }
        .header-title p { font-size: 10px; letter-spacing: 2px; color: var(--text-muted); }
        
        .menu-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 8px 10px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .sidebar {
            position: fixed;
            top: 0;
            left: -280px;
            width: 280px;
            height: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border-right: 1px solid var(--border-color);
            z-index: 1000;
            padding: 24px;
            transition: left 0.3s ease;
        }
        .sidebar.open { left: 0; }
        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        .sidebar-menu a {
            display: block;
            color: var(--text-color);
            text-decoration: none;
            padding: 12px 0;
            border-bottom: 1px solid var(--input-border);
            font-size: 14px;
            font-weight: 500;
        }
        .sidebar-menu a:hover { color: #38bdf8; }

        .theme-toggle {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 6px 10px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
        }

        .card { 
            background: var(--card-bg); 
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            padding: 24px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 420px; 
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
    
    __HEADER__
    
    __SIDEBAR__
    
    <div class="card">
        __CONTENT__
    </div>

    <script>
        function toggleSidebar() {
            const sb = document.getElementById('sidebar');
            if (sb) sb.classList.toggle('open');
        }
        function toggleTheme() {
            const body = document.body;
            const newTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('stella_theme', newTheme);
        }
        document.body.setAttribute('data-theme', localStorage.getItem('stella_theme') || 'dark');

        window.addEventListener('load', () => {
            const intro = document.getElementById('intro-screen');
            if (intro) {
                setTimeout(() => {
                    intro.style.opacity = '0';
                    setTimeout(() => intro.remove(), 800);
                }, 2800);
            }
        });
    </script>
</body>
</html>"""

def get_page(content: str, title: str = "STELLA SYSTEM", show_intro: bool = False, show_full_nav: bool = False) -> str:
    intro_html = """
    <div id="intro-screen">
        <div class="intro-content">
            <div class="intro-title">STELLA</div>
            <div class="intro-line"></div>
        </div>
    </div>
    """ if show_intro else ""
    
    if show_full_nav:
        header_html = """
        <div class="header-container">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div class="header-title" style="text-align: center;">
                <h1>STELLA SYSTEM</h1>
                <p>PANEL DASHBOARD</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">🌓</button>
        </div>
        """
        sidebar_html = """
        <div id="sidebar" class="sidebar">
            <div class="sidebar-header">
                <h3>Меню</h3>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <div class="sidebar-menu">
                <a href="#" onclick="alert('Вы уже в панели управления')">🏠 Главная панель</a>
                <a href="#" onclick="alert('Графика и баланс: Система активна, баланс: 1,450 ST')">📊 Графика и Баланс</a>
                <a href="#" onclick="alert('Все системные узлы функционируют в штатном режиме')">⚙️ Системные настройки</a>
                <a href="/" style="color: #fca5a5;">🚪 Выход</a>
            </div>
        </div>
        """
    else:
        header_html = """
        <div class="header-container" style="justify-content: center; position: relative;">
            <div class="header-title" style="text-align: center;">
                <h1>STELLA SYSTEM</h1>
                <p>ACCESS PORTAL</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()" style="position: absolute; right: 0; top: 0;">🌓</button>
        </div>
        """
        sidebar_html = ""

    return BASE_TEMPLATE.replace("__TITLE__", title).replace("__CONTENT__", content).replace("__INTRO__", intro_html).replace("__HEADER__", header_html).replace("__SIDEBAR__", sidebar_html)

# Шаг 1: Логин и пароль (с картинкой космоса)
@app.get("/", response_class=HTMLResponse)
async def index():
    content = """
        <img src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=800&auto=format&fit=crop" alt="Stella Space" class="banner-img">
        <form method="POST" action="/verify-pin">
            <input type="text" name="username" placeholder="👤 Логин" required>
            <input type="password" name="password" placeholder="🔒 Пароль" required>
            <button type="submit">Войти</button>
        </form>
    """
    return get_page(content, "STELLA SYSTEM - LOGIN", show_intro=False, show_full_nav=False)

# Шаг 2: Ввод ПИН-кода
@app.post("/verify-pin", response_class=HTMLResponse)
async def verify_pin_page(username: str = Form(...), password: str = Form(...)):
    content = f"""
        <div style="text-align:center; margin-bottom: 16px;">
            <p style="color: #38bdf8; font-size: 13px; font-weight: 600;">🔐 Безопасность STELLA</p>
            <h3 style="margin-top:6px; font-size:16px;">Введите 4-значный ПИН-код</h3>
        </div>
        <form method="POST" action="/check-pin">
            <input type="hidden" name="username" value="{username}">
            <input type="password" name="pin_code" placeholder="• • • •" maxlength="4" inputmode="numeric" style="text-align:center; font-size: 20px; letter-spacing: 8px;" required>
            <button type="submit">Подтвердить</button>
        </form>
        <a href="/" class="logout">Отмена</a>
    """
    return get_page(content, "STELLA SYSTEM - PIN", show_intro=False, show_full_nav=False)

# Шаг 3: Панель управления ботами (доступна после правильного ПИН-кода)
@app.post("/check-pin", response_class=HTMLResponse)
async def check_pin(username: str = Form(...), pin_code: str = Form(...)):
    if pin_code != SECRET_PIN:
        return RedirectResponse(url="/", status_code=303)
    
    content = """
        <div style="text-align:center; margin-bottom: 16px;">
            <p style="color: #4ade80; font-size: 13px; font-weight: 600;">✔ Доступ разрешен</p>
            <h3 style="margin-top:6px; font-size:16px;">Управление ботами</h3>
        </div>
        <form method="POST" action="/add-bot">
            <input type="text" name="bot_name" placeholder="Имя бота" required>
            <input type="text" name="bot_token" placeholder="Токен бота от BotFather" required>
            <button type="submit">Запустить бота</button>
        </form>
        <a href="/" class="logout">Выйти</a>
    """
    return get_page(content, "STELLA SYSTEM - PANEL", show_intro=False, show_full_nav=False)

# Шаг 4: Финал — Анимация STELLA + появление 3 полосок (меню) и дашборда с балансом/графикой внутри!
@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot(bot_name: str = Form(...), bot_token: str = Form(...)):
    msg = f"""
        <div style="text-align:center; padding: 10px 0;">
            <h2 style='color:#4ade80; margin-bottom: 10px;'>🚀 Успех!</h2>
            <p style='color:var(--text-color); margin-bottom: 16px;'>Бот <b>'{bot_name}'</b> запущен в систему.</p>
            
            <!-- Блок графики и баланса -->
            <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 14px; margin-bottom: 16px; text-align: left;">
                <p style="font-size: 12px; color: var(--text-muted);">АКТИВНЫЙ БАЛАНС СИСТЕМЫ</p>
                <h3 style="font-size: 20px; color: #38bdf8; margin: 4px 0 12px 0;">1,450.00 ST</h3>
                <p style="font-size: 12px; color: var(--text-muted);">ТЕЛЕМЕТРИЯ ЯДРА</p>
                <div style="width: 100%; height: 6px; background: rgba(56, 189, 248, 0.2); border-radius: 3px; margin-top: 6px; overflow: hidden;">
                    <div style="width: 75%; height: 100%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8;"></div>
                </div>
            </div>

            <a href='/check-pin' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>Вернуться к ботам</a>
        </div>
    """
    # show_intro=True запускает 3-секундную анимацию STELLA, а show_full_nav=True включает 3 полоски (меню) в шапке!
    return get_page(msg, "STELLA SYSTEM - DASHBOARD", show_intro=True, show_full_nav=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

