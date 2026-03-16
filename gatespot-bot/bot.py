import os
import logging
import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8743684831:AAHVgIwKDCF8Xp-V_ixeYZJlgbR5dqYwTD4")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL", "")

TYPE, APPARTEMENT, CATEGORIE, DESCRIPTION, MONTANT = range(5)

APPARTEMENTS = {
    "Casablanca": ["Anfa City", "Anfa 212", "Tour 33", "Gauthier"],
    "Rabat": ["Souissi", "Agdal"]
}

VILLES = {
    "Anfa City": "Casablanca",
    "Anfa 212": "Casablanca",
    "Tour 33": "Casablanca",
    "Gauthier": "Casablanca",
    "Souissi": "Rabat",
    "Agdal": "Rabat"
}

CATEGORIES_DEPENSE = ["Maintenance", "Électricité", "Eau", "Consommables", "Ménage", "Autre"]
CATEGORIES_REVENU = ["Airbnb", "Cash"]

user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💸 Dépense", callback_data="type_depense"),
         InlineKeyboardButton("💰 Revenu", callback_data="type_revenu")]
    ]
    await update.message.reply_text(
        "🏠 *Gatespot Bot*\n\nQue veux-tu enregistrer ?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TYPE

async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data_store[user_id] = {"type": query.data.replace("type_", "")}

    keyboard = []
    for ville, apparts in APPARTEMENTS.items():
        keyboard.append([InlineKeyboardButton(f"📍 {ville}", callback_data=f"ville_{ville}")])
        row = []
        for appart in apparts:
            row.append(InlineKeyboardButton(appart, callback_data=f"appart_{appart}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

    type_label = "dépense" if user_data_store[user_id]["type"] == "depense" else "revenu"
    await query.edit_message_text(
        f"🏠 {type_label.capitalize()} — Quel appartement ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return APPARTEMENT

async def appartement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("ville_"):
        return APPARTEMENT

    user_id = query.from_user.id
    appart = query.data.replace("appart_", "")
    user_data_store[user_id]["appartement"] = appart
    user_data_store[user_id]["ville"] = VILLES[appart]

    type_op = user_data_store[user_id]["type"]
    categories = CATEGORIES_DEPENSE if type_op == "depense" else CATEGORIES_REVENU

    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await query.edit_message_text(
        f"📂 *{appart}* — Catégorie ?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CATEGORIE

async def categorie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data_store[user_id]["categorie"] = query.data.replace("cat_", "")

    appart = user_data_store[user_id]["appartement"]
    cat = user_data_store[user_id]["categorie"]

    await query.edit_message_text(
        f"📝 *{appart}* — {cat}\n\nDécris en quelques mots :\n(ex: réparation clim, capsules nespresso, nuit du 15 mars...)",
        parse_mode="Markdown"
    )
    return DESCRIPTION

async def description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id]["description"] = update.message.text.strip()

    appart = user_data_store[user_id]["appartement"]
    cat = user_data_store[user_id]["categorie"]
    desc = user_data_store[user_id]["description"]

    await update.message.reply_text(
        f"💰 *{appart}* — {cat} — {desc}\n\nMontant en DH ?",
        parse_mode="Markdown"
    )
    return MONTANT

async def montant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    montant = update.message.text.strip().replace(",", ".")

    if not montant.replace(".", "").isdigit():
        await update.message.reply_text("⚠️ Montant invalide ! Tape un nombre (ex: 500)")
        return MONTANT

    user_data_store[user_id]["montant"] = montant
    return await enregistrer(update, user_id)

async def enregistrer(update, user_id):
    data = user_data_store.get(user_id, {})
    type_op = data.get("type")

    payload = {
        "date": str(datetime.date.today()),
        "appartement": data.get("appartement"),
        "ville": data.get("ville"),
        "categorie": data.get("categorie"),
        "montant": data.get("montant"),
        "notes": data.get("description"),
        "type": type_op
    }

    emoji = "💸" if type_op == "depense" else "💰"

    if MAKE_WEBHOOK_URL:
        try:
            requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=10)
            status = "✅ Enregistré dans Google Sheets !"
        except:
            status = "⚠️ Erreur d'envoi vers Google Sheets"
    else:
        status = "⚠️ Webhook Make non configuré"

    message = (
        f"{emoji} *{type_op.capitalize()} enregistrée !*\n\n"
        f"🏠 {data.get('appartement')} ({data.get('ville')})\n"
        f"📂 {data.get('categorie')}\n"
        f"📝 {data.get('description')}\n"
        f"💰 {data.get('montant')} DH\n\n"
        f"{status}"
    )

    keyboard = [[InlineKeyboardButton("➕ Nouvelle saisie", callback_data="restart")]]

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    user_data_store.pop(user_id, None)
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💸 Dépense", callback_data="type_depense"),
         InlineKeyboardButton("💰 Revenu", callback_data="type_revenu")]
    ]
    await query.edit_message_text(
        "🏠 *Gatespot Bot*\n\nQue veux-tu enregistrer ?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TYPE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Annulé. Tape /start pour recommencer.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(restart, pattern="^restart$")
        ],
        states={
            TYPE: [CallbackQueryHandler(type_handler, pattern="^type_")],
            APPARTEMENT: [
                CallbackQueryHandler(appartement_handler, pattern="^appart_"),
                CallbackQueryHandler(appartement_handler, pattern="^ville_")
            ],
            CATEGORIE: [CallbackQueryHandler(categorie_handler, pattern="^cat_")],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_handler)],
            MONTANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, montant_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    app.add_handler(conv_handler)
    print("🤖 Gatespot Bot démarré !")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
