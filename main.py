import os
import sqlite3
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import httpx
import random
import json
from datetime import datetime

app = FastAPI()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stella.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cities (name TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS districts (city TEXT, district TEXT PRIMARY KEY, items INTEGER DEFAULT 0, usd REAL DEFAULT 0, ltc REAL DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY)")
    
    # Таблица товаров с добавлением веса (weight) и времени создания (created_at)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category TEXT, 
            city TEXT, 
            district TEXT, 
            name TEXT, 
            weight TEXT,
            price REAL, 
            stock INTEGER DEFAULT 1,
            product_link TEXT, 
            photo_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            username TEXT,
            full_name TEXT,
            product_name TEXT,
            weight TEXT,
            price REAL,
            district TEXT,
            created_at TEXT,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_login', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_password', 'stella777')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('admin_pin', '7777')")

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
                    return f"https://api.telegram.org/file/bot{token}/{file_data['result']['file_path']}"
    except Exception as e:
        print(f"Avatar error: {e}")
    return default_avatar

@app.post("/webhook")
async def telegram_webhook(request: Request):
    token = get_config("bot_token")
    if not token:
        return {"ok": True}
    
    api_url = f"https://api.telegram.org/bot{token}"

    try:
        data = await request.json()
        user, chat_id = None, None
        
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

                    num1, num2 = random.randint(1, 5), random.randint(1, 5)
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
                callback_data = cq.get("data", "")
                query_id = cq["id"]
                message_id = cq["message"]["message_id"]

                async with httpx.AsyncClient(timeout=10.0) as client:
                    try:
                        await client.post(f"{api_url}/answerCallbackQuery", json={"callback_query_id": query_id})
                    except Exception:
                        pass

                    if callback_data.startswith("captcha_"):
                        cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
                        conn.commit()
                        conn.close()
                        
                        welcome_msg = get_config("welcome_msg")
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🏙️ Открыть каталог", "callback_data": "open_catalog"}],
                                [{"text": "👤 Мой профиль", "callback_data": "user_profile"},
                                 {"text": "💰 Пополнить LTC", "callback_data": "top_up_ltc"}]
                            ]
                        }
                        try:
                            await client.post(f"{api_url}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                        except Exception:
                            pass

                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"✅ <b>Проверка успешно пройдена!</b>\n\n{welcome_msg}",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })
                        return

                    cursor.execute("SELECT is_verified FROM users WHERE user_id = ?", (chat_id,))
                    v_row = cursor.fetchone()
                    
                    if not v_row or v_row[0] == 0:
                        conn.close()
                        return

                    if callback_data == "open_catalog":
                        cursor.execute("SELECT name FROM cities")
                        cities = [row[0] for row in cursor.fetchall()]
                        conn.close()
                        if not cities:
                            await client.post(f"{api_url}/editMessageText", json={
                                "chat_id": chat_id, "message_id": message_id,
                                "text": "В данный момент в боте нет доступных городов.",
                                "reply_markup": {"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "main_menu"}]]}
                            })
                            return
                        keyboard = {"inline_keyboard": [[{"text": f"🏙️ {city}", "callback_data": f"city_{city}"}]] for city in cities}
                        keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "main_menu"}])
                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": "🏙️ <b>Выберите город для покупки:</b>",
                            "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data == "user_profile":
                        cursor.execute("SELECT balance_usd, balance_ltc, ltc_address FROM users WHERE user_id = ?", (chat_id,))
                        user_info = cursor.fetchone()
                        
                        cursor.execute("SELECT COUNT(*), SUM(price) FROM purchases WHERE user_id = ?", (chat_id,))
                        stats = cursor.fetchone()
                        conn.close()
                        
                        total_count = stats[0] or 0
                        total_spent = stats[1] or 0.0

                        profile_text = (
                            f"👤 <b>ВАШ ПРОФИЛЬ</b>\n\n"
                            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
                            f"💵 <b>Баланс USD:</b> ${user_info[0]:.2f}\n"
                            f"🪙 <b>Баланс LTC:</b> {user_info[1]:.4f} LTC\n\n"
                            f"📊 <b>КУПЛЕНО ТОВАРОВ:</b> {total_count} шт. (на ${total_spent:.2f})\n"
                        )
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🔄 Обновить", "callback_data": "user_profile"}],
                                [{"text": "🔙 Главное меню", "callback_data": "main_menu"}]
                            ]
                        }
                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": profile_text, "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data == "top_up_ltc":
                        cursor.execute("SELECT ltc_address FROM users WHERE user_id = ?", (chat_id,))
                        row = cursor.fetchone()
                        conn.close()
                        ltc_addr = row[0] if row else "Адрес не найден"

                        topup_text = f"💰 <b>ПОПОЛНЕНИЕ БАЛАНСА LTC</b>\n\nОтправьте Litecoin на адрес:\n<code>{ltc_addr}</code>"
                        keyboard = {"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "user_profile"}]]}
                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": topup_text, "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data == "main_menu":
                        conn.close()
                        welcome_msg = get_config("welcome_msg")
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🏙️ Открыть каталог", "callback_data": "open_catalog"}],
                                [{"text": "👤 Мой профиль", "callback_data": "user_profile"},
                                 {"text": "💰 Пополнить LTC", "callback_data": "top_up_ltc"}]
                            ]
                        }
                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"🏠 <b>Главное меню:</b>\n\n{welcome_msg}",
                            "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data.startswith("city_"):
                        selected_city = callback_data.replace("city_", "").strip()
                        cursor.execute("SELECT district FROM districts WHERE city = ?", (selected_city,))
                        districts = [row[0] for row in cursor.fetchall()]
                        conn.close()

                        if not districts:
                            keyboard = {"inline_keyboard": [[{"text": "🔙 К городам", "callback_data": "open_catalog"}]]}
                            await client.post(f"{api_url}/editMessageText", json={
                                "chat_id": chat_id, "message_id": message_id,
                                "text": f"⚠️ В городе <b>{selected_city}</b> пока нет районов.",
                                "parse_mode": "HTML", "reply_markup": keyboard
                            })
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📍 {d}", "callback_data": f"dist_{d}"}]] for d in districts}
                        keyboard["inline_keyboard"].append([{"text": "🔙 К городам", "callback_data": "open_catalog"}])
                        
                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"🏙️ Город: <b>{selected_city}</b>\nВыберите район:",
                            "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data.startswith("dist_"):
                        selected_district = callback_data.replace("dist_", "").strip()
                        cursor.execute("SELECT name FROM categories")
                        categories = [row[0] for row in cursor.fetchall()]
                        conn.close()
                        
                        if not categories:
                            keyboard = {"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "open_catalog"}]]}
                            await client.post(f"{api_url}/editMessageText", json={
                                "chat_id": chat_id, "message_id": message_id,
                                "text": "⚠️ Категории не настроены.", "reply_markup": keyboard
                            })
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📂 {cat}", "callback_data": f"cat_{selected_district}_{cat}"}]] for cat in categories}
                        keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "open_catalog"}])

                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"📍 Район: <b>{selected_district}</b>\nВыберите категорию:",
                            "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data.startswith("cat_"):
                        parts = callback_data.replace("cat_", "").split("_", 1)
                        if len(parts) < 2:
                            conn.close()
                            return
                        
                        selected_district = parts[0]
                        selected_cat = parts[1]

                        cursor.execute("SELECT id, name, weight, price, stock FROM products WHERE district = ? AND category = ? AND stock > 0", (selected_district, selected_cat))
                        products = cursor.fetchall()
                        conn.close()

                        if not products:
                            keyboard = {"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": f"dist_{selected_district}"}]]}
                            await client.post(f"{api_url}/editMessageText", json={
                                "chat_id": chat_id, "message_id": message_id,
                                "text": f"📦 В категории <b>{selected_cat}</b> нет товаров в наличии.",
                                "parse_mode": "HTML", "reply_markup": keyboard
                            })
                            return

                        keyboard = {"inline_keyboard": [[{"text": f"📦 {p[1]} ({p[2]}) — ${p[3]} (Остаток: {p[4]} шт.)", "callback_data": f"buy_{p[0]}"}]] for p in products}
                        keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": f"dist_{selected_district}"}])

                        await client.post(f"{api_url}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"📂 Категория: <b>{selected_cat}</b>\nВыберите товар:",
                            "parse_mode": "HTML", "reply_markup": keyboard
                        })

                    elif callback_data.startswith("buy_"):
                        prod_id_to_buy = int(callback_data.replace("buy_", "").strip())
                        
                        cursor.execute("SELECT id, name, weight, price, product_link, p