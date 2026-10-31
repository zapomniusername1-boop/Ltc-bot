import os
import sqlite3
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import httpx

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
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('bot_name', 'Не привязан')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('bot_token', '')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('welcome_msg', 'Добро пожаловать в STELLA SYSTEM! Выберите город для покупки:')")
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
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user = msg["from"]
            user_id = user["id"]
            username = user.get("username", "нет")
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            
            avatar_url = await fetch_user_avatar(token, user_id)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, avatar_url) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name, avatar_url=excluded.avatar_url
            """, (user_id, f"@{username}" if username != "нет" else "нет", full_name, avatar_url))
            conn.commit()

            text = msg.get("text", "")
            
            if text == "/start":
                cursor.execute("SELECT name FROM cities")
                cities = [row[0] for row in cursor.fetchall()]
                conn.close()

                if not cities:
                    async with httpx.AsyncClient() as client:
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "В данный момент в боте нет доступных городов."
                        })
                    return {"ok": True}

                keyboard = {"inline_keyboard": [[{"text": f"🏙️ {city}", "callback_data": f"city_{city}"}]] for city in cities}
                
                welcome_msg = get_config("welcome_msg")
                async with httpx.AsyncClient() as client:
                    await client.post(f"{api_url}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": welcome_msg,
                        "reply_markup": keyboard
                    })
            else:
                conn.close()

        elif "callback_query" in data:
            cq = data["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            callback_data = cq["data"]
            query_id = cq["id"]

            async with httpx.AsyncClient() as client:
                try:
                    await client.post(f"{api_url}/answerCallbackQuery", json={"callback_query_id": query_id})
                except Exception as ex:
                    print(f"Answer callback error: {ex}")

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                try:
                    if callback_data.startswith("city_"):
                        selected_city = callback_data.replace("city_", "").strip()
                        
                        cursor.execute("SELECT district FROM districts WHERE city = ?", (selected_city,))
                        districts = [row[0] for row in cursor.fetchall()]

                        if not districts:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"⚠️ В городе <b>{selected_city}</b> пока нет добавленных районов. Добавьте их в панели управления!",
                                "parse_mode": "HTML"
                            })
                            conn.close()
                            return {"ok": True}

                        # Исправленная клавиатура для районов
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": f"📍 {d}", "callback_data": f"dist_{d}"}] 
                                for d in districts
                            ]
                        }
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
                                "text": "⚠️ Категории товаров не настроены."
                            })
                            conn.close()
                            return {"ok": True}

                        keyboard = {
                            "inline_keyboard": [
                                [{"text": f"📂 {cat}", "callback_data": f"cat_{selected_district}_{cat}"}] 
                                for cat in categories
                            ]
                        }
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
                            return {"ok": True}
                        
                        selected_district = parts[0]
                        selected_cat = parts[1]

                        cursor.execute("SELECT name, price FROM products WHERE district = ? AND category = ?", (selected_district, selected_cat))
                        products = cursor.fetchall()

                        if not products:
                            await client.post(f"{api_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"📦 В этой категории для района <b>{selected_district}</b> пока нет товаров.",
                                "parse_mode": "HTML"
                            })
                            conn.close()
                            return {"ok": True}

                        keyboard = {
                            "inline_keyboard": [
                                [{"text": f"📦 {p[0]} — ${p[1]}", "callback_data": f"buy_{p[0]}"}] 
                                for p in products
                            ]
                        }
                        await client.post(f"{api_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"Категория: <b>{selected_cat}</b>. Выберите товар:",
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        })

                    elif callback_data.startswith("buy_"):
                        prod_name = callback_data.replace("buy_", "").strip()
                        cursor.execute("SELECT name, product_link, photo_link FROM products WHERE name = ?", (prod_name,))
                        product = cursor.fetchone()

                        if product:
                            onetime_msg = get_config("onetime_msg")
                            delivery_text = f"{onetime_msg}\n\n<b>{product[0]}</b>\n"
                            if product[1]:
                                delivery_text += f"🔗 Ссылка: {product[1]}"

                            if product[2]:
                                await client.post(f"{api_url}/sendPhoto", json={
                                    "chat_id": chat_id,
                                    "photo": product[2],
                                    "caption": delivery_text,
                                    "parse_mode": "HTML"
                                })
                            else:
                                await client.post(f"{api_url}/sendMessage", json={
                                    "chat_id": chat_id,
                                    "text": delivery_text,
                                    "parse_mode": "HTML"
                                })
                finally:
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
            transition: left 0.3s ease; overflow-y: auto; display: flex; flex-direction: column; justify-content: space-between;
        }
        .sidebar.open { left: 0; }
        .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .sidebar-menu a {
            display: block; color: var(--text-color); text-decoration: none; padding: 10px 0;
            border-bottom: 1px solid var(--input-border); font-size: 14px; font-weight: 500;
        }
        .sidebar-menu a:hover { color: #38bdf8; }

        .admin-profile {
            background: var(--input-bg); border: 1px solid var(--border-color); padding: 12px;
            border-radius: 12px; display: flex; align-items: center; gap: 12px; margin-top: 15px;
        }
        .admin-avatar {
            width: 42px; height: 42px; border-radius: 50%; object-fit: cover;
            border: 1px solid #38bdf8;
        }
        .admin-info h4 { font-size: 13px; font-weight: 600; color: var(--text-color); }
        .admin-info p { font-size: 11px; color: #38bdf8; }
        .admin-info span { font-size: 10px; color: var(--text-muted); display: block; }

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
            display: none; position: fixed; top: 0; left: 0; width: 100%