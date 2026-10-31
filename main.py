import os
import sqlite3
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import httpx
import random

app = FastAPI()

SECRET_PIN = "7777"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stella.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            name TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            city TEXT,
            district TEXT PRIMARY KEY,
            items INTEGER DEFAULT 0,
            usd REAL DEFAULT 0,
            ltc REAL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            city TEXT,
            district TEXT,
            name TEXT,
            price REAL,
            product_link TEXT,
            photo_link TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            avatar_url TEXT,
            balance_usd REAL DEFAULT 0.0,
            balance_ltc REAL DEFAULT 0.0,
            ltc_address TEXT DEFAULT '',
            is_verified INTEGER DEFAULT 0,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            price REAL,
            district TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('bot_name', 'Не привязан')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('bot_token', '')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('welcome_msg', 'Добро пожаловать в STELLA SYSTEM! Выберите нужный раздел:')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('onetime_msg', 'Оплата прошла успешно! Вот ваш товар:')")
    
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_name', 'Admin Stella')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_username', '@stella_admin')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_id', '777888999')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_avatar', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop')")
    
    conn.commit()
    conn.close()

init_db()

def get_config(key: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def set_config(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

async def fetch_user_avatar(token: str, user_id: int) -> str:
    default_avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop"
    try:
        async with httpx.AsyncClient() as client:
            photos_res = await client.get(f"https://api.telegram.org/bot{token}/getUserProfilePhotos", params={"user_id": user_id, "limit": 1})
            photos_data = photos_res.json()
            
            if photos_data.get("ok") and photos_data["result"]["total_count"] > 0:
                file_id = photos_data["result"]["photos"][0][-1]["file_id"]
                file_res = await client.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": file_id})
                file_data = file_res.json()
                
                if file_data.get("ok"):
                    file_path = file_data["result"]["file_path"]
                    return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as e:
        print(f"Avatar fetch error: {e}")
        
    return default_avatar

@app.post("/webhook")
async def telegram_webhook(request: Request):
    token = get_config("bot_token")
    if not token:
        return {"ok": True}
    
    api_url = f"https://api.telegram.org/bot{token}"

    try:
        data = await request.json()
        
        user = None
        chat_id = None
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user = msg["from"]
        elif "callback_query" in data:
            cq = data["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            user = cq["from"]

        if user and chat_id:
            user_id = user["id"]
            username = user.get("username", "нет")
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            avatar_url = await fetch_user_avatar(token, user_id)
            fake_ltc_wallet = f"LTC1Q{user_id}stella99sys..."

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, avatar_url, ltc_address) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    username=excluded.username, 
                    full_name=excluded.full_name, 
                    avatar_url=excluded.avatar_url,
                    ltc_address=COALESCE(NULLIF(ltc_address, ''), excluded.ltc_address)
            """, (user_id, f"@{username}" if username != "нет" else "нет", full_name, avatar_url, fake_ltc_wallet))
            conn.commit()

            if "message" in data:
                text = msg.get("text", "")
                if text == "/start":
                    cursor.execute("UPDATE users SET is_verified = 0 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    conn.close()

                    num1 = random.randint(1, 5)
                    num2 = random.randint(1, 5)
                    correct_sum = num1 + num2
                    options = [correct_sum, correct_sum + 1, abs(correct_sum - 1)]
                    random.shuffle(options)

                    keyboard = {
                        "inline_keyboard": [
                            [{"text": str(opt), "callback_data": f"captcha_{opt}"}] 
                            for opt in options
                        ]
                    }

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"🤖 <b>Проверка безопасности (Капча)</b>\n\nПодтверрите, что вы не робот. Решите пример:\n\n<b>{num1} + {num2} = ?</b>",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })
                    return {"ok": True}
                else:
                    conn.close()

            elif "callback_query" in data:
                cq = data["callback_query"]
                callback_data = cq["data"]
                query_id = cq["id"]

                async with httpx.AsyncClient(timeout=10.0) as client:
                    try:
                        await client.post(f"{api_url}/answerCallbackQuery", json={"callback_query_id": query_id})
                    except Exception:
                        pass

                    if callback_data.startswith("captcha_"):
                        cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (chat_id,))
                        conn.commit()
                        
                        welcome_msg = get_config("welcome_msg")
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🏙️ Открыть каталог", "callback_data": "open_catalog"}],
                                [{"text": "👤 Мой профиль", "callback_data": "user_profile"},
                                 {"text": "💰 Пополнить LTC", "callback_data": "top_up_ltc"}]
                            ]
                        }
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"✅ <b>Капча успешно пройдена!</b>\n\n{welcome_msg}",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })
                        conn.close()
                        return

                    cursor.execute("SELECT is_verified FROM users WHERE user_id = ?", (chat_id,))
                    v_row = cursor.fetchone()
                    if not v_row or v_row[0] == 0:
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "⚠️ Сначала отправьте /start для прохождения проверки."
                        })
                        conn.close()
                        return

                    if callback_data == "open_catalog":
                        cursor.execute("SELECT name FROM cities")
                        cities = [row[0] for row in cursor.fetchall()]
                        if not cities:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "В данный момент в боте нет доступных городов."
                            })
                            conn.close()
                            return
                        keyboard = {"inline_keyboard": [[{"text": f"🏙️ {city}", "callback_data": f"city_{city}"}]] for city in cities}
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "Выберите город для покупки:",
                            "reply_markup": keyboard
                        })

                    elif callback_data == "user_profile":
                        cursor.execute("SELECT balance_usd, balance_ltc, ltc_address FROM users WHERE user_id = ?", (chat_id,))
                        user_info = cursor.fetchone()
                        
                        cursor.execute("SELECT product_name, price, district, date FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 5", (chat_id,))
                        user_purchases = cursor.fetchall()

                        cursor.execute("SELECT COUNT(*), SUM(price) FROM purchases WHERE user_id = ?", (chat_id,))
                        stats = cursor.fetchone()
                        total_count = stats[0] or 0
                        total_spent = stats[1] or 0.0

                        profile_text = (
                            f"👤 <b>ВАШ ПРОФИЛЬ</b>\n\n"
                            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
                            f"💵 <b>Баланс USD:</b> ${user_info[0]:.2f}\n"
                            f"🪙 <b>Баланс LTC:</b> {user_info[1]:.4f} LTC\n\n"
                            f"📊 <b>ЦИФРЫ ПОКУПОК:</b>\n"
                            f"• Всего куплено: <b>{total_count} шт.</b>\n"
                            f"• Потрачено: <b>${total_spent:.2f}</b>\n\n"
                            f"📜 <b>Последние покупки:</b>\n"
                        )

                        if user_purchases:
                            for p in user_purchases:
                                profile_text += f"— {p[0]} (${p[1]}) | Район: {p[2]} | <i>{p[3]}</i>\n"
                        else:
                            profile_text += "<i>У вас пока нет покупок.</i>"

                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🔄 Обновить", "callback_data": "user_profile"},
                                 {"text": "🔙 Главное меню", "callback_data": "main_menu"}]
                            ]
                        }
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": profile_text,
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data == "top_up_ltc":
                        cursor.execute("SELECT ltc_address FROM users WHERE user_id = ?", (chat_id,))
                        row = cursor.fetchone()
                        ltc_addr = row[0] if row else "Адрес не найден"

                        topup_text = (
                            f"💰 <b>ПОПОЛНЕНИЕ БАЛАНСА LTC</b>\n\n"
                            f"Отправьте Litecoin (LTC) на ваш адрес:\n\n"
                            f"<code>{ltc_addr}</code>"
                        )
                        keyboard = {
                            "inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "user_profile"}]]
                        }
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": topup_text,
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data == "main_menu":
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🏙️ Открыть каталог", "callback_data": "open_catalog"}],
                                [{"text": "👤 Мой профиль", "callback_data": "user_profile"},
                                 {"text": "💰 Пополнить LTC", "callback_data": "top_up_ltc"}]
                            ]
                        }
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "🏠 Главное меню:",
                            "reply_markup": keyboard
                        })

                    elif callback_data.startswith("city_"):
                        selected_city = callback_data.replace("city_", "").strip()
                        cursor.execute("SELECT district FROM districts WHERE city = ?", (selected_city,))
                        districts = [row[0] for row in cursor.fetchall()]

                        if not districts:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"⚠️ В городе <b>{selected_city}</b> пока нет районов.",
                                "parse_mode": "HTML"
                            })
                            conn.close()
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📍 {d}", "callback_data": f"dist_{d}"}] for d in districts]}
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"Город: <b>{selected_city}</b>. Выберите район:",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data.startswith("dist_"):
                        selected_district = callback_data.replace("dist_", "").strip()
                        cursor.execute("SELECT name FROM categories")
                        categories = [row[0] for row in cursor.fetchall()]
                        
                        if not categories:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "⚠️ Категории не настроены."
                            })
                            conn.close()
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📂 {cat}", "callback_data": f"cat_{selected_district}_{cat}"}] for cat in categories]}
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"Район: <b>{selected_district}</b>. Выберите категорию:",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data.startswith("cat_"):
                        parts = callback_data.replace("cat_", "").split("_", 1)
                        if len(parts) < 2:
                            conn.close()
                            return
                        
                        selected_district = parts[0]
                        selected_cat = parts[1]

                        cursor.execute("SELECT name, price FROM products WHERE district = ? AND category = ?", (selected_district, selected_cat))
                        products = cursor.fetchall()

                        if not products:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"📦 В этой категории пока нет товаров.",
                                "parse_mode": "HTML"
                            })
                            conn.close()
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📦 {p[0]} — ${p[1]}", "callback_data": f"buy_{p[0]}"}] for p in products]}
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"Категория: <b>{selected_cat}</b>. Выберите товар:",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data.startswith("buy_"):
                        prod_name = callback_data.replace("buy_", "").strip()
                        cursor.execute("SELECT name, price, product_link, photo_link, district FROM products WHERE name = ?", (prod_name,))
                        product = cursor.fetchone()

                        if product:
                            cursor.execute("INSERT INTO purchases (user_id, product_name, price, district) VALUES (?, ?, ?, ?)", 
                                           (chat_id, product[0], product[1], product[4]))
                            cursor.execute("UPDATE districts SET items = items + 1 WHERE district = ?", (product[4],))
                            conn.commit()

                            onetime_msg = get_config("onetime_msg")
                            delivery_text = f"{onetime_msg}\n\n<b>{product[0]}</b>\nЦена: ${product[1]}\n"
                            if product[2]:
                                delivery_text += f"🔗 Ссылка: {product[2]}"

                            if product[3]:
                                await client.post(f"{api_url}/sendPhoto", json={
                                    "chat_id": chat_id,
                                    "photo": product[3],
                                    "caption": delivery_text,
                                    "parse_mode": "HTML"
                                })
                            else:
                                await client.post(f"{api_url}/sendMessage", json={
                                    "chat_id": chat_id,
                                    "text": delivery_text,
                                    "parse_mode": "HTML"
                                })
                    conn.close()

    except Exception as e:
        print(f"Webhook error: {e}")
        
    return {"ok": True}

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITLE__</title>
    <style>
        :root { --bg-color: #070a13; --card-bg: rgba(15, 23, 42, 0.85); --border-color: rgba(56, 189, 248, 0.3); --text-color: #f8fafc; --input-bg: rgba(15, 23, 42, 0.8); --input-border: rgba(100, 116, 139, 0.3); }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; background: var(--bg-color); color: var(--text-color); display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .header-container { width: 100%; max-width: 420px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .header-title h1 { font-size: 16px; color: #38bdf8; }
        .menu-btn, .theme-toggle { background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color); padding: 8px 10px; border-radius: 8px; cursor: pointer; }
        .sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: var(--card-bg); border-right: 1px solid var(--border-color); z-index: 1000; padding: 24px; transition: left 0.3s ease; }
        .sidebar.open { left: 0; }
        .sidebar-menu a { display: block; color: var(--text-color); text-decoration: none; padding: 10px 0; border-bottom: 1px solid var(--input-border); }
        .card { background: var(--card-bg); border: 1px solid var(--border-color); padding: 20px; border-radius: 20px; width: 100%; max-width: 420px; }
        input, select, textarea { width: 100%; padding: 13px; margin-bottom: 12px; border-radius: 10px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-color); }
        button[type="submit"] { width: 100%; padding: 13px; border-radius: 10px; border: none; background: #0284c7; color: #fff; font-weight: 600; cursor: pointer; }
        .logout { background: rgba(239, 68, 68, 0.15); margin-top: 12px; text-align: center; display: block; text-decoration: none; padding: 11px; border-radius: 10px; color: #fca5a5; }
    </style>
</head>
<body>
    __HEADER__
    __SIDEBAR__
    <div class="card">__CONTENT__</div>
    <script>function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }</script>
</body>
</html>"""

def get_page(content: str, title: str = "STELLA", show_full_nav: bool = False) -> str:
    header_html = '<div class="header-container"><button class="menu-btn" onclick="toggleSidebar()">☰</button><h1>STELLA</h1></div>' if show_full_nav else '<div class="header-container" style="justify-content:center;"><h1>STELLA ACCESS</h1></div>'
    sidebar_html = f'''
    <div id="sidebar" class="sidebar">
        <div>
            <h3>Управление</h3>
            <button onclick="toggleSidebar()">✕</button>
            <div class="sidebar-menu">
                <a href="/dashboard">📊 Дашборд</a>
                <a href="/bot-settings">🤖 Настройки бота</a>
                <a href="/clients">👥 Клиентская база</a>
                <a href="/cities">🏙️ Города</a>
                <a href="/districts">📍 Районы</a>
                <a href="/categories">📂 Категории</a>
                <a href="/products">📦 Товары</a>
                <a href="/" style="color: #fca5a5;">🚪 Выход</a>
            </div>
        </div>
    </div>''' if show_full_nav else ""
    return BASE_TEMPLATE.replace("__TITLE__", title).replace("__CONTENT__", content).replace("__HEADER__", header_html).replace("__SIDEBAR__", sidebar_html)

@app.get("/", response_class=HTMLResponse)
async def index():
    return get_page('<form method="POST" action="/verify-pin"><input type="password" name="pin_code" placeholder="Введите ПИН (7777)" required><button type="submit">Войти</button></form>')

@app.post("/verify-pin", response_class=HTMLResponse)
async def verify_pin(pin_code: str = Form(...)):
    if pin_code != SECRET_PIN:
        return RedirectResponse(url="/", status_code=303)
    return await dashboard_get()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_get():
    return get_page(f'<h2>Дашборд</h2><p style="color:#4ade80;">🤖 Бот: {get_config("bot_name")}</p><a href="/clients" class="logout" style="background:#0284c7;color:#fff;">👥 Клиенты</a><a href="/products" class="logout" style="background:#0284c7;color:#fff;">📦 Товары</a><a href="/" class="logout">Выйти</a>', show_full_nav=True)

@app.get("/clients", response_class=HTMLResponse)
async def clients_page():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, first_seen FROM users ORDER BY first_seen DESC")
    users = cursor.fetchall()
    conn.close()
    list_html = "".join([f'<div><b>{u[2]}</b> ({u[1]}) | ID: {u[0]}</div>' for u in users]) or 'Нет клиентов'
    return get_page(f'<h2>Клиенты ({len(users)})</h2><div>{list_html}</div><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.get("/bot-settings", response_class=HTMLResponse)
async def bot_settings_page():
    return get_page(f'<h2>Настройки бота</h2><form method="POST" action="/update-bot"><input type="text" name="bot_name" placeholder="Имя (@Bot)" required><input type="text" name="bot_token" placeholder="Токен BotFather" required><button type="submit">Сохранить</button></form><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.post("/update-bot", response_class=HTMLResponse)
async def update_bot(request: Request, bot_name: str = Form(...), bot_token: str = Form(...)):
    set_config("bot_name", bot_name)
    set_config("bot_token", bot_token)
    host_url = str(request.base_url).rstrip('/')
    async with httpx.AsyncClient() as client:
        await client.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={host_url}/webhook")
    return RedirectResponse(url="/bot-settings", status_code=303)

@app.get("/cities", response_class=HTMLResponse)
async def cities_page():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cities")
    cities = [r[0] for r in cursor.fetchall()]
    conn.close()
    list_html = "".join([f'<div>🏙️ {c}</div>' for c in cities]) or 'Нет городов'
    return get_page(f'<h2>Города</h2><form method="POST" action="/add-city"><input type="text" name="city_name" placeholder="Город" required><button type="submit">Добавить</button></form><div>{list_html}</div><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.post("/add-city", response_class=HTMLResponse)
async def add_city(city_name: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city_name.strip(),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/cities", status_code=303)

@app.get("/districts", response_class=HTMLResponse)
async def districts_page():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cities")
    cities = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT city, district FROM districts")
    districts = cursor.fetchall()
    conn.close()
    opts = "".join([f'<option value="{c}">{c}</option>' for c in cities])
    list_html = "".join([f'<div>📍 {d[1]} ({d[0]})</div>' for d in districts]) or 'Нет районов'
    return get_page(f'<h2>Районы</h2><form method="POST" action="/add-district"><select name="city" required><option value="" disabled selected>Город</option>{opts}</select><input type="text" name="district_name" placeholder="Район" required><button type="submit">Добавить</button></form><div>{list_html}</div><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.post("/add-district", response_class=HTMLResponse)
async def add_district(city: str = Form(...), district_name: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO districts (city, district) VALUES (?, ?)", (city.strip(), district_name.strip()))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/districts", status_code=303)

@app.get("/categories", response_class=HTMLResponse)
async def categories_page():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    cats = [r[0] for r in cursor.fetchall()]
    conn.close()
    list_html = "".join([f'<div>📂 {c}</div>' for c in cats]) or 'Нет категорий'
    return get_page(f'<h2>Категории</h2><form method="POST" action="/add-category"><input type="text" name="category_name" placeholder="Категория" required><button type="submit">Добавить</button></form><div>{list_html}</div><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.post("/add-category", response_class=HTMLResponse)
async def add_category(category_name: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category_name.strip(),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/products", response_class=HTMLResponse)
async def products_page():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    cats = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT name FROM cities")
    cities = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT district, city FROM districts")
    districts = cursor.fetchall()
    cursor.execute("SELECT name, price, district FROM products")
    products = cursor.fetchall()
    conn.close()

    c_opts = "".join([f'<option value="{c}">{c}</option>' for c in cats])
    ci_opts = "".join([f'<option value="{c}">{c}</option>' for c in cities])
    d_opts = "".join([f'<option value="{d[0]}">{d[0]} ({d[1]})</option>' for d in districts])
    list_html = "".join([f'<div>📦 {p[0]} - ${p[1]} ({p[2]})</div>' for p in products]) or 'Нет товаров'

    return get_page(f'<h2>Товары</h2><form method="POST" action="/add-product"><select name="category" required><option value="" disabled selected>Категория</option>{c_opts}</select><select name="city" required><option value="" disabled selected>Город</option>{ci_opts}</select><select name="district" required><option value="" disabled selected>Район</option>{d_opts}</select><input type="text" name="product_name" placeholder="Название" required><input type="number" step="0.01" name="price" placeholder="Цена ($)" required><input type="url" name="product_link" placeholder="Ссылка"><button type="submit">Добавить</button></form><div>{list_html}</div><a href="/dashboard" class="logout" style="background:#0284c7;color:#fff;">Назад</a>', show_full_nav=True)

@app.post("/add-product", response_class=HTMLResponse)
async def add_product(category: str = Form(...), city: str = Form(...), district: str = Form(...), product_name: str = Form(...), price: float = Form(...), product_link: str = Form("")):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (category, city, district, name, price, product_link) VALUES (?, ?, ?, ?, ?, ?)", 
                   (category.strip(), city.strip(), district.strip(), product_name.strip(), price, product_link.strip()))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/products", status_code=303)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
