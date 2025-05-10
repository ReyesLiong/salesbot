import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID"))

CATEGORIES = {
    "Pokemon TCG Pocket": [
        ("gold120", "120 Gold = $20"),
        ("gold250", "250 Gold = $40"),
        ("gold690", "690 Gold = $85"),
        ("gold2x690", "2x 690 Gold = $165"),
        ("gold3x690", "3x 690 Gold = $245"),
        ("gold5x690", "5x 690 Gold = $395"),
        ("lilliePack", "Lillie Accessories Pack = $25"),
        ("pokecombo", "All 3 Reduced Price Pokegold Sets = $16")
    ],
    "Brawl Stars": [
        ("bs360", "360 💎 = $24"),
        ("bs950", "950 💎 = $57"),
        ("bs2000", "2000 💎 = $114"),
        ("brawlpass", "Brawl Pass = $8.99"),
        ("brawlpassplus", "Brawl Pass Plus = $11.99"),
        ("propass", "Pro Pass = $29.99")
    ],
    "Clash of Clans/Clash Royale": [
        ("coc2500", "2500 💎 = $24"),
        ("coc6500", "6500 💎 = $57"),
        ("coc14000", "14000 💎 = $114"),
        ("goldpass", "[CoC] Gold Pass = $8.99"),
        ("diamondpass", "[CR] Diamond Pass = $13.99")
    ],
    "Pokemon GO": [
        ("pg15500", "🪙 15500 Coins = $48"),
        ("pg31000", "🪙 31000 Coins = $94"),
        ("pg46500", "🪙 46500 Coins = $135"),
        ("pgcandy1", "🍬 Candy (Non-Legendary) = $9"),
        ("pgcandy2", "🍬 Candy (Legendary) = $14"),
        ("pg30raids", "🎫 30 Raids = $14"),
        ("pg50raids", "🎫 50 Raids = $20"),
        ("pg100raids", "🎫 100 Raids = $35"),
        ("pg1mDust", "🌟 1M Stardust = $20"),
        ("pg2mDust", "🌟 2M Stardust = $39"),
        ("pg2_5mXP", "❇️ 2.5M XP = $6"),
        ("pg20mXP", "❇️ 20M XP = $30"),
        ("pg176mXP", "❇️ 176M XP = $220"),
        ("pgLevel40", "⭐ LEVEL 40 Fresh Account = $15")
    ]
}

CATEGORY_LIST = list(CATEGORIES.keys())
PRODUCT_LOOKUP = {item_id: name for cat in CATEGORIES.values() for item_id, name in cat}
PRICES = {item_id: float(name.split('= $')[-1]) for item_id, name in PRODUCT_LOOKUP.items()}

USER_CARTS = {}
USER_STATE = {}
USER_SCREENSHOT = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in CATEGORY_LIST]
    keyboard.append([InlineKeyboardButton("🛒 View Cart & Checkout", callback_data="checkout")])
    USER_CARTS[update.effective_user.id] = []
    await update.message.reply_text("🛍️ Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("cat_"):
        category = data[4:]
        keyboard = [
            [InlineKeyboardButton(PRODUCT_LOOKUP[item_id], callback_data=f"add_{item_id}")]
            for item_id, _ in CATEGORIES[category]
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back")])
        await query.edit_message_text(f"📦 {category} Products:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("add_"):
        item = data[4:]
        cart = USER_CARTS.setdefault(user_id, [])
        cart.append(item)

        # Find the category it came from
        category = None
        for cat, items in CATEGORIES.items():
            if any(i == item for i, _ in items):
                category = cat
                break

        # Rebuild keyboard for the same category
        if category:
            keyboard = [
                [InlineKeyboardButton(PRODUCT_LOOKUP[item_id], callback_data=f"add_{item_id}")]
                for item_id, _ in CATEGORIES[category]
            ]
            keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back")])
            await query.edit_message_text(
                f"✅ Added {PRODUCT_LOOKUP[item]} to cart.\n\n📦 {category} Products:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data == "checkout":
        cart = USER_CARTS.get(user_id, [])
        if not cart:
            await query.edit_message_text("🛒 Your cart is empty.")
            return
        summary = "\n".join([f"- {PRODUCT_LOOKUP[i]} (${PRICES[i]})" for i in cart])
        total = sum(PRICES[i] for i in cart)
        remove_buttons = [[InlineKeyboardButton(f"❌ Remove {PRODUCT_LOOKUP[i]}", callback_data=f"remove_{idx}")]
                          for idx, i in enumerate(cart)]
        remove_buttons.append([InlineKeyboardButton("✅ Proceed to Payment", callback_data="pay")])
        await query.edit_message_text(
            f"🧾 Order Summary:\n{summary}\n\n💰 Total: ${total}",
            reply_markup=InlineKeyboardMarkup(remove_buttons)
        )

    elif data.startswith("remove_"):
        idx = int(data.split("_")[1])
        cart = USER_CARTS.get(user_id, [])
        if 0 <= idx < len(cart):
            removed = cart.pop(idx)
            await query.edit_message_text(f"❌ Removed {PRODUCT_LOOKUP[removed]} from your cart. Use /start to continue shopping.")

    elif data == "pay":
        USER_STATE[user_id] = "awaiting_payment"
        await query.edit_message_text(
            "💵 Please PayNow to *9123XXXX* and send a screenshot here.\nAfter that, you'll be asked for login details.",
            parse_mode='Markdown'
        )

    elif data == "back":
        await start(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if USER_STATE.get(user_id) == "awaiting_payment":
        USER_SCREENSHOT[user_id] = update.message.photo[-1].file_id
        USER_STATE[user_id] = "awaiting_login"
        cart = USER_CARTS.get(user_id, [])
        prompt = ""
        if any(i.startswith("pg") for i in cart):
            prompt = "\n\nPlease enter your Pokemon Trainer Club login info:\n- Username\n- Password"
        elif any(i.startswith("bs") or i.startswith("coc") for i in cart):
            prompt = "\n\nPlease enter your Supercell login email."
        elif any(i.startswith("gold") or i == "lilliePack" or i == "pokecombo" for i in cart):
            prompt = "\n\nPlease provide the following for Pokémon TCG Pocket:\n- Login type (Nintendo or Google)\n- Email / Sign-in ID\n- Password\n- In-game Name"
        await update.message.reply_text("✅ Screenshot received." + prompt)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if USER_STATE.get(user_id) != "awaiting_login":
        return
    login_info = update.message.text
    cart = USER_CARTS.get(user_id, [])
    screenshot_id = USER_SCREENSHOT.get(user_id)
    summary = "\n".join([f"- {PRODUCT_LOOKUP[i]} (${PRICES[i]})" for i in cart])
    total = sum(PRICES[i] for i in cart)
    caption = (
        f"🛒 *New Order Received*\n\n{summary}\n\n💰 *Total*: ${total}\n\n"
        f"🔐 *Login Info*: {login_info}\n"
        f"👤 From: @{update.message.from_user.username or update.message.from_user.id}"
    )
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=screenshot_id, caption=caption, parse_mode='Markdown')
    await update.message.reply_text("🎉 Order submitted! We'll process it soon.")
    USER_CARTS[user_id] = []
    USER_STATE.pop(user_id, None)
    USER_SCREENSHOT.pop(user_id, None)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_selection))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()
