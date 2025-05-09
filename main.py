import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID"))

PRODUCTS = {
    "gold120": {"name": "120 Gold", "price": 20},
    "gold250": {"name": "250 Gold", "price": 40},
    "vipPass": {"name": "VIP Pass", "price": 15}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cart"] = []
    keyboard = [[InlineKeyboardButton(p["name"], callback_data=key)] for key, p in PRODUCTS.items()]
    keyboard.append([InlineKeyboardButton("🛒 View Cart & Checkout", callback_data="checkout")])
    await update.message.reply_text("🛍️ Product Catalog:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "checkout":
        cart = context.user_data.get("cart", [])
        if not cart:
            await query.edit_message_text("🛒 Your cart is empty.")
            return

        total = sum(PRODUCTS[item]["price"] for item in cart)
        summary = "\n".join([f"- {PRODUCTS[i]['name']} (${PRODUCTS[i]['price']})" for i in cart])
        await query.edit_message_text(
            f"🧾 Order Summary:\n{summary}\n\n💰 Total: ${total}\n\n"
            "📩 Please PayNow to *9123XXXX*, then send a *screenshot*.\n"
            "_After that, enter your login + password._",
            parse_mode='Markdown'
        )
        context.user_data["awaiting_payment"] = True
    else:
        context.user_data.setdefault("cart", []).append(data)
        await query.edit_message_text(f"✅ Added {PRODUCTS[data]['name']} to cart. Use /start to add more.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_payment"):
        await update.message.reply_text("Please checkout first by using /start.")
        return
    context.user_data["screenshot"] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Screenshot received. Now send your login info in this format:\n\n`Login / Password / IGN`", parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "screenshot" not in context.user_data:
        await update.message.reply_text("Please upload your screenshot first.")
        return

    login_info = update.message.text
    cart = context.user_data.get("cart", [])
    screenshot_id = context.user_data["screenshot"]
    summary = "\n".join([f"- {PRODUCTS[i]['name']} (${PRODUCTS[i]['price']})" for i in cart])
    total = sum(PRODUCTS[i]['price'] for i in cart)

    caption = (
        f"🛒 *New Order Received*\n\n"
        f"{summary}\n\n"
        f"💰 *Total*: ${total}\n\n"
        f"🔐 *Login Info*: {login_info}\n"
        f"👤 From: @{update.message.from_user.username or update.message.from_user.id}"
    )

    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=screenshot_id, caption=caption, parse_mode='Markdown')
    await update.message.reply_text("🎉 Order submitted! We'll process it soon.")
    context.user_data.clear()

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_selection))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot running...")
    app.run_polling()

