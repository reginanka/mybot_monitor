import os
import io
from datetime import datetime
from typing import List
import pytz
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_LOG_CHANNEL_ID = os.getenv("TELEGRAM_LOG_CHANNEL_ID")
UKRAINE_TZ = pytz.timezone("Europe/Kyiv")

log_messages: List[str] = []

def get_ukraine_time() -> datetime:
    return datetime.now().astimezone(UKRAINE_TZ)

def log_to_buffer(message: str) -> None:
    ts = get_ukraine_time().strftime("%H:%M:%S")
    line = f"{ts} - {message}"
    print(line)
    log_messages.append(line)

def send_log_to_channel() -> None:
    if not TELEGRAM_LOG_CHANNEL_ID or not TELEGRAM_BOT_TOKEN or not log_messages:
        return
    
    try:
        # Формуємо повний текст логу
        header = "📊 ЛОГ ВИКОНАННЯ СКРИПТА\n\n"
        footer = (
            f"\n\n⏰ Завершено: "
            f"{get_ukraine_time().strftime('%d.%m.%Y %H:%M:%S')} (Київський час)"
        )
        log_body = "\n".join(log_messages)
        full_text = header + f"<pre>{log_body}</pre>" + footer
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Перевіряємо розмір
        if len(full_text) <= 4000:
            # Відправляємо одним повідомленням
            data = {
                "chat_id": TELEGRAM_LOG_CHANNEL_ID,
                "text": full_text,
                "parse_mode": "HTML",
            }
            requests.post(url, data=data, timeout=10)
        else:
            # Розбиваємо на частини
            lines = log_messages
            max_chunk_size = 3800  # Залишаємо місце для header та нумерації
            current_chunk = []
            current_size = 0
            part_num = 1
            
            for line in lines:
                line_size = len(line) + 1  # +1 для \n
                
                if current_size + line_size > max_chunk_size and current_chunk:
                    # Відправляємо поточну частину
                    chunk_body = "\n".join(current_chunk)
                    chunk_text = (
                        f"{header}📋 Частина {part_num}\n\n"
                        f"<pre>{chunk_body}</pre>"
                        f"{footer}"
                    )
                    data = {
                        "chat_id": TELEGRAM_LOG_CHANNEL_ID,
                        "text": chunk_text,
                        "parse_mode": "HTML",
                    }
                    requests.post(url, data=data, timeout=10)
                    
                    # Скидаємо буфер
                    current_chunk = [line]
                    current_size = line_size
                    part_num += 1
                else:
                    current_chunk.append(line)
                    current_size += line_size
            
            # Відправляємо останню частину
            if current_chunk:
                chunk_body = "\n".join(current_chunk)
                chunk_text = (
                    f"{header}📋 Частина {part_num}\n\n"
                    f"<pre>{chunk_body}</pre>"
                    f"{footer}"
                )
                data = {
                    "chat_id": TELEGRAM_LOG_CHANNEL_ID,
                    "text": chunk_text,
                    "parse_mode": "HTML",
                }
                requests.post(url, data=data, timeout=10)
                
    except Exception as e:
        # Логуємо помилку в консоль, але не падаємо
        print(f"❌ Помилка відправки логу в Telegram: {e}")
