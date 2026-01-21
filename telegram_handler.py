import os
import logging
from pathlib import Path
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')


async def send_message(message: str, channel_id: str = TELEGRAM_CHANNEL_ID) -> bool:
    """Відправити текстове повідомлення"""
    if not TELEGRAM_BOT_TOKEN or not channel_id:
        logger.error("❌ TELEGRAM_BOT_TOKEN або TELEGRAM_CHANNEL_ID не налаштовані")
        return False
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode="HTML"
        )
        logger.info("✓ Повідомлення відправлено в Telegram")
        return True
    except TelegramError as e:
        logger.error(f"❌ Помилка Telegram: {e}")
        return False


async def send_photo(image_path: Path, caption: str = None, 
                    channel_id: str = TELEGRAM_CHANNEL_ID) -> bool:
    """Відправити картинку"""
    if not TELEGRAM_BOT_TOKEN or not channel_id:
        logger.error("❌ Telegram не налаштований")
        return False
    
    if not image_path or not image_path.exists():
        logger.warning(f"⚠️  Картинка не знайдена: {image_path}")
        return False
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        with open(image_path, 'rb') as f:
            await bot.send_photo(
                chat_id=channel_id,
                photo=f,
                caption=caption,
                parse_mode="HTML"
            )
        logger.info(f"✓ Картинка відправлена: {image_path.name}")
        return True
    except TelegramError as e:
        logger.error(f"❌ Помилка картинки: {e}")
        return False


def send_notification(message: str, image_path: Path = None) -> bool:
    """
    Синхронна обгортка для відправлення.
    Якщо є картинка — шле повідомлення З картинкою (без дублювання).
    Якщо нема картинки — шле просто текст.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if image_path and image_path.exists():
                # Шле тільки картинку з caption (одне повідомлення)
                loop.run_until_complete(send_photo(image_path, caption=message))
            else:
                # Шле тільки текст
                loop.run_until_complete(send_message(message))
            
            return True
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"❌ Помилка відправлення: {e}")
        return False
