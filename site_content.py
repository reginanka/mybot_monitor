import os
import hashlib
from io import BytesIO
from typing import Tuple, Optional
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from PIL import Image
from log_utils import log_to_buffer

URL = os.getenv("URL")

def get_schedule_content() -> Tuple[Optional[str], Optional[str]]:
    """Повертає дату оновлення."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 3080})
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page_content = page.content()
            browser.close()
            soup = BeautifulSoup(page_content, "html.parser")
            for br in soup.find_all("br"):
                br.replace_with("\n")
            
            update_date = None
            
            for elem in soup.find_all(["div", "span", "p", "h2", "h3", "h4", "h5"]):
                text = elem.get_text(strip=False)
                if "Дата" in text and update_date is None:
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    update_date = "\n".join(lines)
                    log_to_buffer(f"✅ Знайдено дату оновлення: {update_date}")
            
            if not update_date:
                log_to_buffer("⚠️ Дата оновлення не знайдена")
            
            return None, update_date
    except Exception as e:
        log_to_buffer(f"❌ Помилка Playwright при читанні тексту: {e}")
        return None, None

def take_screenshot_between_elements() -> Tuple[Optional[str], Optional[str]]:
    """Робить скріншот: між 'Дата оновлення інформації' та 'робіт'."""
    try:
        log_to_buffer("📸 Створюю скріншот проміжку між елементами...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 3080})
            page.goto(URL, wait_until="networkidle", timeout=30000)
            date_element = page.locator("text=/Дата оновлення інформації/").first
            end_element = page.locator("text=/робіт/").last
            if date_element.count() == 0:
                log_to_buffer("❌ Не знайдено елемент 'Дата оновлення інформації'")
                browser.close()
                return None, None
            date_box = date_element.bounding_box()
            end_box = end_element.bounding_box() if end_element.count() > 0 else None
            if not date_box:
                log_to_buffer("❌ Не вдалося отримати координати 'Дата оновлення інформації'")
                browser.close()
                return None, None
            x = 0
            width = 1920
            start_y = date_box["y"] + date_box["height"]
            full_screenshot = page.screenshot()
            browser.close()
            image = Image.open(BytesIO(full_screenshot))
            if end_box:
                end_y = end_box["y"] + end_box["height"] + 5
                log_to_buffer(f"📐 Обрізка до слова 'робіт': y={start_y}-{end_y}")
            else:
                end_y = image.height
                log_to_buffer("📐 Обрізка на всю висоту сторінки (робіт не знайдено)")
            height = end_y - start_y
            if height <= 0:
                log_to_buffer("❌ Некоректна висота області для скріншота")
                return None, None
            cropped_image = image.crop((x, start_y, x + width, end_y))
            screenshot_path = "screenshot.png"
            cropped_image.save(screenshot_path)
            screenshot_hash = hashlib.md5(cropped_image.tobytes()).hexdigest()
            log_to_buffer(f"✅ Скріншот створено. Хеш: {screenshot_hash}")
            return screenshot_path, screenshot_hash
    except Exception as e:
        log_to_buffer(f"❌ Помилка створення скріншота: {e}")
        return None, None
