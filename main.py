import os
import sqlite3
from fastapi import FastAPI, Form, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
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
            is_banned INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Новичок',
            notes TEXT DEFAULT '',
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

            # Проверка на блокировку (Бан)
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            b_row = cursor.fetchone()
            if b_row and b_row[0] == 1:
                conn.close()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(f"{api_url}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "❌ <b>Ваш аккаунт заблокирован администратором.</b> Доступ к боту закрыт.",
                        "parse_mode": "HTML"
                    })
                return {"ok": True}

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
                        
                        cursor.execute("SELECT id, name, weight, price, product_link, photo_link, district, stock, created_at FROM products WHERE id = ?", (prod_id_to_buy,))
                        product = cursor.fetchone()

                        if product:
                            prod_id, p_name, p_weight, p_price, p_link, p_photo, p_dist, p_stock, p_created = product
                            
                            cursor.execute("SELECT username, full_name FROM users WHERE user_id = ?", (chat_id,))
                            u_info = cursor.fetchone()
                            u_uname = u_info[0] if u_info else "нет"
                            u_fname = u_info[1] if u_info else "Без имени"

                            cursor.execute("""
                                INSERT INTO purchases (user_id, username, full_name, product_name, weight, price, district, created_at) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (chat_id, u_uname, u_fname, p_name, p_weight, p_price, p_dist, p_created))
                            
                            cursor.execute("UPDATE districts SET items = items + 1 WHERE district = ?", (p_dist,))
                            
                            new_stock = p_stock - 1
                            if new_stock > 0:
                                cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))
                            else:
                                cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                                
                            conn.commit()
                        conn.close()

                        if product:
                            onetime_msg = get_config("onetime_msg")
                            delivery_text = f"✅ <b>{onetime_msg}</b>\n\n<b>{product[1]} ({product[2]})</b>\nЦена: ${product[3]}\n"
                            if product[4]:
                                delivery_text += f"🔗 <b>Ссылка:</b> {product[4]}"

                            keyboard = {"inline_keyboard": [[{"text": "🏙️ В каталог", "callback_data": "open_catalog"}, {"text": "👤 Профиль", "callback_data": "user_profile"}]]}

                            try:
                                await client.post(f"{api_url}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                            except Exception:
                                pass

                            if product[5]:
                                await client.post(f"{api_url}/sendPhoto", json={
                                    "chat_id": chat_id, "photo": product[5],
                                    "caption": delivery_text, "parse_mode": "HTML", "reply_markup": keyboard
                                })
                            else:
                                await client.post(f"{api_url}/sendMessage", json={
                                    "chat_id": chat_id, "text": delivery_text,
                                    "parse_mode": "HTML", "reply_markup": keyboard
                                })
                        else:
                            await client.post(f"{api_url}/answerCallbackQuery", json={"callback_query_id": query_id, "text": "⚠️ Товар закончился!", "show_alert": True})

    except Exception as e:
        print(f"Webhook error: {e}")
        
    return {"ok": True}

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STELLA SYSTEM</title>
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
            --stars-opacity: 0.12;
        }
        [data-theme="light"] {
            --bg-color: #f1f5f9;
            --bg-gradient: radial-gradient(circle at 50% 30%, #e2e8f0 0%, #cbd5e1 100%);
            --card-bg: rgba(255, 255, 255, 0.9);
            --border-color: rgba(2, 132, 199, 0.3);
            --text-color: #0f172a;
            --text-muted: #64748b;
            --input-bg: rgba(241, 245, 249, 0.9);
            --input-border: rgba(203, 213, 225, 0.8);
            --stars-opacity: 0.03;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--bg-color); background-image: var(--bg-gradient); color: var(--text-color); 
            display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; padding: 20px;
            overflow-x: hidden; position: relative; transition: background 0.3s ease, color 0.3s ease;
        }
        body::before {
            content: ""; position: absolute; width: 100%; height: 100%; top: 0; left: 0;
            background-image: radial-gradient(var(--text-color) 1px, transparent 0); background-size: 35px 35px; opacity: var(--stars-opacity); z-index: -1;
        }
        .header-container { width: 100%; max-width: 480px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .header-title h1 { font-size: 16px; letter-spacing: 3px; font-weight: 600; color: #38bdf8; text-shadow: 0 0 10px rgba(56,189,248,0.4); }
        .header-title p { font-size: 10px; letter-spacing: 2px; color: var(--text-muted); }
        .menu-btn, .theme-btn { background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color); padding: 8px 10px; border-radius: 8px; cursor: pointer; font-size: 15px; }
        
        .sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: var(--card-bg); backdrop-filter: blur(20px); border-right: 1px solid var(--border-color); z-index: 1000; padding: 24px; transition: left 0.3s ease; display: flex; flex-direction: column; justify-content: space-between; }
        .sidebar.open { left: 0; }
        .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .sidebar-menu a { display: block; color: var(--text-color); text-decoration: none; padding: 10px 0; border-bottom: 1px solid var(--input-border); font-size: 14px; }
        .sidebar-menu a:hover { color: #38bdf8; }
        .admin-profile { background: var(--input-bg); border: 1px solid var(--border-color); padding: 12px; border-radius: 12px; display: flex; align-items: center; gap: 12px; margin-top: 15px; }
        .admin-avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 1px solid #38bdf8; }
        .admin-info h4 { font-size: 13px; font-weight: 600; }
        .admin-info p { font-size: 11px; color: #38bdf8; }
        .admin-info span { font-size: 10px; color: var(--text-muted); }
        
        .card { background: var(--card-bg); backdrop-filter: blur(15px); border: 1px solid var(--border-color); padding: 20px; border-radius: 20px; width: 100%; max-width: 480px; box-shadow: 0 0 35px rgba(14, 165, 233, 0.2); position: relative; }
        input, select, textarea { width: 100%; padding: 13px; margin-bottom: 12px; border-radius: 10px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-color); font-size: 14px; outline: none; }
        input:focus { border-color: #38bdf8; box-shadow: 0 0 8px rgba(56,189,248,0.3); }
        button[type="submit"] { width: 100%; padding: 13px; margin-top: 4px; border-radius: 10px; border: none; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(2,132,199,0.4); transition: transform 0.2s; }
        button[type="submit"]:active { transform: scale(0.98); }
        .logout { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); margin-top: 12px; text-align: center; display: block; text-decoration: none; padding: 11px; border-radius: 10px; color: #fca5a5; font-weight: 600; font-size: 14px; }
        
        .gear-container { position: absolute; top: 20px; right: 20px; }
        .gear-btn { background: var(--input-bg); border: 1px solid var(--border-color); color: #38bdf8; width: 36px; height: 36px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; transition: transform 0.3s; }
        .gear-btn:hover { transform: rotate(90deg); }
        .dropdown-menu { display: none; position: absolute; right: 0; top: 44px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; width: 180px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 50; overflow: hidden; backdrop-filter: blur(10px); }
        .dropdown-menu a, .dropdown-menu button { display: block; width: 100%; padding: 10px 14px; text-align: left; background: none; border: none; color: var(--text-color); font-size: 13px; cursor: pointer; text-decoration: none; }
        .dropdown-menu a:hover, .dropdown-menu button:hover { background: rgba(56, 189, 248, 0.1); color: #38bdf8; }
        .dropdown-menu .delete-opt { color: #fca5a5; }
        .dropdown-menu .delete-opt:hover { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(5px); justify-content: center; align-items: center; z-index: 1000; padding: 20px; }
        .modal-content { background: var(--card-bg); border: 1px solid var(--border-color); padding: 20px; border-radius: 16px; width: 100%; max-width: 400px; box-shadow: 0 0 30px rgba(56,189,248,0.2); }

        #holoOverlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(7, 10, 19, 0.85); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; }
        .holo-spinner { width: 70px; height: 70px; border: 3px solid rgba(56,189,248,0.2); border-top: 3px solid #38bdf8; border-radius: 50%; animation: spinHolo 0.8s linear infinite; box-shadow: 0 0 20px rgba(56,189,248,0.5); position: relative; display: flex; justify-content: center; align-items: center; }
        .holo-spinner::after { content: "✓"; font-size: 32px; color: #38bdf8; text-shadow: 0 0 10px #38bdf8; animation: pulseCheck 0.8s ease infinite alternate; }
        @keyframes spinHolo { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes pulseCheck { 0% { opacity: 0.4; } 100% { opacity: 1; } }

        #loader {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--bg-color);
            display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 9999;
            transition: opacity 0.5s ease;
        }
        .spinner { width: 50px; height: 50px; border: 3px solid rgba(56,189,248,0.2); border-top: 3px solid #38bdf8; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 15px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body data-theme="dark">
    <div id="loader">
        <div class="spinner"></div>
        <h2 style="color: #38bdf8; font-size: 14px; letter-spacing: 4px;">STELLA SYSTEM</h2>
    </div>

    <div id="holoOverlay">
        <div class="holo-spinner"></div>
        <p style="color: #38bdf8; margin-top: 15px; font-size: 13px; letter-spacing: 2px;">ДЕЙСТВИЕ ВЫПОЛНЕНО</p>
    </div>

    REPLACE_HEADER
    REPLACE_SIDEBAR
    <div class="card">REPLACE_CONTENT</div>

    <script>
        if (localStorage.getItem('theme') === 'light') {
            document.body.setAttribute('data-theme', 'light');
        }
        function toggleTheme() {
            const current = document.body.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }

        window.addEventListener('load', () => {
            const loader = document.getElementById('loader');
            loader.style.opacity = '0';
            setTimeout(() => loader.style.display = 'none', 500);
        });
        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
        function toggleDropdown(id = 'gearDropdown') {
            const menu = document.getElementById(id);
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        }
        window.onclick = function(event) {
            if (!event.target.matches('.gear-btn') && !event.target.closest('.gear-btn')) {
                const dropdowns = document.getElementsByClassName("dropdown-menu");
                for (let i = 0; i < dropdowns.length; i++) {
                    dropdowns[i].style.display = "none";
                }
            }
        }
        function openModal(id) { document.getElementById(id).style.display = 'flex'; const drop = document.getElementById('gearDropdown'); if(drop) drop.style.display = 'none'; }
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }
        
        function showHolo(form) {
            document.getElementById('holoOverlay').style.display = 'flex';
            setTimeout(() => { form.submit(); }, 700);
            return false;
        }
    </script>
</body>
</html>"""

def get_page(content: str, show_full_nav: bool = False) -> str:
    if show_full_nav:
        header_html = """
        <div class="header-container">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div class="header-title" style="text-align: center;"><h1>STELLA SYSTEM</h1><p>CONTROL SYSTEM</p></div>
            <button class="theme-btn" onclick="toggleTheme()" title="Сменить тему">🌓</button>
        </div>
        """
        sidebar_html = f"""
        <div id="sidebar" class="sidebar">
            <div>
                <div class="sidebar-header"><h3>Управление</h3><button class="menu-btn" onclick="toggleSidebar()">✕</button></div>
                <div class="sidebar-menu">
                    <a href="/dashboard">📊 Дашборд</a>
                    <a href="/bot-settings">🤖 Настройки бота</a>
                    <a href="/bot-messages">💬 Сообщения бота</a>
                    <a href="/clients">👥 Клиентская база</a>
                    <a href="/cities">🏙️ Города</a>
                    <a href="/districts">📍 Районы</a>
                    <a href="/categories">📂 Категории</a>
                    <a href="/products">📦 Товары</a>
                    <a href="/purchases-history">📜 История покупок</a>
                    <a href="/config-auth" style="color: #38bdf8;">⚙️ Изменить пароль/пин</a>
                    <a href="/logout" style="color: #fca5a5;">🚪 Выход</a>
                </div>
            </div>
            <div class="admin-profile">
                <img src="{get_config('admin_avatar')}" alt="Avatar" class="admin-avatar">
                <div class="admin-info">
                    <h4>{get_config('admin_name')}</h4>
                    <p>{get_config('admin_username')}</p>
                    <span>ID: {get_config('admin_id')}</span>
                </div>
            </div>
        </div>
        """
    else:
        header_html = """
        <div class="header-container" style="justify-content: space-between;">
            <div style="width: 36px;"></div>
            <div class="header-title" style="text-align: center;"><h1>STELLA SYSTEM</h1><p>ACCESS PORTAL</p></div>
            <button class="theme-btn" onclick="toggleTheme()" title="Сменить тему">🌓</button>
        </div>
        """
        sidebar_html = ""

    page = BASE_TEMPLATE.replace("REPLACE_HEADER", header_html)
    page = page.replace("REPLACE_SIDEBAR", sidebar_html)
    page = page.replace("REPLACE_CONTENT", content)
    return page

@app.get("/", response_class=HTMLResponse)
async def index():
    content = """
        <div style="text-align: center; margin-bottom: 16px;">
            <h3 style="font-size: 15px; color: #38bdf8; letter-spacing: 1px;">Шаг 1: Авторизация</h3>
        </div>
        <form method="POST" action="/verify-login">
            <input type="text" name="login" placeholder="Ваш логин" required>
            <input type="password" name="password" placeholder="Ваш пароль" required>
            <button type="submit">Далее →</button>
        </form>
    """
    return get_page(content, show_full_nav=False)

@app.post("/verify-login", response_class=HTMLResponse)
async def verify_login(login: str = Form(...), password: str = Form(...)):
    stored_login = get_config("admin_login")
    stored_password = get_config("admin_password")
    
    if login != stored_login or password != stored_password:
        return RedirectResponse(url="/", status_code=303)
        
    response = RedirectResponse(url="/pin-page", status_code=303)
    response.set_cookie(key="pre_auth", value="true")
    return response

@app.get("/pin-page", response_class=HTMLResponse)
async def pin_page(request: Request):
    if request.cookies.get("pre_auth") != "true":
        return RedirectResponse(url="/", status_code=303)
    
    content = """
        <div style="text-align: center; margin-bottom: 16px;">
            <h3 style="font-size: 15px; color: #38bdf8; letter-spacing: 1px;">Шаг 2: ПИН-код</h3>
        </div>
        <form method="POST" action="/verify-pin">
            <input type="password" name="pin_code" placeholder="• • • •" maxlength="4" minlength="4" inputmode="numeric" style="text-align:center; font-size: 20px; letter-spacing: 8px;" required>
            <button type="submit">Подтвердить вход</button>
        </form>
    """
    return get_page(content, show_full_nav=False)

@app.post("/verify-pin", response_class=HTMLResponse)
async def verify_pin(request: Request, pin_code: str = Form(...)):
    if request.cookies.get("pre_auth") != "true":
        return RedirectResponse(url="/", status_code=303)
        
    stored_pin = get_config("admin_pin")
    if pin_code != stored_pin:
        return RedirectResponse(url="/pin-page", status_code=303)
        
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="auth", value="true")
    response.delete_cookie(key="pre_auth")
    return response

