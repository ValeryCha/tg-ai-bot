import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from groq import AsyncGroq


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

if not GROQ_API_KEY:
    raise RuntimeError("Не задан GROQ_API_KEY")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

groq_client = AsyncGroq(api_key=GROQ_API_KEY)


def split_text(text: str, limit: int = 3900):
    """
    Telegram не принимает сообщения больше ~4096 символов.
    Поэтому длинные ответы режем на части.
    """
    parts = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].strip()
    if text:
        parts.append(text)
    return parts


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет! Я AI-бот.\n\n"
        "Напиши мне любой вопрос, и я постараюсь ответить."
    )


@dp.message(F.text)
async def ai_handler(message: Message):
    user_text = message.text.strip()

    if len(user_text) > 3000:
        await message.answer("Слишком длинный запрос. Сократи его до 3000 символов.")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:
        response = await groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты полезный Telegram AI-ассистент. "
                        "Отвечай понятно, по делу, на русском языке."
                    )
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )

        answer = response.choices[0].message.content

        for part in split_text(answer):
            await message.answer(part)

    except Exception as e:
        logging.exception("Ошибка при запросе к AI")
        await message.answer(
            "Произошла ошибка при обращении к AI.\n\n"
            f"Технически: {type(e).__name__}: {e}"
        )


async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
