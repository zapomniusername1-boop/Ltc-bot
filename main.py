import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

TOKEN = "ТВОЙ_ТОКЕН_БОТА"
DB_NAME = "database.db"  # Твоя база данных SQLite, куда админка сохраняет данные

router = Router()


class OrderState(StatesGroup):
  choosing_district = State()
  viewing_product = State()


# Вспомогательная функция для работы с SQLite (куда пишет твоя админка)
def get_db_connection():
  conn = sqlite3.connect(DB_NAME)
  conn.row_factory = sqlite3.Row
  return conn


# Шаг 1: Старт и кнопка города
@router.message(Command("start"))
async def cmd_start(message: Message):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[[InlineKeyboardButton(text="🏙 Бельцы", callback_data="city_beltsy")]]
  )
  await message.answer("Добро пожаловать в STELLA SYSTEM!\nВыберите город для покупки:", reply_markup=keyboard)


# Шаг 2: После нажатия «Бельцы» подтягиваем районы из базы (которые ты создал в админке)
@router.callback_query(F.data == "city_beltsy")
async def process_city(callback: CallbackQuery, state: FSMContext):
  conn = get_db_connection()
  cursor = conn.cursor()

  # Достаем районы из базы (предполагается таблица districts, привязанная к Бельцам)
  cursor.execute(
      "SELECT id, name FROM districts WHERE city_id = (SELECT id FROM cities WHERE name = 'Бельцы')"
  )
  districts = cursor.fetchall()
  conn.close()

  if not districts:
    # Запасной вариант, если из админки еще ничего не добавили
    await callback.message.edit_text("В городе Бельцы пока нет добавленных районов в админ-панели.")
    await callback.answer()
    return

  # Динамически создаем кнопки из админки
  keyboard_districts = InlineKeyboardMarkup(
      inline_keyboard=[[InlineKeyboardButton(text=row["name"], callback_data=f"dist_{row['id']}")] for row in districts]
  )

  await callback.message.edit_text(
      "Вы выбрали: **Бельцы**\nТеперь выберите район:", reply_markup=keyboard_districts, parse_mode="Markdown"
  )
  await state.set_state(OrderState.choosing_district)
  await callback.answer()


# Шаг 3: После выбора района подтягиваем товары из базы (которые ты добавил в админке)
@router.callback_query(OrderState.choosing_district, F.data.startswith("dist_"))
async def process_district(callback: CallbackQuery, state: FSMContext):
  district_id = callback.data.split("_")[1]

  conn = get_db_connection()
  cursor = conn.cursor()

  # Достаем товары для конкретного района из базы данных админки
  cursor.execute("SELECT id, title, price FROM products WHERE district_id = ?", (district_id,))
  products = cursor.fetchall()
  conn.close()

  if not products:
    await callback.message.edit_text("В этом районе пока нет доступных товаров.")
    await callback.answer()
    return

  # Создаем кнопки с товарами и ценами из админки
  keyboard_products = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text=f"{row['title']} — {row['price']} лей", callback_data=f"prod_{row['id']}")]
          for row in products
      ]
  )

  await callback.message.edit_text(
      "Выберите товар из списка:", reply_markup=keyboard_products, parse_mode="Markdown"
  )
  await state.set_state(OrderState.viewing_product)
  await callback.answer()


# Шаг 4: Выбор конкретного товара
@router.callback_query(OrderState.viewing_product, F.data.startswith("prod_"))
async def process_product(callback: CallbackQuery, state: FSMContext):
  product_id = callback.data.split("_")[1]

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT title, description, price FROM products WHERE id = ?", (product_id,))
  product = cursor.fetchone()
  conn.close()

  if product:
    await callback.message.edit_text(
        f"✅ Вы выбрали товар:\n\n**{product['title']}**\nОписание: {product['description']}\nЦена: {product['price']} лей\n\nПереходим к оплате..."
    )
  else:
    await callback.message.edit_text("Товар не найден.")

  await state.clear()
  await callback.answer()


async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(router)
  print("Бот успешно запущен и подключен к базе админки!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
