import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time

# ---------------- Логи ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Переменные ----------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
RENDER_URL = "https://tg-bot-info.onrender.com"  # ЗАМЕНИТЕ на ваш реальный URL

# ---------------- Команда /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "Привет! Все работает нормально."
    )
    await update.message.reply_text(welcome_text)

# ---------------- Инициализация приложения ----------------
telegram_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global telegram_app
    
    try:
        # Инициализируем Telegram приложение
        telegram_app = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики
        telegram_app.add_handler(CommandHandler("start", start))
        
        # Инициализируем
        await telegram_app.initialize()
        
        # Настраиваем вебхук
        webhook_url = f"{RENDER_URL}/webhook"
        await telegram_app.bot.set_webhook(webhook_url)
        
        logger.info("Бот успешно запущен!")
        logger.info(f"Webhook установлен: {webhook_url}")
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    
    yield
    
    # Shutdown
    if telegram_app:
        await telegram_app.shutdown()

# ---------------- FastAPI ----------------
app = FastAPI(lifespan=lifespan)

# Переменная для отслеживания последнего запроса
last_request_time = 0

@app.post("/webhook")
async def webhook(request: Request):
    """Обработчик вебхуков от Telegram"""
    global last_request_time
    
    current_time = time.time()
    
    # Если сервер спал больше 10 минут, это пробуждение
    if current_time - last_request_time > 600:
        logger.info("🔄 Сервер просыпается...")
        # Даем время полностью проснуться
        import asyncio
        await asyncio.sleep(2)
    
    last_request_time = current_time
    
    if telegram_app is None:
        logger.error("Telegram application not initialized")
        return {"status": "error", "message": "Application not initialized"}
    
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        
        # Обрабатываем обновление
        await telegram_app.process_update(update)
        
        logger.info(f"✅ Обработан запрос от пользователя {update.effective_user.id if update.effective_user else 'unknown'}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка в webhook: {e}")
        # Возвращаем 200 OK чтобы Telegram не считал запрос неудачным
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


