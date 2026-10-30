import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

SECRET_PIN = "7777"

def render_login_page():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STELLA SYSTEM - ACCESS PORTAL</title>
    <style>
        :root {
            --bg-gradient: radial-gradient(circle at 50% 30%, #111a2e 0%, #050811 100%);
            --bg-color: #070a13;
            --card-bg: rgba(15, 23, 42, 0.75);
            --border-color: rgba(56, 189, 248, 0.3);
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --input-bg: rgba(15, 23, 42, 0.8);
            --input-border: rgba(148, 163, 184, 0.2);
        }
        [data-theme="light"] {
            --bg-gradient: radial-gradient(circle at 50% 30%, #e2e8f0 0%, #cbd5e1 100%);
            --bg-color: #f1f5f9;
            --card-bg: rgba(255, 255, 255, 0.85);
            --border-color: rgba(2, 132, 199, 0.3);
            --text-color: #0f172a;
            --text-muted: #64748b;
            --input-bg: rgba(255, 255, 255, 0.9);
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
        }
        .header-title { text-align: center; margin-bottom: 20px; }
        .header-title h1 { font-size: 16px; letter-spacing: 4px; font-weight: 500; }
        .header-title p { font-size: 10px; letter-spacing: 2px; color: var(--text-muted); margin-top: 4px; }
        .card { 
            background: var(--card-bg); 
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            padding: 20px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 360px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15); 
        }
        .banner-img {
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            display: block;
        }
        .input-group { position: relative; margin-bottom: 14px; }
        input { 
            width: 100%; 
            padding: 14px; 
            border-radius: 10px; 
            border: 1px solid var(--input-border); 
            background: var(--input-bg); 
            color: var(--text-color); 
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
        .theme-toggle {
            position: absolute;
            top: 20px;
            right: 20px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
        }
    </style>
</head>
<body data-theme="dark">
    <button class="theme-toggle" onclick="toggleTheme()">🌓 Тема</button>

    <div class="header-title">
        <h1>STELLA SYSTEM</h1>
        <p>ACCESS PORTAL</p>
    </div>

    <div class="card">
        <img src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=800&auto=format&fit=crop" alt="Stella Space" class="banner-img">

        <form method="POST" action="/login">
            <div class="input-group">
                <input type="text" name="username" placeholder="Логин" required>
            </div>
            
            <div class="input-group">
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            
            <button type="submit">Авторизоваться</button>
        </form>
    </div>

    <script>
        function toggleTheme() {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('stella_theme', newTheme);
        }
        const savedTheme = localStorage.getItem('stella_theme') || 'dark';
        document.body.setAttribute('data-theme', savedTheme);
    </script>
</body>
</html>"""

def render_admin_page