@app.get("/config-auth", response_class=HTMLResponse)
async def config_auth_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)
        
    content = f"""
        <div style="text-align:center; margin-bottom: 14px;"><h2>Смена данных входа</h2></div>
        <form method="POST" action="/update-auth-data">
            <input type="text" name="new_login" value="{get_config('admin_login')}" placeholder="Новый логин" required>
            <input type="password" name="new_password" placeholder="Новый пароль" required>
            <input type="password" name="new_pin" value="{get_config('admin_pin')}" maxlength="4" placeholder="Новый ПИН (4 цифры)" required>
            <button type="submit">Сохранить новые данные</button>
        </form>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
    """
    return get_page(content, show_full_nav=True)

@app.post("/update-auth-data", response_class=HTMLResponse)
async def update_auth_data(request: Request, new_login: str = Form(...), new_password: str = Form(...), new_pin: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)
        
    set_config("admin_login", new_login.strip())
    set_config("admin_password", new_password.strip())
    set_config("admin_pin", new_pin.strip()[:4])
    
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/logout", response_class=HTMLResponse)
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="auth")
    response.delete_cookie(key="pre_auth")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_get(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT district, items FROM districts")
    districts_data = cursor.fetchall()
    conn.close()

    labels = [d[0] for d in districts_data] if districts_data else ["Нет районов"]
    items_data = [d[1] for d in districts_data] if districts_data else [0]
    bot_name = get_config("bot_name")

    labels_json = json.dumps(labels, ensure_ascii=False)
    items_json = json.dumps(items_data, ensure_ascii=False)

    dashboard_content = """
        <div style="text-align:center; margin-bottom: 12px;">
            <p style="color: #38bdf8; font-size: 11px; letter-spacing: 2px; font-weight: 600;">АНАЛИТИКА</p>
            <h2 style="font-size: 18px; margin-top: 2px;">Дашборд и Графики</h2>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 11px; color: var(--text-muted);">Активный бот:</span>
            <span style="font-size: 12px; color: #4ade80; font-weight: 600;">🤖 BOT_NAME_VAL</span>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; margin-bottom: 12px;">
            <span style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 6px;">Доход по месяцам (USD / LTC):</span>
            <canvas id="incomeChart" style="max-height: 110px;"></canvas>
        </div>

        <div style="background: var(--input-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; margin-bottom: 12px;">
            <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 6px;">
                <span style="font-size: 11px; color: var(--text-muted);">Районы (куплено товаров):</span>
                <a href="/products" style="font-size: 10px; color: #38bdf8; text-decoration: none;">⚙️ Товары</a>
            </div>
            <canvas id="districtChart" style="max-height: 110px;"></canvas>
        </div>

        <a href='/logout' class='logout' style='text-decoration: none;'>Выйти</a>

        <script>
            const ctxIncome = document.getElementById('incomeChart').getContext('2d');
            new Chart(ctxIncome, {
                type: 'line',
                data: {
                    labels: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0, 0],
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        borderWidth: 2,
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

            const districtsLabels = LABELS_JSON_PLACEHOLDER;
            const districtsItems = ITEMS_JSON_PLACEHOLDER;

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
    dashboard_content = dashboard_content.replace("BOT_NAME_VAL", bot_name)
    dashboard_content = dashboard_content.replace("LABELS_JSON_PLACEHOLDER", labels_json)
    dashboard_content = dashboard_content.replace("ITEMS_JSON_PLACEHOLDER", items_json)
    
    return get_page(dashboard_content, show_full_nav=True)

@app.get("/clients", response_class=HTMLResponse)
async def clients_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, avatar_url, first_seen, rank, is_banned FROM users ORDER BY first_seen DESC")
    users = cursor.fetchall()
    conn.close()

    list_html = "".join([f"""
        <div style="display: flex; align-items: center; gap: 12px; background: var(--input-bg); padding: 10px 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid var(--input-border);">
            <img src="{u[3]}" alt="Avatar" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover; border: 1px solid #38bdf8; flex-shrink: 0;">
            <div style="flex-grow: 1; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                    <span style="font-size: 13px; font-weight: 600; color: #f8fafc;">{u[2] or 'Без имени'}</span>
                    <span style="font-size: 11px; color: {'#ef4444' if u[6] == 1 else '#4ade80'};">{'🔴 Заблокирован' if u[6] == 1 else u[5]}</span>
                </div>
                <div style="font-size: 10px; color: var(--text-muted);">ID: {u[0]} | Юзер: {u[1]}</div>
            </div>
        </div>
    """ for u in users]) if users else '<p style="font-size: 11px; color: var(--text-muted); text-align: center;">Клиентов пока нет</p>'

    content = f"""
        <div style="text-align:center; margin-bottom: 14px;"><h2>Клиентская база ({len(users)})</h2></div>
        <div style="max-height: 280px; overflow-y: auto; margin-bottom: 14px;">{list_html}</div>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
    """
    return get_page(content, show_full_nav=True)

@app.get("/bot-settings", response_class=HTMLResponse)
async def bot_settings_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)
        
    bot_name = get_config("bot_name")
    content = f"""
        <div style="text-align:center; margin-bottom: 14px;"><h2>Управление ботом</h2></div>
        <p style="font-size: 12px; color: #4ade80; margin-bottom: 10px;">🤖 Текущий: {bot_name}</p>
        <form method="POST" action="/update-bot">
            <input type="text" name="bot_name" placeholder="Имя бота (например, @MyBot)" required>
            <input type="text" name="bot_token" placeholder="Токен от BotFather" required>
            <button type="submit">Сохранить и запустить</button>
        </form>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
    """
    return get_page(content, show_full_nav=True)

@app.post("/update-bot", response_class=HTMLResponse)
async def update_bot(request: Request, bot_name: str = Form(...), bot_token: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    if bot_name and bot_token:
        set_config("bot_name", bot_name)
        set_config("bot_token", bot_token)
        host_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            await client.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={host_url}/webhook&allowed_updates=[\"message\",\"callback_query\"]")
        return RedirectResponse(url="/bot-settings", status_code=303)
    return RedirectResponse(url="/bot-settings", status_code=303)

@app.get("/bot-messages", response_class=HTMLResponse)
async def bot_messages_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    welcome_msg = get_config("welcome_msg")
    onetime_msg = get_config("onetime_msg")
    content = f"""
        <h2>Сообщения бота</h2>
        <form method="POST" action="/update-bot-messages">
            <textarea name="welcome_msg" rows="3" required>{welcome_msg}</textarea>
            <textarea name="onetime_msg" rows="3" required>{onetime_msg}</textarea>
            <button type="submit">Сохранить</button>
        </form>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>Назад</a>
    """
    return get_page(content, show_full_nav=True)

@app.post("/update-bot-messages", response_class=HTMLResponse)
async def update_bot_messages(request: Request, welcome_msg: str = Form(...), onetime_msg: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    set_config("welcome_msg", welcome_msg)
    set_config("onetime_msg", onetime_msg)
    return RedirectResponse(url="/bot-messages", status_code=303)

# ==================== УПРАВЛЕНИЕ ГОРОДАМИ ====================
@app.get("/cities", response_class=HTMLResponse)
async def cities_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cities")
    cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    list_html = "".join([f'<div style="background: var(--input-bg); padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; border: 1px solid var(--input-border); font-size: 14px;">🏙️ {c}</div>' for c in cities]) or '<p style="font-size: 12px; color: var(--text-muted); text-align: center; padding: 20px;">Список городов пуст</p>'
    delete_options = "".join([f'<option value="{c}">{c}</option>' for c in cities])

    content = f"""
        <div class="gear-container">
            <button class="gear-btn" onclick="toggleDropdown('cityDropdown')" title="Настройки">⚙️</button>
            <div id="cityDropdown" class="dropdown-menu">
                <button onclick="openModal('addCityModal')">➕ Добавить город</button>
                <button class="delete-opt" onclick="openModal('deleteCityModal')">🗑️ Удалить город</button>
            </div>
        </div>

        <h2 style="margin-bottom: 15px;">Города</h2>
        <div style="max-height: 300px; overflow-y: auto; margin-bottom: 15px;">{list_html}</div>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>

        <div id="addCityModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #38bdf8; font-size: 15px; margin-bottom: 12px;">Добавить город</h3>
                <form method="POST" action="/add-city" onsubmit="return showHolo(this)">
                    <input type="text" name="city_name" placeholder="Название города" required>
                    <button type="submit">Сохранить</button>
                </form>
                <button type="button" onclick="closeModal('addCityModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>

        <div id="deleteCityModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #ef4444; font-size: 15px; margin-bottom: 12px;">Удалить город</h3>
                <form method="POST" action="/delete-city" onsubmit="return showHolo(this)">
                    <select name="city_name" required style="border-color: rgba(239, 68, 68, 0.4);">
                        <option value="" disabled selected>Выберите город</option>
                        {delete_options}
                    </select>
                    <button type="submit" style="background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 4px 15px rgba(239,68,68,0.4);">Удалить</button>
                </form>
                <button type="button" onclick="closeModal('deleteCityModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>
    """
    return get_page(content, show_full_nav=True)

@app.post("/add-city", response_class=HTMLResponse)
async def add_city(request: Request, city_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city_name.strip(),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/cities", status_code=303)

@app.post("/delete-city", response_class=HTMLResponse)
async def delete_city(request: Request, city_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cities WHERE name = ?", (city_name,))
    cursor.execute("DELETE FROM districts WHERE city = ?", (city_name,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/cities", status_code=303)

# ==================== УПРАВЛЕНИЕ РАЙОНАМИ ====================
@app.get("/districts", response_class=HTMLResponse)
async def districts_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cities")
    cities = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT city, district FROM districts")
    districts = cursor.fetchall()
    conn.close()
    
    city_options = "".join([f'<option value="{c}">{c}</option>' for c in cities])
    delete_options = "".join([f'<option value="{d[1]}">{d[1]} ({d[0]})</option>' for d in districts])
    
    list_html = "".join([f'<div style="background: var(--input-bg); padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; border: 1px solid var(--input-border); font-size: 14px;">📍 {d[1]} <span style="color:var(--text-muted); font-size:12px;">({d[0]})</span></div>' for d in districts]) or '<p style="font-size: 12px; color: var(--text-muted); text-align: center; padding: 20px;">Список районов пуст</p>'

    content = f"""
        <div class="gear-container">
            <button class="gear-btn" onclick="toggleDropdown('districtDropdown')" title="Настройки">⚙️</button>
            <div id="districtDropdown" class="dropdown-menu">
                <button onclick="openModal('addDistrictModal')">➕ Добавить район</button>
                <button class="delete-opt" onclick="openModal('deleteDistrictModal')">🗑️ Удалить район</button>
            </div>
        </div>

        <h2 style="margin-bottom: 15px;">Районы</h2>
        <div style="max-height: 300px; overflow-y: auto; margin-bottom: 15px;">{list_html}</div>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>

        <div id="addDistrictModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #38bdf8; font-size: 15px; margin-bottom: 12px;">Добавить район</h3>
                <form method="POST" action="/add-district" onsubmit="return showHolo(this)">
                    <select name="city" required>
                        <option value="" disabled selected>Выберите город</option>
                        {city_options}
                    </select>
                    <input type="text" name="district_name" placeholder="Название района" required>
                    <button type="submit">Сохранить</button>
                </form>
                <button type="button" onclick="closeModal('addDistrictModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>

        <div id="deleteDistrictModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #ef4444; font-size: 15px; margin-bottom: 12px;">Удалить район</h3>
                <form method="POST" action="/delete-district" onsubmit="return showHolo(this)">
                    <select name="district_name" required style="border-color: rgba(239, 68, 68, 0.4);">
                        <option value="" disabled selected>Выберите район</option>
                        {delete_options}
                    </select>
                    <button type="submit" style="background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 4px 15px rgba(239,68,68,0.4);">Удалить</button>
                </form>
                <button type="button" onclick="closeModal('deleteDistrictModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>
    """
    return get_page(content, show_full_nav=True)

@app.post("/add-district", response_class=HTMLResponse)
async def add_district(request: Request, city: str = Form(...), district_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO districts (city, district) VALUES (?, ?)", (city.strip(), district_name.strip()))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/districts", status_code=303)

@app.post("/delete-district", response_class=HTMLResponse)
async def delete_district(request: Request, district_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM districts WHERE district = ?", (district_name,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/districts", status_code=303)

# ==================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ====================
@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    list_html = "".join([f'<div style="background: var(--input-bg); padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; border: 1px solid var(--input-border); font-size: 14px;">📂 {c}</div>' for c in categories]) or '<p style="font-size: 12px; color: var(--text-muted); text-align: center; padding: 20px;">Список категорий пуст</p>'
    delete_options = "".join([f'<option value="{c}">{c}</option>' for c in categories])

    content = f"""
        <div class="gear-container">
            <button class="gear-btn" onclick="toggleDropdown('categoryDropdown')" title="Настройки">⚙️</button>
            <div id="categoryDropdown" class="dropdown-menu">
                <button onclick="openModal('addModal')">➕ Добавить категорию</button>
                <button class="delete-opt" onclick="openModal('deleteModal')">🗑️ Удалить категорию</button>
            </div>
        </div>

        <h2 style="margin-bottom: 15px;">Категории</h2>
        <div style="max-height: 300px; overflow-y: auto; margin-bottom: 15px;">{list_html}</div>
        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>

        <div id="addModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #38bdf8; font-size: 15px; margin-bottom: 12px;">Добавить категорию</h3>
                <form method="POST" action="/add-category" onsubmit="return showHolo(this)">
                    <input type="text" name="category_name" placeholder="Название категории" required>
                    <button type="submit">Сохранить</button>
                </form>
                <button type="button" onclick="closeModal('addModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>

        <div id="deleteModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #ef4444; font-size: 15px; margin-bottom: 12px;">Удалить категорию</h3>
                <form method="POST" action="/delete-category" onsubmit="return showHolo(this)">
                    <select name="category_name" required style="border-color: rgba(239, 68, 68, 0.4);">
                        <option value="" disabled selected>Выберите категорию</option>
                        {delete_options}
                    </select>
                    <button type="submit" style="background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 4px 15px rgba(239,68,68,0.4);">Удалить</button>
                </form>
                <button type="button" onclick="closeModal('deleteModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>
    """
    return get_page(content, show_full_nav=True)

@app.post("/add-category", response_class=HTMLResponse)
async def add_category(request: Request, category_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category_name.strip(),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/categories", status_code=303)

@app.post("/delete-category", response_class=HTMLResponse)
async def delete_category(request: Request, category_name: str = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE name = ?", (category_name.strip(),))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/categories", status_code=303)

# ==================== УПРАВЛЕНИЕ ТОВАРАМИ С ВЕСОМ ====================
@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT name FROM cities")
    cities = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT district, city FROM districts")
    districts = cursor.fetchall()
    
    cursor.execute("SELECT id, category, city, district, name, weight, price, stock, created_at FROM products")
    products = cursor.fetchall()
    conn.close()

    cat_options = "".join([f'<option value="{c}">{c}</option>' for c in categories])
    city_options = "".join([f'<option value="{c}">{c}</option>' for c in cities])
    district_options = "".join([f'<option value="{d[0]}">{d[0]} ({d[1]})</option>' for d in districts])
    delete_product_options = "".join([f'<option value="{p[0]}">{p[4]} ({p[5]}) — ${p[6]} ({p[3]})</option>' for p in products])

    rows_html = "".join([f"""
        <tr style="border-bottom: 1px solid var(--input-border); font-size: 13px;">
            <td style="padding: 10px;"><b>{p[4]}</b> <span style="color: #38bdf8;">({p[5]})</span></td>
            <td style="padding: 10px; color: #38bdf8;">{p[1]}</td>
            <td style="padding: 10px; color: var(--text-muted);">{p[3]} ({p[2]})</td>
            <td style="padding: 10px;"><b>${p[6]}</b></td>
            <td style="padding: 10px;"><span style="color: #4ade80; background: rgba(74,222,128,0.1); padding: 3px 6px; border-radius: 4px; font-size: 11px;">🟢 В продаже ({p[7]} шт.)</span></td>
            <td style="padding: 10px; font-size: 11px; color: var(--text-muted);">{p[8]}</td>
        </tr>
    """ for p in products]) if products else '<tr><td colspan="6" style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 12px;">Список товаров пуст</td></tr>'

    content = f"""
        <div class="gear-container">
            <button class="gear-btn" onclick="toggleDropdown('prodDropdown')" title="Настройки">⚙️</button>
            <div id="prodDropdown" class="dropdown-menu">
                <button onclick="openModal('addProductModal')">➕ Добавить товар</button>
                <button class="delete-opt" onclick="openModal('deleteProductModal')">🗑️ Удалить товар</button>
            </div>
        </div>

        <h2 style="margin-bottom: 15px;">Товары на складе</h2>
        
        <div style="max-height: 320px; overflow-y: auto; margin-bottom: 15px; border: 1px solid var(--input-border); border-radius: 12px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background: var(--input-bg); border-bottom: 1px solid var(--border-color); font-size: 11px; color: var(--text-muted);">
                        <th style="padding: 10px;">Товар (Вес)</th>
                        <th style="padding: 10px;">Категория</th>
                        <th style="padding: 10px;">Район (Город)</th>
                        <th style="padding: 10px;">Цена</th>
                        <th style="padding: 10px;">Статус</th>
                        <th style="padding: 10px;">Добавлен</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>

        <div id="addProductModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #38bdf8; font-size: 15px; margin-bottom: 12px;">Добавить товар</h3>
                <form method="POST" action="/add-product" onsubmit="return showHolo(this)">
                    <select name="category" required><option value="" disabled selected>Категория</option>{cat_options}</select>
                    <select name="city" required><option value="" disabled selected>Город</option>{city_options}</select>
                    <select name="district" required><option value="" disabled selected>Район</option>{district_options}</select>
                    <input type="text" name="product_name" placeholder="Название товара" required>
                    <input type="text" name="weight" placeholder="Фасовка/Вес (например, 1 г, 2 г)" required>
                    <input type="number" step="0.01" name="price" placeholder="Цена ($)" required>
                    <input type="number" name="stock" placeholder="Количество (шт.)" value="1" min="1" required>
                    <input type="url" name="product_link" placeholder="Ссылка выдачи после покупки">
                    <button type="submit">Сохранить товар</button>
                </form>
                <button type="button" onclick="closeModal('addProductModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>

        <div id="deleteProductModal" class="modal">
            <div class="modal-content">
                <h3 style="color: #ef4444; font-size: 15px; margin-bottom: 12px;">Удалить товар</h3>
                <form method="POST" action="/delete-product" onsubmit="return showHolo(this)">
                    <select name="product_id" required style="border-color: rgba(239, 68, 68, 0.4);">
                        <option value="" disabled selected>Выберите товар</option>
                        {delete_product_options}
                    </select>
                    <button type="submit" style="background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 4px 15px rgba(239,68,68,0.4);">Удалить</button>
                </form>
                <button type="button" onclick="closeModal('deleteProductModal')" style="width: 100%; margin-top: 8px; background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px; border-radius: 10px; cursor: pointer;">Отмена</button>
            </div>
        </div>
    """
    return get_page(content, show_full_nav=True)

@app.post("/add-product", response_class=HTMLResponse)
async def add_product(request: Request, category: str = Form(...), city: str = Form(...), district: str = Form(...), product_name: str = Form(...), weight: str = Form(...), price: float = Form(...), stock: int = Form(1), product_link: str = Form("")):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (category, city, district, name, weight, price, stock, product_link, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (category.strip(), city.strip(), district.strip(), product_name.strip(), weight.strip(), price, stock, product_link.strip(), now_time))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/products", status_code=303)

@app.post("/delete-product", response_class=HTMLResponse)
async def delete_product(request: Request, product_id: int = Form(...)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/products", status_code=303)

# ==================== ИСТОРИЯ ПОКУПОК ====================
@app.get("/purchases-history", response_class=HTMLResponse)
async def purchases_history_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, weight, price, district, created_at, sold_at, full_name, username, user_id 
        FROM purchases ORDER BY id DESC
    """)
    purchases = cursor.fetchall()
    conn.close()

    history_rows = "".join([f"""
        <tr style="border-bottom: 1px solid var(--input-border); font-size: 12px;">
            <td style="padding: 10px;">
                <b>{p[0]}</b> <span style="color: #38bdf8;">({p[1]})</span><br>
                <span style="color: #38bdf8;">${p[2]}</span> | <span style="color: var(--text-muted);">{p[3]}</span>
            </td>
            <td style="padding: 10px;">
                <b>{p[6]}</b><br>
                <span style="color: #4ade80;">{p[7]}</span> <span style="color: var(--text-muted);">(ID: {p[8]})</span>
            </td>
            <td style="padding: 10px; color: var(--text-muted);">
                ➕ Добавлен: {p[4]}<br>
                🛒 Продан: <b style="color: #fca5a5;">{p[5]}</b>
            </td>
        </tr>
    """ for p in purchases]) if purchases else '<tr><td colspan="3" style="text-align: center; padding: 25px; color: var(--text-muted); font-size: 12px;">История покупок пуста</td></tr>'

    content = f"""
        <h2 style="margin-bottom: 15px;">📜 История покупок</h2>
        
        <div style="max-height: 380px; overflow-y: auto; margin-bottom: 15px; border: 1px solid var(--input-border); border-radius: 12px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background: var(--input-bg); border-bottom: 1px solid var(--border-color); font-size: 11px; color: var(--text-muted);">
                        <th style="padding: 10px;">Товар (Вес) / Цена / Район</th>
                        <th style="padding: 10px;">Покупатель (Юзер)</th>
                        <th style="padding: 10px;">Таймстампы (Даты)</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
        </div>

        <a href='/dashboard' class='logout' style='background: #0284c7; color: #fff; border: none; text-decoration: none;'>← В дашборд</a>
    """
    return get_page(content, show_full_nav=True)


