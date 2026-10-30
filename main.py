import asyncio
import logging
import uuid
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Вставь свой токен от BotFather вместо 'ТВОЙ_БОТ_ТОКЕН' в кавычках!
BOT_TOKEN = "9066444400:AAHED7ZPbwpWRX07tkaMDM8v1nw-agfhPWA"

logging.basicConfig(level=logging.INFO)
router = Router()

USERS_DB = {}
PRODUCTS = {
    "1": {"name": "📂 Цифровой гайд / Товар #1", "price_ltc": 0.05},
    "2": {"name": "🔑 Доступ к каналу / Товар #2", "price_ltc": 0.12},
}


@router.message(CommandStart())
async def cmd_start(message: Message):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛍 Каталог товаров", callback_data="catalog"
              )
          ],
          [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
      ]
  )
  await message.answer(
      "👋 **Добро пожаловать в магазин!**\n\nВыбери нужный раздел в меню ниже:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
  buttons = []
  for p_id, p_info in PRODUCTS.items():
    buttons.append([
        InlineKeyboardButton(
            text=f"{p_info['name']} — {p_info['price_ltc']} LTC",
            callback_data=f"buy_{p_id}",
        )
    ])

  buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")])
  keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

  await callback.message.edit_text(
      "📦 **Доступные товары:**\nНажми на товар для покупки:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: CallbackQuery):
  p_id = callback.data.split("_")[1]
  product = PRODUCTS.get(p_id)

  fake_ltc_address = "LTC1Q_DEMO_ADDRESS_EXAMPLE_XYZ12345"
  order_id = str(uuid.uuid4())[:8]

  text = (
      f"🛒 **Оформление заказа #{order_id}**\n\n"
      f"Товар: *{product['name']}*\n"
      f"Сумма к оплате: `{product['price_ltc']} LTC`\n\n"
      f"📌 **Адрес для оплаты (Litecoin):**\n`{fake_ltc_address}`\n\n"
      "⚠️ *Переводите точную сумму. После подтверждения сети товар придет автоматически.*"
  )

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[[
          InlineKeyboardButton(
              text="🔄 Проверить оплату", callback_data=f"check_{order_id}"
          )
      ], [InlineKeyboardButton(text="◀️ В каталог", callback_data="catalog")]]
  )

  await callback.message.edit_text(
      text, reply_markup=keyboard, parse_mode="Markdown"
  )
  await callback.answer()


@router.callback_query(F.data == "back_home")
async def back_home(callback: CallbackQuery):
  await cmd_start(callback.message)
  await callback.answer()


async def main():
  bot = Bot(token=BOT_TOKEN)
  dp = Dispatcher()
  dp.include_router(router)

  print("Бот запущен и готов к работе!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
  
