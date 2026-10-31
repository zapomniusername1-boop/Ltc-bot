import os
import sqlite3
from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import uvicorn

app = FastAPI()

SECRET_PIN = "7777"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stella.db")


def init_db():
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """
  )
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS cities (
            name TEXT PRIMARY KEY
        )
    """
  )
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS districts (
            city TEXT,
            district TEXT PRIMARY KEY,
            items INTEGER DEFAULT 0,
            usd REAL DEFAULT 0,
            ltc REAL DEFAULT 0
        )
    """
  )
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    """
  )
  cursor.execute(
      """
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
    """
  )
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            avatar_url TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
  )
  conn.commit()

  cursor.execute(
      "INSERT OR IGNORE INTO config (key, value) VALUES ('bot_name', 'Не привязан')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO config (key, value) VALUES ('bot_token', '')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO config (key, value) VALUES ('welcome_msg', 'Добро"
      " пожаловать в STELLA SYSTEM! Выберите город для покупки:')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO config (key, value) VALUES ('onetime_msg',"
      " 'Оплата прошла успешно! Вот ваш товар:')"
  )
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


async def fetch_user_avatar(token: str, user_id: int) -> str:
  default_avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop"
  try:
    async with httpx.AsyncClient() as client:
      photos_res = await client.get(
          f"https://api.telegram.org/bot{token}/getUserProfilePhotos",
          params={"user_id": user_id, "limit": 1},
      )
      photos_data = photos_res.json()
      if photos_data.get("ok") and photos_data["result"]["total_count"] > 0:
        file_id = photos_data["result"]["photos"][0][-1]["file_id"]
        file_res = await client.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
        )
        file_data = file_res.json()
        if file_data.get("ok"):
          file_path = file_data["result"]["file_path"]
          return f"https://api.telegram.org/file/bot{token}/{file_path}"
  except Exception as e:
    print(f"Avatar fetch error: {e}")
  return default_avatar


