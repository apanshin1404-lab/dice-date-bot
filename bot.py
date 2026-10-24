import asyncio
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent, Message,
)

from content import DATES

TOKEN = os.environ["BOT_TOKEN"]
DICE_FACES = "⚀⚁⚂⚃⚄⚅"
ANIM_FRAMES = ["🎲 Кубик катится...", "🎲 Крутится...", "🎲 Почти..."]


def kb(text: str, data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=data)]])


START_TEXT = (
    "🎲 <b>Кубик свиданий</b>\n\n"
    "Первый бросок выбирает, куда идём.\n"
    "Второй бросок выбирает, как именно.\n\n"
    "Что выпало, то и делаем. Без переигровок 😉"
)


def date_text(d: int) -> str:
    date = DATES[d - 1]
    return f"{DICE_FACES[d - 1]} Выпало <b>{d}</b>\n\n{date['emoji']} <b>{date['title']}</b>\n{date['desc']}\n\nТеперь второй бросок: как именно?"


def final_text(d: int, f: int) -> str:
    date = DATES[d - 1]
    fmt = date["formats"][f - 1]
    return (
        f"{DICE_FACES[f - 1]} Выпало <b>{f}</b>\n\n"
        f"{date['emoji']} <b>{date['title']}</b>\n"
        f"➜ <b>{fmt['title']}</b>\n{fmt['desc']}\n\n"
        f"Решено. Осталось выбрать день 📅"
    )


# ---------- обычный чат (личка с ботом или группа): настоящий кубик Telegram ----------

async def roll_real(bot: Bot, chat_id: int) -> int:
    msg = await bot.send_dice(chat_id, emoji="🎲")
    await asyncio.sleep(4)  # ждём, пока доиграет анимация
    return msg.dice.value


# ---------- inline-режим (в вашем личном чате через @бот): кубик рисуем сами ----------

async def roll_fake(bot: Bot, inline_message_id: str) -> int:
    for frame in ANIM_FRAMES:
        await bot.edit_message_text(frame, inline_message_id=inline_message_id)
        await asyncio.sleep(0.7)
    return random.randint(1, 6)


def setup(dp: Dispatcher, bot: Bot) -> None:

    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer(START_TEXT, reply_markup=kb("🎲 Кинуть кубик", "roll:date"))

    @dp.inline_query()
    async def inline(q: InlineQuery):
        await q.answer(
            [InlineQueryResultArticle(
                id="dice",
                title="🎲 Кубик свиданий",
                description="Кидай кубик, он решит, куда идём",
                input_message_content=InputTextMessageContent(message_text=START_TEXT, parse_mode="HTML"),
                reply_markup=kb("🎲 Кинуть кубик", "roll:date"),
            )],
            cache_time=0, is_personal=True,
        )

    @dp.callback_query(F.data == "roll:date")
    async def on_roll_date(c: CallbackQuery):
        await c.answer()
        if c.inline_message_id:
            d = await roll_fake(bot, c.inline_message_id)
            await bot.edit_message_text(date_text(d), inline_message_id=c.inline_message_id,
                                        reply_markup=kb("🎲 Кинуть за формат", f"roll:fmt:{d}"))
        else:
            await c.message.edit_reply_markup(reply_markup=None)
            d = await roll_real(bot, c.message.chat.id)
            await c.message.answer(date_text(d), reply_markup=kb("🎲 Кинуть за формат", f"roll:fmt:{d}"))

    @dp.callback_query(F.data.startswith("roll:fmt:"))
    async def on_roll_fmt(c: CallbackQuery):
        await c.answer()
        d = int(c.data.split(":")[2])
        if c.inline_message_id:
            f = await roll_fake(bot, c.inline_message_id)
            await bot.edit_message_text(final_text(d, f), inline_message_id=c.inline_message_id,
                                        reply_markup=kb("🔁 Сыграть ещё раз", "roll:date"))
        else:
            await c.message.edit_reply_markup(reply_markup=None)
            f = await roll_real(bot, c.message.chat.id)
            await c.message.answer(final_text(d, f), reply_markup=kb("🔁 Сыграть ещё раз", "roll:date"))


async def health_server():
    # Хостинги вроде Render ждут открытый порт, иначе считают сервис мёртвым.
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", "10000"))).start()


async def main():
    bot = Bot(TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    setup(dp, bot)
    await health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
