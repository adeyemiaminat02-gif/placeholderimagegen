import os
import re
import io
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw

# Enable basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fallback token for local testing (Never commit your production token!)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_LOCAL_TEST_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a greeting when /start is issued."""
    await update.message.reply_text(
        "👋 Welcome! Send me dimensions like *300x200* or *600 400*, "
        "and I will generate a placeholder image for you!",
        parse_mode="Markdown"
    )

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
        # (Using a simple bounding box calculation fallback for basic system fonts)
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
    if not TOKEN or TOKEN == "YOUR_LOCAL_TEST_TOKEN":
        logger.error("No valid TELEGRAM_BOT_TOKEN found. Exiting.")
        return

    # Build the application container
    app = Application.builder().token(TOKEN).build()

    # Bind handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_placeholder))

    # Run the continuous execution loop (Ideal for Render Background Workers)
    logger.info("Bot started successfully. Listening for updates...")
    app.run_polling()

if __name__ == "__main__":
    main()
