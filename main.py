import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Переменная для хранения ПИН-кода
SECRET_PIN = "7777"

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STELLA SYSTEM - ACCESS PORTAL</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
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
        .header-title {
            text-align: center;
            margin-bottom: 20px;
        }
        .header-title h1 {
            font-size: 16px;
            letter-spacing: 4px;
            color: #e2e8f0;
            font-weight: 500;
        }
        .header-title p {
            font-size: 10px;
            letter-spacing: 2px;
            color: #64748b;
            margin-top: 4px;
        }
        .card { 
            background: rgba(15, 23, 42, 0.65); 
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 20px; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 360px; 
            box-shadow: 0 0 30px rgba(14, 165, 233, 0.15), inset 0 0 15px rgba(56, 189, 248, 0.05); 
        }
        .banner-img {
            width: 100%;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            display: block;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .input-group {
            position: relative;
            margin-bottom: 14px;
        }
        .input-group svg {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            width: 18px;
            height: 18px;
            stroke: #94a3b8;
            fill: none;
        }
        input { 
            width: 100%; 
            padding: 14px 14px 14px 44px; 
            border-radius: 10px; 
            border: 1px solid rgba(148, 163, 184, 0.2); 
            background: rgba(15, 23, 42, 0.8); 
            color: #fff; 
            font-size: 15px;
            outline: none;
            transition: all 0.3s ease;
        }
        input:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
        }
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
            transition: all 0.3s ease;
        }
        button:active {
            transform: scale(0.98);
        }
        .forgot-pass {
            display: block;
            text-align: center;
            margin-top: 18px;
            color: #94a3b8;
            font-size: 13px;
            text-decoration: underline;
            transition: color 0.2s;
        }
        .forgot-pass:hover {
            color: #38bdf8;
        }
    </style>
</head>
<body>

    <div class="header-title">
        <h1>STELLA SYSTEM</h1>
        <p>ACCESS PORTAL</p>
    </div>

    <div class="card">
        <!-- Космический баннер STELLA -->
        <img
