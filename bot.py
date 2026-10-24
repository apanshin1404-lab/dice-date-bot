import asyncio
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery,
    InlineQueryResultPhoto, InputMediaAnimation, InputMediaPhoto, Message,
)

import dice_art
from content import DATES

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", "10000"))
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
DICE_FACES = "⚀⚁⚂⚃⚄⚅"


def asset(name: str) -> str:
    return f"{BASE_URL}/static/{name}"


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


# ---------- inline-режим (в вашем личном чате через @бот): крутим свою картинку ----------

async def roll_inline(bot: Bot, imid: str, caption: str, markup: InlineKeyboardMarkup) -> None:
    """Показывает крутящийся кубик, потом выпавшую грань с подписью."""
    await bot.edit_message_media(
        InputMediaAnimation(media=asset("dice.gif"), caption="🎲 Кубик крутится..."),
        inline_message_id=imid,
    )
    await asyncio.sleep(2.5)
    value = random.randint(1, 6)
    await bot.edit_message_media(
        InputMediaPhoto(media=asset(f"face{value}.png"), caption=caption(value), parse_mode="HTML"),
        inline_message_id=imid, reply_markup=markup(value),
    )


def setup(dp: Dispatcher, bot: Bot) -> None:

    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer(START_TEXT, reply_markup=kb("🎲 Кинуть кубик", "roll:date"))

    @dp.inline_query()
    async def inline(q: InlineQuery):
        await q.answer(
            [InlineQueryResultPhoto(
                id="dice",
                photo_url=asset("cover.png"), thumbnail_url=asset("cover.png"),
                photo_width=512, photo_height=512,
                title="🎲 Кубик свиданий",
                description="Кидай кубик, он решит, куда идём",
                caption=START_TEXT, parse_mode="HTML",
                reply_markup=kb("🎲 Кинуть кубик", "roll:date"),
            )],
            cache_time=0, is_personal=True,
        )

    @dp.callback_query(F.data == "roll:date")
    async def on_roll_date(c: CallbackQuery):
        await c.answer()
        if c.inline_message_id:
            await roll_inline(bot, c.inline_message_id, date_text,
                              lambda d: kb("🎲 Кинуть за формат", f"roll:fmt:{d}"))
        else:
            await c.message.edit_reply_markup(reply_markup=None)
            d = await roll_real(bot, c.message.chat.id)
            await c.message.answer(date_text(d), reply_markup=kb("🎲 Кинуть за формат", f"roll:fmt:{d}"))

    @dp.callback_query(F.data.startswith("roll:fmt:"))
    async def on_roll_fmt(c: CallbackQuery):
        await c.answer()
        d = int(c.data.split(":")[2])
        if c.inline_message_id:
            await roll_inline(bot, c.inline_message_id, lambda f: final_text(d, f),
                              lambda f: kb("🔁 Сыграть ещё раз", "roll:date"))
        else:
            await c.message.edit_reply_markup(reply_markup=None)
            f = await roll_real(bot, c.message.chat.id)
            await c.message.answer(final_text(d, f), reply_markup=kb("🔁 Сыграть ещё раз", "roll:date"))


async def health_server():
    # Хостинги вроде Render ждут открытый порт, иначе считают сервис мёртвым.
    # Заодно раздаём картинки кубика, Telegram забирает их по ссылке.
    from aiohttp import web
    dice_art.build(ASSETS)
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="ok"))
    app.router.add_static("/static/", ASSETS)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()


async def keep_awake():
    # Бесплатный Render усыпляет сервис без запросов. Раз в 10 минут дёргаем сами себя.
    import aiohttp
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        await asyncio.sleep(600)
        try:
            async with aiohttp.ClientSession() as s:
                await s.get(url, timeout=aiohttp.ClientTimeout(total=20))
        except Exception:
            pass


async def main():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    setup(dp, bot)
    await health_server()
    asyncio.create_task(keep_awake())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