# ==================== API ДЛЯ АДМИНКИ (Ранги, Баны, Рассылка) ====================

class UpdateClientSchema(BaseModel):
    rank: str
    notes: str

class BroadcastSchema(BaseModel):
    message_text: str

@app.post("/api/clients/{user_id}/update")
async def update_client(user_id: int, data: UpdateClientSchema):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET rank = ?, notes = ? WHERE user_id = ?", 
        (data.rank, data.notes, user_id)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Данные клиента успешно обновлены"}

@app.post("/api/clients/{user_id}/toggle-ban")
async def toggle_ban(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Клиент не найден в базе")
    
    new_status = 0 if row[0] == 1 else 1
    cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, user_id))
    conn.commit()
    conn.close()
    
    token = get_config("bot_token")
    if token:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if new_status == 1:
                try:
                    await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                        "chat_id": user_id,
                        "text": "❌ <b>Вы были заблокированы администратором.</b> Доступ к боту закрыт.",
                        "parse_mode": "HTML"
                    })
                except Exception:
                    pass
            else:
                try:
                    await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                        "chat_id": user_id,
                        "text": "✅ <b>Ваш аккаунт был разблокирован.</b> Добро пожаловать обратно!",
                        "parse_mode": "HTML"
                    })
                except Exception:
                    pass

    return {"status": "success", "is_banned": new_status}

@app.post("/api/admin/broadcast")
async def send_broadcast(data: BroadcastSchema):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()
    
    token = get_config("bot_token")
    if not token:
        raise HTTPException(status_code=400, detail="Токен бота не настроен")

    success_count = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for user in users:
            try:
                res = await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                    "chat_id": user[0],
                    "text": data.message_text,
                    "parse_mode": "HTML"
                })
                if res.json().get("ok"):
                    success_count += 1
            except Exception:
                pass
            
    return {"status": "success", "sent_to": success_count}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
