import os
import asyncio
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

app = FastAPI()

SECRET_PIN = "7777"

# Базы данных
CITIES_DB = []
DISTRICTS_DB = []
CATEGORIES_DB = []
PRODUCTS_DB = []
BOT_CONFIG = {"name": "Не привязан", "token": ""}

# Тексты сообщений бота, редактируемые в панели
BOT_MESSAGES = {
    "welcome": "Добро пожаловать в STELLA SYSTEM! Выберите город и район для покупки.",
    "onetime": "Оплата прошла успешно! Вот ваш товар:"
}

# Инициализация Telegram бота (будет обновляться при сохранении токена)
bot_instance = None
dp = Dispatcher()

def update_telegram_bot():
    global bot_instance
    if BOT_CONFIG["token"]:
        bot_instance = Bot(token=BOT_CONFIG["token"], default=DefaultBotProperties(parse_mode=ParseMode.HTML))

@dp.message(lambda message: message.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(BOT_MESSAGES["welcome"])

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITLE__</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #070a13;
            --bg-gradient: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            --card-bg: rgba(15, 23, 42, 0.85);
            --border-color: rgba(56, 189, 248, 0.3);
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --input-bg: rgba(15, 23, 42, 0.8);
            --input-border: rgba(100, 116, 139, 0.3);
        }
        [data-theme="light"] {
            --bg-color: #f1f5f9;
            --bg-gradient: radial-gradient(circle at 50% 30%, #e2e8f0 0%, #cbd5e1 100%);
            --card-bg: rgba(255, 255, 255, 0.9);
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
            top: 0; left: 0; width: 100%; height: 100%;
            background: #070a13;
            background-image: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            z-index: 9999;
            transition: opacity 0.8s ease, visibility 0.8s ease;
        }
        .intro-content {
            text-align: center;
            animation: riseUpAndFade 3s cubic-bezier(0.77, 0, 0.175, 1) forwards;
        }
        .intro-title {
            font-size: 34px; font-weight: 700; letter-spacing: 12px; color: #ffffff;
            text-shadow: 0 0 25px rgba(56, 189, 248, 0.8); margin-bottom: 8px;
        }
        .intro-line {
            width: 60px; height: 2px; background: #38bdf8; margin: 0 auto;
            box-shadow: 0 0 12px #38bdf8;
        }

        @keyframes riseUpAndFade {
            0% { transform: translateY(0); opacity: 1; }
            75% { transform: translateY(0); opacity: 1; }
            100% { transform: translateY(-40px); opacity: 0; visibility: hidden; }
        }

        .header-container {
            width: 100%; max-width: 420px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
        }
        .header-title h1 { font-size: 16px; letter-spacing: 3px; font-weight: 600; color: #38bdf8; }
        .header-title p { font-size: 10px; letter-spacing: 2px; color: var(--text-muted); }
        
        .menu-btn {
            background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color);
            padding: 8px 10px; border-radius: 8px; cursor: pointer; font-size: 16px;
            display: flex; align-items: center; justify-content: center;
        }

        .sidebar {
            position: fixed; top: 0; left: -280px; width: 280px; height: 100%;
            background: var(--card-bg); backdrop-filter: blur(20px);
            border-right: 1px solid var(--border-color); z-index: 1000; padding: 24px;
            transition: left 0.3s ease;
        }
        .sidebar.open { left: 0; }
        .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .sidebar-menu a {
            display: block; color: var(--text-color); text-decoration: none; padding: 12px 0;
            border-bottom: 1px solid var(--input-border); font-size: 14px; font-weight: 500;
        }
        .sidebar-menu a:hover { color: #38bdf8; }

        .theme-toggle {
            background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color);
            padding: 6px 10px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600;
        }

        .card { 
            background: var(--card-bg); backdrop-filter: blur(16px); border: 1px solid var(--border-color);
            padding: 20px; border-radius: 20px; width: 100%; max-width: 420px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15); 
        }
        .banner-img {
            width: 100%; height: 160px; object-fit: cover; border-radius: 12px; margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1); display: block;
        }
        input, select, textarea { 
            width: 100%; padding: 13px; margin-bottom: 12px; border-radius: 10px; 
            border: 1px solid var(--input-border); background: var(--input-bg); 
            color: var(--text-color); font-size: 14px; outline: none; resize: vertical;
        }
        input:focus, select:focus, textarea:focus { border-color: #38bdf8; box-shadow: 0 0 10px rgba(56, 189, 248, 0.25); }
        button[type="submit"] { 
            width: 100%; padding: 13px; margin-top: 4px; border-radius: 10px; border: none;
            background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff;
            font-size: 15px; font-weight: 600; cursor: pointer; 
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }
        .logout { 
            background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3);
            margin-top: 12px; text-align: center; display: block; text-decoration: none; 
            padding: 11px; border-radius: 10px; color: #fca5a5; font-weight: 600; font-size: 14px;
        }

        #status-popup {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 19, 0.7); z-index: 3000; justify-content: center; align-items: center;
        }
        .popup-box {
            background: #ffffff; color: #0f172a; padding: 30px; border-radius: 20px;
            text-align: center; width: 260px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        @keyframes popIn {
            0% { transform: scale(0.7); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        .popup-icon { font-size: 48px; margin-bottom: 10px; }
        .popup-text { font-size: 16px; font-weight: 600; color: #0f172a; }
    </style>
</head>
<body data-theme="dark">
    __INTRO__
    __HEADER__
    __SIDEBAR__
    
    <div class="card">
        __CONTENT__
    </div>

    <div id="status-popup">
        <div class="popup-box">
            <div id="popup-icon" class="popup-icon"></div>
            <div id="popup-text" class="popup-text"></div>
        </div>
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

        function showPopup(success, message) {
            const popup = document.getElementById('status-popup');
            const icon = document.getElementById('popup-icon');
            const text = document.getElementById('popup-text');
            
            icon.innerHTML = success ? '✅' : '❌';
            text.innerText = message;
            popup.style.display = 'flex';

            setTimeout(() => {
                popup.style.display = 'none';
            }, 1800);
        }

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
                <p>CONTROL SYSTEM</p>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">🌓</button>
        </div>
        """
        sidebar_html = """
        <div id="sidebar" class="sidebar">
            <div class="sidebar-header">
                <h3>Управление</h3>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <div class="sidebar-menu">
                <a href="/dashboard">📊 Статистика и Графика</a>
                <a href="/bot-settings">🤖 Настройки бота</a>
                <a href="/bot-messages">💬 Сообщения бота</a>
                <a href="/cities">🏙️ Управление городами</a>
                <a href="/districts">📍 Управление районами</a>
                <a href="/categories">📂 Категории</a>
                <a href="/products">📦 Товары и выдача</a>
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

@app.post("/verify-pin", response_class=HTMLResponse)
async def verify_pin_page(username: str = Form(...), password: str = Form(...)):
    content = """
        <div style="text-align:center; margin-bottom: 16px;">
            <p style="color: #38bdf8; font-size: 13px; font-weight: 600;">🔐 Безопасность STELLA</p>
            <h3 style="margin-top:6px; font-size:16px;">Введите 4-значный ПИН-код</h3>
        </div>
        <form method="POST" action="/check-pin">
            <input type="password" name="pin_code" placeholder="• • • •" maxlength="4" inputmode="numeric" style="text-align:center; font-size: 20px; letter-spacing: 8px;" required>
            <button type="submit">Подтвердить</button>
        </form>
        <a href="/" class="logout">Отмена</a>
    """
    return get_page(content, "STELLA SYSTEM - PIN", show_intro=False, show_full_nav=False)

@app.post("/check-pin", response_class=HTMLResponse)
async def check_pin(pin_code: str = Form(...)):
    if pin_code != SECRET_PIN:
        return RedirectResponse(url="/", status_code=303)
    return await render_main_dashboard(intro=True)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_get():
    return await render_main_dashboard(intro=False)

@app.get("/bot-settings", response_class=HTMLResponse)
async def bot_settings_page(status: str = None):
    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Ошибка'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">ИНТЕГРАЦИЯ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Управление ботом</h2>
        </div>

        <div style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 14px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">ТЕКУЩИЙ СТАТУС:</p>
            <h3 style="font-size: 14px; color: #4ade80; margin-bottom: 10px;">🤖 {BOT_CONFIG['name']}</h3>
        </div>

        <form method="POST" action="/update-bot" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600;">⚙️ ПРИВЯЗАТЬ НОВОГО БОТА:</p>
            <input type="text" name="bot_name" placeholder="Имя бота (например, @MyBot)" required style="margin-bottom: 8px;">
            <input type="text" name="bot_token" placeholder="Токен от BotFather" required style="margin-bottom: 8px;">
            <button type="submit">Сохранить и запустить</button>
        </form>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - BOT SETTINGS", show_intro=False, show_full_nav=True)

@app.post("/update-bot", response_class=HTMLResponse)
async def update_bot(bot_name: str = Form(...), bot_token: str = Form(...)):
    if bot_name and bot_token:
        BOT_CONFIG["name"] = bot_name
        BOT_CONFIG["token"] = bot_token
        update_telegram_bot()
        return RedirectResponse(url="/bot-settings?status=success", status_code=303)
    return RedirectResponse(url="/bot-settings?status=error", status_code=303)

@app.get("/bot-messages", response_class=HTMLResponse)
async def bot_messages_page(status: str = None):
    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Ошибка'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">КОНТЕНТ БОТА</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Настройка текстов</h2>
        </div>

        <form method="POST" action="/update-bot-messages" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">👋 ПРИВЕТСТВИЕ (/start):</p>
            <textarea name="welcome_msg" rows="3" required style="margin-bottom: 10px;">{BOT_MESSAGES['welcome']}</textarea>
            
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">⚡ ОДНОРАЗОВОЕ СООБЩЕНИЕ (ПОСЛЕ ОПЛАТЫ):</p>
            <textarea name="onetime_msg" rows="3" required style="margin-bottom: 10px;">{BOT_MESSAGES['onetime']}</textarea>

            <button type="submit">Сохранить сообщения</button>
        </form>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - BOT MESSAGES", show_intro=False, show_full_nav=True)

@app.post("/update-bot-messages", response_class=HTMLResponse)
async def update_bot_messages(welcome_msg: str = Form(...), onetime_msg: str = Form(...)):
    if welcome_msg and onetime_msg:
        BOT_MESSAGES["welcome"] = welcome_msg
        BOT_MESSAGES["onetime"] = onetime_msg
        return RedirectResponse(url="/bot-messages?status=success", status_code=303)
    return RedirectResponse(url="/bot-messages?status=error", status_code=303)

@app.get("/cities", response_class=HTMLResponse)
async def cities_page(status: str = None):
    list_html = "".join([f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: var(--input-bg); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--input-border);">
            <span style="font-size: 13px; font-weight: 600;">🏙️ {c}</span>
        </div>
    """ for c in CITIES_DB]) if CITIES_DB else '<p style="font-size: 11px; color: var(--text-muted); text-align: center;">Города еще не добавлены</p>'

    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Ошибка'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">БАЗА ДАННЫХ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Управление городами</h2>
        </div>

        <form method="POST" action="/add-city" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600;">➕ ДОБАВИТЬ ГОРОД:</p>
            <input type="text" name="city_name" placeholder="Название города" required style="margin-bottom: 8px;">
            <button type="submit">Сохранить город</button>
        </form>

        <div style="margin-bottom: 14px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">СПИСОК ГОРОДОВ:</p>
            <div style="max-height: 160px; overflow-y: auto;">
                {list_html}
            </div>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - CITIES", show_intro=False, show_full_nav=True)

@app.post("/add-city", response_class=HTMLResponse)
async def add_city(city_name: str = Form(...)):
    if city_name and city_name not in CITIES_DB:
        CITIES_DB.append(city_name)
        return RedirectResponse(url="/cities?status=success", status_code=303)
    return RedirectResponse(url="/cities?status=error", status_code=303)

@app.get("/districts", response_class=HTMLResponse)
async def districts_page(status: str = None):
    city_options = "".join([f'<option value="{c}">{c}</option>' for c in CITIES_DB])
    
    list_html = "".join([f"""
        <div style="background: var(--input-bg); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--input-border);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600;">{d['district']}</span>
                <span style="font-size: 11px; color: var(--text-muted);">Город: {d['city']}</span>
            </div>
        </div>
    """ for d in DISTRICTS_DB]) if DISTRICTS_DB else '<p style="font-size: 11px; color: var(--text-muted); text-align: center;">Районы еще не добавлены</p>'

    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Ошибка'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">БАЗА ДАННЫХ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Управление районами</h2>
        </div>

        <form method="POST" action="/add-district" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600;">➕ ДОБАВИТЬ РАЙОН:</p>
            <select name="city" required style="margin-bottom: 8px;">
                <option value="" disabled selected>Выберите город</option>
                {city_options}
            </select>
            <input type="text" name="district_name" placeholder="Название района" required style="margin-bottom: 8px;">
            <button type="submit">Сохранить район</button>
        </form>

        <div style="margin-bottom: 14px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">СПИСОК РАЙОНОВ:</p>
            <div style="max-height: 160px; overflow-y: auto;">
                {list_html}
            </div>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - DISTRICTS", show_intro=False, show_full_nav=True)

@app.post("/add-district", response_class=HTMLResponse)
async def add_district(city: str = Form(...), district_name: str = Form(...)):
    if city and district_name:
        DISTRICTS_DB.append({"city": city, "district": district_name, "items": 0, "usd": 0, "ltc": 0})
        return RedirectResponse(url="/districts?status=success", status_code=303)
    return RedirectResponse(url="/districts?status=error", status_code=303)

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(status: str = None):
    list_html = "".join([f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: var(--input-bg); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--input-border);">
            <span style="font-size: 13px; font-weight: 600;">📂 {cat}</span>
        </div>
    """ for cat in CATEGORIES_DB]) if CATEGORIES_DB else '<p style="font-size: 11px; color: var(--text-muted); text-align: center;">Категории не добавлены</p>'

    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Ошибка'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">КАТАЛОГ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Управление категориями</h2>
        </div>

        <form method="POST" action="/add-category" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600;">➕ ДОБАВИТЬ КАТЕГОРИЮ:</p>
            <input type="text" name="category_name" placeholder="Название категории" required style="margin-bottom: 8px;">
            <button type="submit">Сохранить категорию</button>
        </form>

        <div style="margin-bottom: 14px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">СПИСОК КАТЕГОРИЙ:</p>
            <div style="max-height: 160px; overflow-y: auto;">
                {list_html}
            </div>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - CATEGORIES", show_intro=False, show_full_nav=True)

@app.post("/add-category", response_class=HTMLResponse)
async def add_category(category_name: str = Form(...)):
    if category_name and category_name not in CATEGORIES_DB:
        CATEGORIES_DB.append(category_name)
        return RedirectResponse(url="/categories?status=success", status_code=303)
    return RedirectResponse(url="/categories?status=error", status_code=303)

@app.get("/products", response_class=HTMLResponse)
async def products_page(status: str = None):
    cat_options = "".join([f'<option value="{c}">{c}</option>' for c in CATEGORIES_DB])
    city_options = "".join([f'<option value="{c}">{c}</option>' for c in CITIES_DB])
    district_options = "".join([f'<option value="{d["district"]}">{d["district"]} ({d["city"]})</option>' for d in DISTRICTS_DB])

    list_html = "".join([f"""
        <div style="background: var(--input-bg); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--input-border);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600;">📦 {p['name']}</span>
                <span style="font-size: 11px; color: #38bdf8;">${p['price']}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Район: {p['district']} ({p['city']})</div>
            {"<div style='font-size: 11px; color: #4ade80; word-break: break-all;'>🔗 Ссылка: <a href='" + p['product_link'] + "' target='_blank' style='color: #4ade80;'>Перейти</a></div>" if p['product_link'] else ""}
            {"<div style='font-size: 11px; color: #38bdf8; word-break: break-all;'>🖼️ Фото: <a href='" + p['photo_link'] + "' target='_blank' style='color: #38bdf8;'>Смотреть</a></div>" if p['photo_link'] else ""}
        </div>
    """ for p in PRODUCTS_DB]) if PRODUCTS_DB else '<p style="font-size: 11px; color: var(--text-muted); text-align: center;">Товары еще не добавлены</p>'

    popup_script = ""
    if status == "success":
        popup_script = "<script>window.addEventListener('load', () => showPopup(true, 'Изменено'));</script>"
    elif status == "error":
        popup_script = "<script>window.addEventListener('load', () => showPopup(false, 'Укажите ссылку или фото'));</script>"

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">КАТАЛОГ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Товары и выдача</h2>
        </div>

        <form method="POST" action="/add-product" style="background: var(--input-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600;">➕ ДОБАВИТЬ ТОВАР:</p>
            <select name="category" required style="margin-bottom: 8px;">
                <option value="" disabled selected>Выберите категорию</option>
                {cat_options}
            </select>
            <select name="city" required style="margin-bottom: 8px;">
                <option value="" disabled selected>Выберите город</option>
                {city_options}
            </select>
            <select name="district" required style="margin-bottom: 8px;">
                <option value="" disabled selected>Выберите район</option>
                {district_options}
            </select>
            <input type="text" name="product_name" placeholder="Название товара" required style="margin-bottom: 8px;">
            <input type="number" step="0.01" name="price" placeholder="Цена ($)" required style="margin-bottom: 8px;">
            <input type="url" name="product_link" placeholder="Ссылка выдачи после оплаты (необязательно)" style="margin-bottom: 8px;">
            <input type="url" name="photo_link" placeholder="Ссылка на фото товара (необязательно)" style="margin-bottom: 8px;">
            <button type="submit">Сохранить товар</button>
        </form>

        <div style="margin-bottom: 14px;">
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">СПИСОК ТОВАРОВ:</p>
            <div style="max-height: 180px; overflow-y: auto;">
                {list_html}
            </div>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
        {popup_script}
    """
    return get_page(content, "STELLA SYSTEM - PRODUCTS", show_intro=False, show_full_nav=True)

@app.post("/add-product", response_class=HTMLResponse)
async def add_product(category: str = Form(...), city: str = Form(...), district: str = Form(...), product_name: str = Form(...), price: float = Form(...), product_link: str = Form(""), photo_link: str = Form("")):
    if category and city and district and product_name and (product_link or photo_link):
        PRODUCTS_DB.append({
            "category": category,
            "city": city,
            "district": district,
            "name": product_name,
            "price": price,
            "product_link": product_link,
            "photo_link": photo_link
        })
        return RedirectResponse(url="/products?status=success", status_code=303)
    return RedirectResponse(url="/products?status=error", status_code=303)

async def render_main_dashboard(intro: bool = True):
    labels = [d['district'] for d in DISTRICTS_DB] if DISTRICTS_DB else ["Нет районов"]
    items_data = [d['items'] for d in DISTRICTS_DB] if DISTRICTS_DB else [0]

    dashboard_content = """
        <div style="text-align:center; margin-bottom: 12px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">АНАЛИТИКА СИСТЕМЫ</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Доходы и Районы</h2>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 11px; color: var(--text-muted);">Активный бот:</span>
                <span style="font-size: 12px; color: #4ade80; font-weight: 600;">🤖 __BOT_NAME__</span>
            </div>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin-bottom: 14px;">
            <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 6px;">
                <span style="font-size: 11px; color: var(--text-muted);">Доход по месяцам (USD / LTC):</span>
                <span id="selected-month" style="font-size: 11px; color: #38bdf8; font-weight: 600;">Все</span>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                <div style="flex: 1; background: rgba(56, 189, 248, 0.08); padding: 6px; border-radius: 8px; text-align: center;">
                    <span style="font-size: 9px; color: var(--text-muted);">БАЛАНС USD:</span>
                    <div id="stat-usd" style="font-size: 13px; color: #38bdf8; font-weight: 600;">$0.00</div>
                </div>
                <div style="flex: 1; background: rgba(74, 222, 128, 0.08); padding: 6px; border-radius: 8px; text-align: center;">
                    <span style="font-size: 9px; color: var(--text-muted);">БАЛАНС LTC:</span>
                    <div id="stat-ltc" style="font-size: 13px; color: #4ade80; font-weight: 600;">0.00 LTC</div>
                </div>
            </div>
            <canvas id="incomeChart" style="max-height: 120px;"></canvas>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin-bottom: 14px;">
            <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 6px;">
                <span style="font-size: 11px; color: var(--text-muted);">Районы (товаров куплено):</span>
                <a href="/products" style="font-size: 10px; color: #38bdf8; text-decoration: none; font-weight: 600;">⚙️ Товары</a>
            </div>
            <div style="background: rgba(15, 23, 42, 0.5); padding: 6px; border-radius: 8px; text-align: center; margin-bottom: 8px;">
                <span style="font-size: 9px; color: var(--text-muted);" id="label-district">ВЫБРАННЫЙ РАЙОН: ВСЕ</span>
                <div id="stat-items" style="font-size: 13px; color: #38bdf8; font-weight: 600;">0 товаров</div>
            </div>
            <canvas id="districtChart" style="max-height: 130px;"></canvas>
        </div>

        <a href='/' class='logout' style='margin-top: 8px; text-decoration: none;'>Выйти</a>

        <script>
            const monthlyData = [
                { month: 'Янв', usd: 0, ltc: 0 },
                { month: 'Фев', usd: 0, ltc: 0 },
                { month: 'Мар', usd: 0, ltc: 0 },
                { month: 'Апр', usd: 0, ltc: 0 },
                { month: 'Май', usd: 0, ltc: 0 },
                { month: 'Июн', usd: 0, ltc: 0 }
            ];

            const ctxIncome = document.getElementById('incomeChart').getContext('2d');
            new Chart(ctxIncome, {
                type: 'line',
                data: {
                    labels: monthlyData.map(d => d.month),
                    datasets: [{
                        data: monthlyData.map(d => d.usd),
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        borderWidth: 2,
                        pointBackgroundColor: '#ffffff',
                        pointRadius: 4,
                        fill: true,
                        tension: 0.35
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 9 } } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } } }
                    }
                }
            });

            const districtsLabels = __DISTRICTS_LABELS__;
            const districtsItems = __DISTRICTS_ITEMS__;

            const ctxDistrict = document.getElementById('districtChart').getContext('2d');
            new Chart(ctxDistrict, {
                type: 'bar',
                data: {
                    labels: districtsLabels,
                    datasets: [{
                        data: districtsItems,
                        backgroundColor: 'rgba(56, 189, 248, 0.6)',
                        borderColor: '#38bdf8',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 9 } } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } } }
                    }
                }
            });
        </script>
    """
    
    import json
    labels_json = json.dumps(labels, ensure_ascii=False)
    items_json = json.dumps(items_data, ensure_ascii=False)
    
    final_content = dashboard_content.replace("__BOT_NAME__", BOT_CONFIG["name"]).replace("__DISTRICTS_LABELS__", labels_json).replace("__DISTRICTS_ITEMS__", items_json)
    return get_page(final_content, "STELLA SYSTEM - DASHBOARD", show_intro=intro, show_full_nav=True)

# Автозапуск бота в фоновом режиме вместе с FastAPI
@app.on_event("startup")
async def on_startup():
    async def start_bot():
        while True:
            if bot_instance:
                try:
                    await dp.start_polling(bot_instance)
                except Exception:
                    await asyncio.sleep(5)
            else:
                await asyncio.sleep(3)
    
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