# Вебхук Telegram: обрабатывает нажатия: Город -> Район -> Категория -> Товар
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
      full_name = (
          f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
      )

      avatar_url = await fetch_user_avatar(token, user_id)

      conn = sqlite3.connect(DB_PATH)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO users (user_id, username, full_name, avatar_url) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,"
          " full_name=excluded.full_name, avatar_url=excluded.avatar_url
            """,
          (
              user_id,
              f"@{username}" if username != "нет" else "нет",
              full_name,
              avatar_url,
          ),
      )
      conn.commit()

      text = msg.get("text", "")
      if text == "/start":
        cursor.execute("SELECT name FROM cities")
        cities = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not cities:
          async with httpx.AsyncClient() as client:
            await client.post(
                f"{api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "В данный момент в боте нет доступных городов из"
                        " админки."
                    ),
                },
            )
          return {"ok": True}

        keyboard = {
            "inline_keyboard": [
                [{"text": f"🏙️ {city}", "callback_data": f"city_{city}"}]
                for city in cities
            ]
        }
        welcome_msg = get_config("welcome_msg")
        async with httpx.AsyncClient() as client:
          await client.post(
              f"{api_url}/sendMessage",
              json={
                  "chat_id": chat_id,
                  "text": welcome_msg,
                  "reply_markup": keyboard,
              },
          )
      else:
        conn.close()

    elif "callback_query" in data:
      cq = data["callback_query"]
      chat_id = cq["message"]["chat"]["id"]
      callback_data = cq["data"]
      query_id = cq["id"]

      async with httpx.AsyncClient() as client:
        try:
          await client.post(
              f"{api_url}/answerCallbackQuery",
              json={"callback_query_id": query_id},
          )
        except Exception as ex:
          print(f"Answer callback error: {ex}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
          # 1. Выбор города -> Показ районов из админки
          if callback_data.startswith("city_"):
            selected_city = callback_data.replace("city_", "").strip()
            cursor.execute(
                "SELECT district FROM districts WHERE city = ?", (selected_city,)
            )
            districts = [row[0] for row in cursor.fetchall()]

            if not districts:
              await client.post(
                  f"{api_url}/sendMessage",
                  json={
                      "chat_id": chat_id,
                      "text": (
                          f"⚠️ В городе <b>{selected_city}</b> пока нет"
                          " добавленных районов в админке."
                      ),
                      "parse_mode": "HTML",
                  },
              )
              conn.close()
              return {"ok": True}

            keyboard = {
                "inline_keyboard": [
                    [{"text": f"📍 {d}", "callback_data": f"dist_{d}"}]
                    for d in districts
                ]
            }
            await client.post(
                f"{api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        f"Город: <b>{selected_city}</b>. Выберите район:"
                    ),
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
            )

          # 2. Выбор района -> Показ категорий
          elif callback_data.startswith("dist_"):
            selected_district = callback_data.replace("dist_", "").strip()
            cursor.execute("SELECT name FROM categories")
            categories = [row[0] for row in cursor.fetchall()]

            if not categories:
              await client.post(
                  f"{api_url}/sendMessage",
                  json={
                      "chat_id": chat_id,
                      "text": "⚠️ Категории товаров не настроены в админке.",
                  },
              )
              conn.close()
              return {"ok": True}

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": f"📂 {cat}",
                            "callback_data": f"cat_{selected_district}_{cat}",
                        }
                    ]
                    for cat in categories
                ]
            }
            await client.post(
                f"{api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        f"Район: <b>{selected_district}</b>. Выберите категорию:"
                    ),
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
            )

          # 3. Выбор категории -> Показ товаров, добавленных в админке
          elif callback_data.startswith("cat_"):
            parts = callback_data.replace("cat_", "").split("_", 1)
            if len(parts) < 2:
              conn.close()
              return {"ok": True}

            selected_district = parts[0]
            selected_cat = parts[1]

            cursor.execute(
                "SELECT name, price FROM products WHERE district = ? AND"
                " category = ?",
                (selected_district, selected_cat),
            )
            products = cursor.fetchall()

            if not products:
              await client.post(
                  f"{api_url}/sendMessage",
                  json={
                      "chat_id": chat_id,
                      "text": (
                          f"📦 В этой категории для района"
                          f" <b>{selected_district}</b> пока нет товаров."
                      ),
                      "parse_mode": "HTML",
                  },
              )
              conn.close()
              return {"ok": True}

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": f"📦 {p[0]} — ${p[1]}",
                            "callback_data": f"buy_{p[0]}",
                        }
                    ]
                    for p in products
                ]
            }
            await client.post(
                f"{api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        f"Категория: <b>{selected_cat}</b>. Выберите товар:"
                    ),
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
            )

          # 4. Покупка / выдача товара
          elif callback_data.startswith("buy_"):
            prod_name = callback_data.replace("buy_", "").strip()
            cursor.execute(
                "SELECT name, product_link, photo_link FROM products WHERE"
                " name = ?",
                (prod_name,),
            )
            product = cursor.fetchone()

            if product:
              onetime_msg = get_config("onetime_msg")
              delivery_text = (
                  f"{onetime_msg}\n\n<b>{product[0]}</b>\n"
              )
              if product[1]:
                delivery_text += f"🔗 Ссылка: {product[1]}"

              if product[2]:
                await client.post(
                    f"{api_url}/sendPhoto",
                    json={
                        "chat_id": chat_id,
                        "photo": product[2],
                        "caption": delivery_text,
                        "parse_mode": "HTML",
                    },
                )
              else:
                await client.post(
                    f"{api_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": delivery_text,
                        "parse_mode": "HTML",
                    },
                )
        finally:
          conn.close()

  except Exception as e:
    print(f"Webhook error: {e}")

  return {"ok": True}


# --- Админ-панель (FastAPI маршруты) ---


@app.get("/admin", response_class=HTMLResponse)
async def admin_login_get():
  return """
    <!DOCTYPE html>
    <html lang="ru">
    <head><meta charset="UTF-8"><title>Вход в админку</title></head>
    <body style="background:#070a13; color:#fff; font-family:sans-serif; text-align:center; padding-top:100px;">
        <h2>🔐 Введите ПИН-код администратора</h2>
        <form action="/admin" method="post" style="margin-top:20px;">
            <input type="password" name="pin" placeholder="ПИН-код" required style="padding:10px; font-size:16px; border-radius:8px; border:1px solid #38bdf8; background:#0f172a; color:#fff;">
            <button type="submit" style="padding:10px 20px; font-size:16px; background:#0284c7; color:#fff; border:none; border-radius:8px; cursor:pointer;">Войти</button>
        </form>
    </body>
    </html>
    """


@app.post("/admin", response_class=HTMLResponse)
async def admin_login_post(pin: str = Form(...)):
  if pin == SECRET_PIN:
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="admin_session", value="authenticated")
    return response
  return "<h2>Неверный ПИН-код! <a href='/admin'>Назад</a></h2>"


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
  if request.cookies.get("admin_session") != "authenticated":
    return RedirectResponse(url="/admin", status_code=303)

  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute("SELECT name FROM cities")
  cities = [row[0] for row in cursor.fetchall()]
  cursor.execute("SELECT city, district FROM districts")
  districts = cursor.fetchall()
  cursor.execute("SELECT name, district, price FROM products")
  products = cursor.fetchall()
  conn.close()

  return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head><meta charset="UTF-8"><title>Админ-панель STELLA</title></head>
    <body style="background:#070a13; color:#fff; font-family:sans-serif; padding:30px;">
        <h1>🚀 Панель управления STELLA SYSTEM</h1>
        <hr style="border-color:rgba(56,189,248,0.3); margin: 20px 0;">
        
        <h3>Города (всего: {len(cities)})</h3>
        <ul>{"".join([f"<li>{c}</li>" for c in cities])}</ul>
        
        <h3>Районы (всего: {len(districts)})</h3>
        <ul>{"".join([f"<li>{d[0]} — {d[1]}</li>" for d in districts])}</ul>
        
        <h3>Товары (всего: {len(products)})</h3>
        <ul>{"".join([f"<li>{p[0]} ({p[1]}) — ${p[2]}</li>" for p in products])}</ul>
        
        <br><a href="/admin" style="color:#38bdf8;">Выйти</a>
    </body>
    </html>
    """


if __name__ == "__main__":
  uvicorn.run(app, host="127.0.0.1", port=8000)
