import os
import re
import io
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw

# Enable basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fetch token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Welcome message configuration
START_IMAGE_URL = "https://freeimage.host/i/CN86wiP"

START_CAPTION = (
    "We offer a 4% yield, with a USDT exchange rate of 109. "
    "We sell very quickly, so please click the link below to join.\n\n"
    "App registration address:\n"
    "https://example.com/register\n\n"
    "Official channel link:\n"
    "https://t.me/your_official_channel\n\n"
    "Contact me: @YourHandle"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends an image with caption when /start is issued."""
    try:
        # Send the photo directly from URL with caption attached
        await update.message.reply_photo(
            photo=START_IMAGE_URL,
            caption=START_CAPTION
        )
    except Exception as e:
        logger.error(f"Error sending start photo: {e}")
        # Fallback to plain text message if the image URL fails to load
        await update.message.reply_text(START_CAPTION)

async def generate_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses dimensions, generates an image in-memory, and replies with it."""
    text = update.message.text.strip().lower()
    
    # Matches patterns like 300x200, 300 x 200, 300 200, 300,200
    match = re.match(r"^(\d+)\s*[x\s,]\s*(\d+)$", text)
    
    if not match:
        await update.message.reply_text("❌ Please send dimensions in a format like `300x200` or `600 400`.")
        return

    width, height = int(match.group(1)), int(match.group(2))

    # Boundary safety checks for Telegram restrictions and memory guardrails
    if width < 10 or height < 10:
        await update.message.reply_text("❌ Minimum size is 10x10.")
        return
    if width > 4000 or height > 4000:
        await update.message.reply_text("❌ Maximum size is 4000x4000 to prevent server timeouts.")
        return

    await update.message.reply_chat_action("upload_photo")

    try:
        # Create a classic gray placeholder image
        img = Image.new("RGB", (width, height), color="#CCCCCC")
        draw = ImageDraw.Draw(img)
        
        # Draw a subtle border and an 'X' marking the boundaries
        draw.rectangle([0, 0, width - 1, height - 1], outline="#AAAAAA", width=2)
        draw.line([(0, 0), (width, height)], fill="#BBBBBB", width=1)
        draw.line([(0, height), (width, 0)], fill="#BBBBBB", width=1)
        
        # Render size string text
        label = f"{width} x {height}"
        
        # Calculate dynamic text placement relative to image dimensions
        text_bbox = draw.textbbox((0, 0), label)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        
        text_x = (width - text_w) // 2
        text_y = (height - text_h) // 2
        draw.text((text_x, text_y), label, fill="#555555")

        # Save to a byte stream to transmit via API without disk overhead
        bio = io.BytesIO()
        bio.name = f"placeholder_{width}x{height}.png"
        img.save(bio, "PNG")
        bio.seek(0)

        # Upload to Telegram chat
        await update.message.reply_photo(photo=bio, caption=f"🖼 Here is your {width}x{height} placeholder.")

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        await update.message.reply_text("💥 An error occurred while generating your image.")

def main() -> None:
    """Initializes and runs the bot app."""
    if not TOKEN:
        logger.error("No valid TELEGRAM_BOT_TOKEN found in environment variables. Exiting.")
        return

    # Build the application container
    app = Application.builder().token(TOKEN).build()

    # Bind handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_placeholder))

    logger.info("Bot started successfully. Listening for updates...")
    
    # Explicitly create and set a running event loop for asyncio/Python 3.14 compatibility
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the continuous long polling loop
    app.run_polling()

if __name__ == "__main__":
    main()
