import os
import json
import secrets
import string
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, \
    PreCheckoutQueryHandler
import logging
import threading

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8987437321:AAGa9oXg__-xTX3ii7RnH2azoPvMO4tfoFI")
IMAGE_PATH = "mil8kavpn.png"

USER_DATA_FILE = "users_data.json"
VPN_LINKS_FILE = "vpn_links.json"
PENDING_REQUESTS_FILE = "pending_requests.json"

# Цена премиума в звездах (Telegram Stars)
PREMIUM_PRICE_ADMIN = 1
PREMIUM_PRICE_USER = 100

# Список админов
ADMINS = {
    "admin",
    "mil8kavpn",
    "7737148018",
}

# Ссылки спонсоров
SPONSOR_LINKS = {
    "sponsor1": "https://t.me/mil8kavpn",
    "sponsor2": "https://t.me/StarsovEarnBot?start=5iOIZqTtO"
}

# Цена VPN в монетах
VPN_PRICE = 15000
VPN_PRICE_PREMIUM = 7500


# ========== РАБОТА С JSON ==========
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_vpn_code():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


# ========== ПРОВЕРКА АДМИНА ==========
def is_admin(user):
    if not user:
        return False
    if user.username and user.username.lower() in ADMINS:
        return True
    if str(user.id) in ADMINS:
        return True
    return False


def get_user_price(user):
    if is_admin(user):
        return PREMIUM_PRICE_ADMIN
    return PREMIUM_PRICE_USER


def get_user_price_display(user):
    if is_admin(user):
        return "1 ⭐"
    return "100 ⭐"


# ========== РАДУЖНЫЙ НИК ==========
def rainbow_text(text):
    colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣']
    result = []
    for i, char in enumerate(text):
        color = colors[i % len(colors)]
        result.append(f"{color}{char}")
    return ''.join(result)


# ========== ОТПРАВКА С КАРТИНКОЙ ==========
async def send_with_image(update, context, text, reply_markup=None, parse_mode='Markdown'):
    try:
        if os.path.exists(IMAGE_PATH):
            with open(IMAGE_PATH, 'rb') as photo:
                if hasattr(update, 'callback_query') and update.callback_query:
                    try:
                        await update.callback_query.message.delete()
                    except:
                        pass
                    await context.bot.send_photo(
                        chat_id=update.callback_query.message.chat_id,
                        photo=photo,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
        else:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
    except Exception as e:
        logger.error(f"Error sending with image: {e}")
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )


# ========== ПРОВЕРКА СПОНСОРОВ ==========
def check_sponsors_required(user_data, user_id):
    if user_id not in user_data:
        return False
    if "sponsors_checked" not in user_data[user_id]:
        user_data[user_id]["sponsors_checked"] = {"sponsor1": False, "sponsor2": False}
        save_json(USER_DATA_FILE, user_data)
        return False
    sponsors = user_data[user_id]["sponsors_checked"]
    return sponsors.get("sponsor1", False) and sponsors.get("sponsor2", False)


async def require_sponsors_check(update, context):
    user_id = None
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = str(update.callback_query.from_user.id)
    elif hasattr(update, 'message') and update.message:
        user_id = str(update.message.from_user.id)
    else:
        return

    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await start(update, context)
        return

    if "sponsors_checked" not in user_data[user_id]:
        user_data[user_id]["sponsors_checked"] = {"sponsor1": False, "sponsor2": False}
        save_json(USER_DATA_FILE, user_data)

    sponsors_checked = user_data[user_id]["sponsors_checked"]

    sponsor1_text = "✅ Спонсор 1" if sponsors_checked.get("sponsor1", False) else "🤝 Спонсор 1"
    sponsor2_text = "✅ Спонсор 2" if sponsors_checked.get("sponsor2", False) else "🤝 Спонсор 2"

    keyboard = [
        [InlineKeyboardButton(sponsor1_text, callback_data="sponsor1")],
        [InlineKeyboardButton(sponsor2_text, callback_data="sponsor2")],
    ]

    if sponsors_checked.get("sponsor1", False) and sponsors_checked.get("sponsor2", False):
        keyboard.append([InlineKeyboardButton("🚀 Войти в бота", callback_data="enter_bot")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🔒 *Доступ к боту*\n\n"
        "Для использования бота необходимо подписаться на наших спонсоров:\n\n"
        "1️⃣ Нажми на кнопку *Спонсор 1* и перейди по ссылке\n"
        "2️⃣ Нажми на кнопку *Спонсор 2* и перейди по ссылке выполни два задания\n\n"
        "✅ После нажатия на обе кнопки появится кнопка *Войти в бота*"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ГЛАВНОЕ МЕНЮ ==========
async def main_menu(update, context):
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await start(update, context)
        return

    if not check_sponsors_required(user_data, user_id):
        await require_sponsors_check(update, context)
        return

    is_admin_user = is_admin(user)

    keyboard = [
        [InlineKeyboardButton("🖱️ Кликер", callback_data="clicker")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("🛒 Купить VPN", callback_data="buy_vpn_menu")],
    ]

    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🏠 *Главное меню*\n\nВыбери раздел:"
    await send_with_image(update, context, text, reply_markup)


# ========== КОМАНДА /START ==========
async def start(update, context):
    user = update.effective_user
    user_id = str(user.id)
    user_data = load_json(USER_DATA_FILE)

    ref_code = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_code = arg.replace("ref_", "")

    if user_id not in user_data:
        referral_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        user_data[user_id] = {
            "username": user.username or user.first_name,
            "first_name": user.first_name,
            "balance": 0,
            "clicks": 0,
            "referral_code": referral_code,
            "referred_by": None,
            "referrals": [],
            "vpn": None,
            "vpn_code": None,
            "premium": False,
            "premium_until": None,
            "bio": "Привет! Я в Clicker боте 🚀",
            "age": None,
            "city": None,
            "is_admin": is_admin(user),
            "created_at": datetime.now().isoformat(),
            "sponsors_checked": {"sponsor1": False, "sponsor2": False},
            "vpn_request": None,
            "vpn_active": False
        }

        if ref_code:
            for uid, uinfo in user_data.items():
                if uinfo.get("referral_code") == ref_code:
                    user_data[user_id]["referred_by"] = uid
                    user_data[uid]["referrals"].append(user_id)
                    user_data[uid]["balance"] += 20
                    user_data[user_id]["balance"] += 10
                    break

        save_json(USER_DATA_FILE, user_data)
        logger.info(f"✅ New user: {user_id} (admin: {is_admin(user)})")

    if not check_sponsors_required(user_data, user_id):
        await require_sponsors_check(update, context)
    else:
        await main_menu(update, context)


# ========== ОБРАБОТЧИК СПОНСОРОВ ==========
async def handle_sponsor(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    sponsor_key = query.data

    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    if "sponsors_checked" not in user_data[user_id]:
        user_data[user_id]["sponsors_checked"] = {"sponsor1": False, "sponsor2": False}

    if user_data[user_id]["sponsors_checked"].get(sponsor_key, False):
        await require_sponsors_check(update, context)
        return

    user_data[user_id]["sponsors_checked"][sponsor_key] = True
    user_data[user_id]["balance"] += 50

    save_json(USER_DATA_FILE, user_data)

    link = SPONSOR_LINKS.get(sponsor_key)
    sponsor_name = "Спонсор 1" if sponsor_key == "sponsor1" else "Спонсор 2"

    await require_sponsors_check(update, context)

    keyboard = [
        [InlineKeyboardButton("🔗 Перейти к спонсору", url=link)],
        [InlineKeyboardButton("🔙 Вернуться", callback_data="back_to_sponsors")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"✅ *Ты нажал на {sponsor_name}!*\n\n"
        f"💰 Ты получил +50 монет за просмотр!\n"
        f"📊 Твой баланс: {user_data[user_id]['balance']} монет\n\n"
        f"👆 Нажми на кнопку ниже, чтобы перейти к спонсору"
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ========== ВХОД В БОТА ==========
async def enter_bot(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    sponsors_checked = user_data[user_id].get("sponsors_checked", {})
    if not sponsors_checked.get("sponsor1", False) or not sponsors_checked.get("sponsor2", False):
        await require_sponsors_check(update, context)
        return

    await main_menu(update, context)


async def back_to_sponsors(update, context):
    query = update.callback_query
    await query.answer()
    await require_sponsors_check(update, context)


# ========== КЛИКЕР ==========
async def clicker_menu(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    keyboard = [
        [InlineKeyboardButton("🪙 Кликнуть!", callback_data="click")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user = user_data[user_id]
    bonus_text = "⭐ *Премиум бонус: +5 монет за клик!*" if user.get('premium') else ""
    admin_text = "👑 *Администратор*" if user.get('is_admin') else ""

    text = (
        f"🖱️ *Кликер*\n\n"
        f"{admin_text}\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"🖱️ Кликов: {user['clicks']}\n"
        f"{bonus_text}\n\n"
        f"Нажми на кнопку, чтобы заработать монету!"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ОБРАБОТЧИК КЛИКА ==========
async def handle_click(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    is_premium = user_data[user_id].get('premium', False)
    click_bonus = 5 if is_premium else 1

    user_data[user_id]["balance"] += click_bonus
    user_data[user_id]["clicks"] += 1

    referred_by = user_data[user_id].get("referred_by")
    if referred_by and referred_by in user_data:
        if user_data[user_id]["clicks"] % 10 == 0:
            user_data[referred_by]["balance"] += 2

    save_json(USER_DATA_FILE, user_data)

    keyboard = [
        [InlineKeyboardButton("🪙 Еще клик!", callback_data="click")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    premium_text = "⭐ *Премиум бонус! +5 монет!*" if is_premium else ""

    text = (
        f"✅ *+{click_bonus} монет!*\n"
        f"{premium_text}\n\n"
        f"💰 Баланс: {user_data[user_id]['balance']} монет\n"
        f"🖱️ Кликов: {user_data[user_id]['clicks']}\n\n"
        f"Продолжай кликать!"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== СТАТИСТИКА ==========
async def show_stats(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    user = user_data[user_id]
    referrals_count = len(user.get('referrals', []))

    keyboard = [
        [InlineKeyboardButton("🪙 Кликнуть!", callback_data="click")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    premium_status = "⭐ *Премиум*" if user.get('premium') else "Обычный"
    admin_status = "👑 *Администратор*" if user.get('is_admin') else ""

    text = (
        f"📊 *Твоя статистика*\n\n"
        f"{admin_status}\n"
        f"👤 Статус: {premium_status}\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"🖱️ Всего кликов: {user['clicks']}\n"
        f"👥 Рефералов: {referrals_count}\n"
        f"💎 Заработано с рефералов: {referrals_count * 20} монет\n"
    )

    if user.get('premium_until'):
        until = datetime.fromisoformat(user['premium_until'])
        days_left = (until - datetime.now()).days
        text += f"\n⏳ Премиум до: {until.strftime('%d.%m.%Y')} (осталось {days_left} дней)"

    if user.get('vpn_active'):
        text += f"\n🔒 VPN: Активен"

    await send_with_image(update, context, text, reply_markup)


# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
async def referral_menu(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    user = user_data[user_id]
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user['referral_code']}"
    referrals_count = len(user.get('referrals', []))

    keyboard = [
        [InlineKeyboardButton("📤 Поделиться ссылкой",
                              url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся к Clicker боту и зарабатывай монеты! 🚀")],
        [InlineKeyboardButton("📋 Скопировать ссылку", callback_data=f"copy_ref_{user['referral_code']}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"👥 *Реферальная система*\n\n"
        f"📎 Твой реферальный код:\n`{user['referral_code']}`\n\n"
        f"👥 Приглашено: {referrals_count}\n"
        f"💰 Заработано: {referrals_count * 20} монет\n\n"
        f"🔥 За каждого приглашенного ты получаешь:\n"
        f"• 20 монет бонусом\n"
        f"• 20% с каждого его клика!\n\n"
        f"📋 Нажми на кнопку, чтобы скопировать ссылку"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== КОПИРОВАНИЕ ССЫЛКИ ==========
async def copy_ref_callback(update, context):
    query = update.callback_query
    await query.answer()

    ref_code = query.data.split('_')[2]
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"

    keyboard = [
        [InlineKeyboardButton("📤 Поделиться",
                              url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся к Clicker боту и зарабатывай монеты! 🚀")],
        [InlineKeyboardButton("🔙 Назад", callback_data="referral")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"📋 *Твоя реферальная ссылка:*\n\n"
        f"`{ref_link}`\n\n"
        f"Скопируй её и отправь друзьям!\n"
        f"За каждого приглашенного ты получишь 20 монет! 🎁"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ПРОФИЛЬ ==========
async def profile_menu(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    user = user_data[user_id]
    referrals_count = len(user.get('referrals', []))

    if user.get('premium'):
        name_display = rainbow_text(user.get('first_name', 'Пользователь'))
        premium_text = "⭐ ПРЕМИУМ ⭐"
    else:
        name_display = user.get('first_name', 'Пользователь')
        premium_text = "Обычный пользователь"

    admin_text = "👑 АДМИНИСТРАТОР" if user.get('is_admin') else ""

    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton("⭐ Купить Премиум", callback_data="buy_premium")],
        [InlineKeyboardButton("📝 VPN за комментарии", callback_data="vpn_comment")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"👤 *Профиль*\n\n"
        f"👤 Имя: {name_display}\n"
        f"📌 Статус: {premium_text}\n"
        f"{admin_text}\n"
        f"Username: @{user.get('username', 'Не указан')}\n"
        f"ID: `{user_id}`\n\n"
        f"📝 О себе: {user.get('bio', 'Не указано')}\n"
        f"📍 Город: {user.get('city', 'Не указан')}\n"
        f"🎂 Возраст: {user.get('age', 'Не указан')}\n\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"🖱️ Всего кликов: {user['clicks']}\n"
        f"👥 Рефералов: {referrals_count}\n"
    )

    if user.get('premium_until'):
        until = datetime.fromisoformat(user['premium_until'])
        text += f"\n⏳ Премиум до: {until.strftime('%d.%m.%Y')}"

    if user.get('vpn_active'):
        text += f"\n🔒 VPN: Активен"

    await send_with_image(update, context, text, reply_markup)


# ========== РЕДАКТИРОВАНИЕ ПРОФИЛЯ ==========
async def edit_profile_menu(update, context):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📝 Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton("📝 Изменить описание", callback_data="edit_bio")],
        [InlineKeyboardButton("📍 Изменить город", callback_data="edit_city")],
        [InlineKeyboardButton("🎂 Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "✏️ *Редактирование профиля*\n\nВыбери что хочешь изменить:"
    await send_with_image(update, context, text, reply_markup)


async def edit_field_start(update, context):
    query = update.callback_query
    await query.answer()

    field = query.data.replace("edit_", "")
    context.user_data['editing_field'] = field

    field_names = {
        'name': 'новое имя',
        'bio': 'новое описание',
        'city': 'новый город',
        'age': 'новый возраст'
    }

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="edit_profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"✏️ Введи {field_names.get(field, field)}:\n\nОтправь сообщение с новым значением."
    await send_with_image(update, context, text, reply_markup)


async def handle_edit_text(update, context):
    if 'editing_field' not in context.user_data:
        return

    user_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        return

    field = context.user_data['editing_field']
    value = update.message.text

    field_map = {
        'name': 'first_name',
        'bio': 'bio',
        'city': 'city',
        'age': 'age'
    }

    if field in field_map:
        user_data[user_id][field_map[field]] = value
        save_json(USER_DATA_FILE, user_data)

        del context.user_data['editing_field']

        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"✅ *{field.capitalize()} успешно обновлено!*"
        await send_with_image(update, context, text, reply_markup)
    else:
        del context.user_data['editing_field']
        await main_menu(update, context)


# ========== ПОКУПКА ПРЕМИУМ ЧЕРЕЗ STARS ==========
async def buy_premium_menu(update, context):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = str(user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    user_info = user_data[user_id]

    is_admin_user = is_admin(user)
    price_display = get_user_price_display(user)

    if user_info.get('premium'):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "⭐ *У тебя уже есть Премиум!*\n\n"
            f"⏳ Действует до: {datetime.fromisoformat(user_info['premium_until']).strftime('%d.%m.%Y')}"
        )
        await send_with_image(update, context, text, reply_markup)
        return

    admin_discount = "👑 *Админская цена: 1 ⭐!*" if is_admin_user else ""

    keyboard = [
        [InlineKeyboardButton(f"⭐ Оплатить {price_display}", callback_data="pay_premium")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"⭐ *Премиум Статус*\n\n"
        f"💰 Цена: {price_display} (Telegram Stars)\n"
        f"{admin_discount}\n\n"
        f"🔥 *Что дает Премиум:*\n"
        f"• 🪙 +5 монет за каждый клик (вместо 1)\n"
        f"• 💰 Скидка 50% на все товары\n"
        f"• 🌈 Радужный ник в профиле\n"
        f"• 👑 Эксклюзивный статус\n"
        f"• ⏳ Действует 30 дней\n\n"
        f"Нажми 'Оплатить' для покупки через Telegram Stars"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ОПЛАТА ЧЕРЕЗ STARS ==========
async def pay_premium(update, context):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = str(user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    price_in_cents = get_user_price(user)

    logger.info(f"💰 User {user_id} price: {price_in_cents} cents")

    prices = [LabeledPrice("⭐ Премиум статус (30 дней)", price_in_cents)]

    await context.bot.send_invoice(
        chat_id=user_id,
        title="⭐ Премиум статус",
        description=f"30 дней премиум доступа в Clicker боте:\n"
                    "• +5 монет за клик\n"
                    "• Скидка 50% на все товары\n"
                    "• Радужный ник\n"
                    "• Эксклюзивный статус",
        payload=f"premium_{user_id}_{datetime.now().timestamp()}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="premium_payment",
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        is_flexible=False
    )


# ========== ОБРАБОТКА ПРЕДВАРИТЕЛЬНОЙ ПРОВЕРКИ ==========
async def pre_checkout_handler(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)
    logger.info(f"✅ Pre-checkout ok for user {query.from_user.id}")


# ========== ОБРАБОТКА УСПЕШНОЙ ОПЛАТЫ ==========
async def successful_payment_handler(update, context):
    user_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await update.message.reply_text("❌ Ошибка! Начни с /start")
        return

    user_data[user_id]["premium"] = True
    user_data[user_id]["premium_until"] = (datetime.now() + timedelta(days=30)).isoformat()

    save_json(USER_DATA_FILE, user_data)

    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"⭐ *Поздравляем! Ты купил Премиум Статус!*\n\n"
        f"🔥 Теперь ты получаешь:\n"
        f"• 🪙 +5 монет за клик\n"
        f"• 💰 Скидка 50% на все товары\n"
        f"• 🌈 Радужный ник в профиле\n"
        f"• 👑 Эксклюзивный статус\n\n"
        f"⏳ Премиум активен 30 дней!\n"
        f"💰 Твой баланс монет: {user_data[user_id]['balance']}"
    )

    if os.path.exists(IMAGE_PATH):
        with open(IMAGE_PATH, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    logger.info(f"✅ User {user_id} bought premium via Stars!")


# ========== VPN ЗА КОММЕНТАРИИ ==========
async def vpn_comment_menu(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    if user_data[user_id].get('vpn_active', False):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "✅ *У тебя уже есть активный VPN!*"
        await send_with_image(update, context, text, reply_markup)
        return

    keyboard = [
        [InlineKeyboardButton("✅ Я выполнил!", callback_data="vpn_complete")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📝 *Бесплатный VPN*\n\n"
        "Чтобы получить доступ, выполните задание:\n\n"
        "📌 *Инструкция:*\n\n"
        "1️⃣ Откройте TikTok/Youtube и введите в поиске: *впн бравл старс*\n\n"
        "2️⃣ В фильтрах выберите *Дата публикации*\n\n"
        "3️⃣ Найдите видео и напишите *10 комментариев* с этим текстом:\n\n"
        "`С @mil8kavpn 0 пинга`\n\n"
        "4️⃣ *ОБЯЗАТЕЛЬНО!* Отвечайте и лайкайте на чужие комментарии с упоминанием нашего бота @mil8kavpn:\n\n"
        "`Реально работает кстати`\n\n"
        "5️⃣ Сделайте *10 скриншотов* (ваши комментарии + ответы) и отправьте их сюда.\n\n"
        "6️⃣ Без ответов на чужие комментарии VPN *НЕ ВЫДАДУТ!*\n\n"
        "7️⃣ Можно получать раз в сутки.\n"
        "*изменено 10:55*\n\n"
        "📸 Нажми 'Я выполнил!' когда будешь готов отправить скриншоты."
    )

    await send_with_image(update, context, text, reply_markup)


async def vpn_complete(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    if user_data[user_id].get('vpn_active', False):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "✅ *У тебя уже есть активный VPN!*"
        await send_with_image(update, context, text, reply_markup)
        return

    if user_data[user_id].get("vpn_request") and user_data[user_id]["vpn_request"].get("status") == "pending":
        keyboard = [[InlineKeyboardButton("📤 Отправить скриншоты", callback_data="send_screenshots")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "📸 *У тебя уже есть активная заявка!*\n\n"
            "Нажми на кнопку ниже, чтобы отправить скриншоты."
        )
        await send_with_image(update, context, text, reply_markup)
        return

    user_data[user_id]["vpn_request"] = {
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id,
        "username": user_data[user_id].get("username", ""),
        "first_name": user_data[user_id].get("first_name", "")
    }
    save_json(USER_DATA_FILE, user_data)

    pending = load_json(PENDING_REQUESTS_FILE)
    pending[user_id] = user_data[user_id]["vpn_request"]
    save_json(PENDING_REQUESTS_FILE, pending)

    keyboard = [[InlineKeyboardButton("📤 Отправить скриншоты", callback_data="send_screenshots")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📸 *Отправь 10 скриншотов!*\n\n"
        "Нажми на кнопку и отправь 10 скриншотов подряд.\n"
        "После проверки администратор выдаст тебе VPN."
    )

    await send_with_image(update, context, text, reply_markup)


async def send_screenshots(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    if not user_data[user_id].get("vpn_request") or user_data[user_id]["vpn_request"].get("status") != "pending":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "❌ У тебя нет активной заявки на VPN!"
        await send_with_image(update, context, text, reply_markup)
        return

    context.user_data['awaiting_screenshots'] = True
    context.user_data['screenshot_count'] = 0
    context.user_data['screenshots'] = []

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📸 *Отправь 10 скриншотов*\n\n"
        f"Отправь 10 скриншотов (0/10).\n"
        "Нажми 'Отмена' чтобы прервать отправку."
    )

    await send_with_image(update, context, text, reply_markup)


async def handle_screenshots(update, context):
    if not context.user_data.get('awaiting_screenshots', False):
        return

    user_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        return

    if not update.message.photo:
        await update.message.reply_text("❌ Пожалуйста, отправь фото!")
        return

    if not user_data[user_id].get("vpn_request") or user_data[user_id]["vpn_request"].get("status") != "pending":
        context.user_data['awaiting_screenshots'] = False
        context.user_data['screenshot_count'] = 0
        context.user_data['screenshots'] = []
        await update.message.reply_text("❌ У тебя нет активной заявки на VPN!")
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    context.user_data['screenshots'].append(file.file_id)
    context.user_data['screenshot_count'] += 1

    if context.user_data['screenshot_count'] >= 10:
        context.user_data['awaiting_screenshots'] = False

        user_info = user_data[user_id]
        for admin_id in ADMINS:
            if admin_id.isdigit():
                try:
                    keyboard = [
                        [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_vpn_{user_id}")],
                        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_vpn_{user_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    text = (
                        f"📸 *Новая заявка на VPN!*\n\n"
                        f"👤 Пользователь: {user_info.get('first_name', 'Неизвестно')}\n"
                        f"📝 Username: @{user_info.get('username', 'Не указан')}\n"
                        f"🆔 ID: `{user_id}`\n\n"
                        f"📸 Получено 10 скриншотов:"
                    )

                    await context.bot.send_message(
                        chat_id=int(admin_id),
                        text=text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )

                    for i, photo_id in enumerate(context.user_data['screenshots'], 1):
                        await context.bot.send_photo(
                            chat_id=int(admin_id),
                            photo=photo_id,
                            caption=f"📸 Скриншот {i}/10"
                        )

                except Exception as e:
                    logger.error(f"Error sending to admin {admin_id}: {e}")

        context.user_data['screenshots'] = []
        context.user_data['screenshot_count'] = 0

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "✅ *Скриншоты отправлены на проверку!*\n\n"
            "Администратор проверит их и выдаст тебе VPN.\n"
            "Ожидай уведомления."
        )
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    else:
        text = (
            f"📸 *Отправь скриншоты*\n\n"
            f"Отправлено: {context.user_data['screenshot_count']}/10\n"
            "Продолжай отправлять скриншоты."
        )
        await update.message.reply_text(text, parse_mode='Markdown')


# ========== ОБРАБОТКА ЗАЯВОК АДМИНОМ ==========
async def approve_vpn(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    user_id = query.data.split('_')[2]
    user_data = load_json(USER_DATA_FILE)
    pending = load_json(PENDING_REQUESTS_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return

    vpn_code = generate_vpn_code()
    bot_username = context.bot.username
    vpn_link = f"https://t.me/{bot_username}?start=vpn_{vpn_code}"

    user_data[user_id]["vpn_active"] = True
    user_data[user_id]["vpn_code"] = vpn_code
    user_data[user_id]["vpn_request"] = {"status": "approved", "approved_at": datetime.now().isoformat()}

    if user_id in pending:
        del pending[user_id]

    save_json(USER_DATA_FILE, user_data)
    save_json(PENDING_REQUESTS_FILE, pending)

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"✅ *VPN активирован!*\n\n"
                 f"🔗 Твоя ссылка для входа:\n`{vpn_link}`\n\n"
                 f"💰 Твой баланс: {user_data[user_id]['balance']} монет",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending VPN to user {user_id}: {e}")

    keyboard = [[InlineKeyboardButton("✅ Одобрено", callback_data="done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"✅ Заявка пользователя {user_id} одобрена!\n\n"
        f"🔗 VPN ссылка отправлена пользователю.",
        reply_markup=reply_markup
    )


async def reject_vpn(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    user_id = query.data.split('_')[2]
    user_data = load_json(USER_DATA_FILE)
    pending = load_json(PENDING_REQUESTS_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return

    user_data[user_id]["vpn_request"] = {"status": "rejected", "rejected_at": datetime.now().isoformat()}

    if user_id in pending:
        del pending[user_id]

    save_json(USER_DATA_FILE, user_data)
    save_json(PENDING_REQUESTS_FILE, pending)

    try:
        keyboard = [[InlineKeyboardButton("📝 Попробовать снова", callback_data="vpn_comment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=int(user_id),
            text="❌ *Твоя заявка на VPN отклонена!*\n\n"
                 "Пожалуйста, попробуй снова и убедись, что все скриншоты корректны.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending rejection to user {user_id}: {e}")

    keyboard = [[InlineKeyboardButton("❌ Отклонено", callback_data="done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"❌ Заявка пользователя {user_id} отклонена.\n\n"
        f"Пользователь уведомлен.",
        reply_markup=reply_markup
    )


# ========== АДМИН-ПАНЕЛЬ ==========
async def admin_panel(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    pending = load_json(PENDING_REQUESTS_FILE)
    user_data = load_json(USER_DATA_FILE)

    total_users = len(user_data)
    pending_requests = len(pending)
    premium_users = sum(1 for u in user_data.values() if u.get('premium', False))
    total_clicks = sum(u.get('clicks', 0) for u in user_data.values())
    total_balance = sum(u.get('balance', 0) for u in user_data.values())

    keyboard = [
        [InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton("📝 Заявки на VPN", callback_data="admin_requests")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💎 Управление балансом", callback_data="admin_balance")],
        [InlineKeyboardButton("⭐ Подарить премиум", callback_data="admin_gift_premium")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"⚙️ *Админ-панель*\n\n"
        f"📊 Статистика:\n"
        f"• 👥 Пользователей: {total_users}\n"
        f"• ⭐ Премиум: {premium_users}\n"
        f"• 📝 Ожидают VPN: {pending_requests}\n"
        f"• 🖱️ Всего кликов: {total_clicks}\n"
        f"• 💰 Всего монет: {total_balance}\n\n"
        f"Выбери действие:"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== АДМИН-СТАТИСТИКА ==========
async def admin_stats(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    user_data = load_json(USER_DATA_FILE)

    total_users = len(user_data)
    premium_users = sum(1 for u in user_data.values() if u.get('premium', False))
    total_clicks = sum(u.get('clicks', 0) for u in user_data.values())
    total_balance = sum(u.get('balance', 0) for u in user_data.values())
    total_referrals = sum(len(u.get('referrals', [])) for u in user_data.values())

    top_clicks = sorted(user_data.items(), key=lambda x: x[1].get('clicks', 0), reverse=True)[:5]
    top_users_text = "\n".join([
        f"{i + 1}. {u[1].get('first_name', 'Неизвестно')} - {u[1].get('clicks', 0)} кликов"
        for i, u in enumerate(top_clicks)
    ])

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"📊 *Детальная статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"⭐ Премиум: {premium_users}\n"
        f"🖱️ Всего кликов: {total_clicks}\n"
        f"💰 Всего монет: {total_balance}\n"
        f"👥 Всего рефералов: {total_referrals}\n\n"
        f"🏆 *Топ по кликам:*\n{top_users_text}"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ЗАЯВКИ НА VPN ==========
async def admin_requests(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    pending = load_json(PENDING_REQUESTS_FILE)

    if not pending:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📝 *Нет активных заявок на VPN*"
        await send_with_image(update, context, text, reply_markup)
        return

    text = "📝 *Активные заявки на VPN:*\n\n"
    keyboard = []

    for user_id, request in pending.items():
        user_data = load_json(USER_DATA_FILE)
        user_info = user_data.get(user_id, {})
        username = user_info.get('username', 'Неизвестно')
        text += f"• @{username} (ID: `{user_id}`)\n"

        keyboard.append([
            InlineKeyboardButton(f"👤 {username}", callback_data=f"view_request_{user_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_with_image(update, context, text, reply_markup)


async def view_request(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    user_id = query.data.split('_')[2]
    user_data = load_json(USER_DATA_FILE)
    pending = load_json(PENDING_REQUESTS_FILE)

    if user_id not in pending:
        await query.edit_message_text("❌ Заявка уже обработана!")
        return

    user_info = user_data.get(user_id, {})
    request = pending.get(user_id, {})

    keyboard = [
        [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_vpn_{user_id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_vpn_{user_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_requests")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"📝 *Заявка на VPN*\n\n"
        f"👤 Имя: {user_info.get('first_name', 'Неизвестно')}\n"
        f"📝 Username: @{user_info.get('username', 'Не указан')}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📅 Создана: {request.get('created_at', 'Неизвестно')}\n\n"
        f"Скриншоты отправлены ранее."
    )

    await send_with_image(update, context, text, reply_markup)


# ========== РАССЫЛКА ==========
async def admin_broadcast(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    keyboard = [
        [InlineKeyboardButton("📝 Текст", callback_data="broadcast_text")],
        [InlineKeyboardButton("🖼 Фото", callback_data="broadcast_photo")],
        [InlineKeyboardButton("🎥 Видео", callback_data="broadcast_video")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📢 *Рассылка*\n\n"
        "Выбери тип сообщения для рассылки:\n\n"
        "⚠️ Сообщение будет отправлено ВСЕМ пользователям!"
    )

    await send_with_image(update, context, text, reply_markup)


async def broadcast_text(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['broadcast_type'] = 'text'
    context.user_data['broadcast_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📢 *Отправь текст для рассылки*\n\n⚠️ Сообщение будет отправлено ВСЕМ пользователям!"
    await send_with_image(update, context, text, reply_markup)


async def broadcast_photo(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['broadcast_type'] = 'photo'
    context.user_data['broadcast_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📢 *Отправь фото для рассылки*\n\n⚠️ Сообщение будет отправлено ВСЕМ пользователям!"
    await send_with_image(update, context, text, reply_markup)


async def broadcast_video(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['broadcast_type'] = 'video'
    context.user_data['broadcast_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📢 *Отправь видео для рассылки*\n\n⚠️ Сообщение будет отправлено ВСЕМ пользователям!"
    await send_with_image(update, context, text, reply_markup)


async def handle_broadcast(update, context):
    if not context.user_data.get('broadcast_mode', False):
        return

    admin_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if admin_id not in user_data or not user_data[admin_id].get('is_admin', False):
        return

    broadcast_type = context.user_data.get('broadcast_type', 'text')
    users = list(user_data.keys())
    
    if not users:
        await update.message.reply_text("❌ Нет пользователей для рассылки!")
        context.user_data['broadcast_mode'] = False
        return

    sent = 0
    failed = 0

    progress_msg = await update.message.reply_text(
        f"📢 Начинаю рассылку {len(users)} пользователям...\n"
        f"Тип: {broadcast_type}"
    )

    for i, uid in enumerate(users, 1):
        try:
            if broadcast_type == 'photo' and update.message.photo:
                photo = update.message.photo[-1].file_id
                caption = update.message.caption or "📢 Важное сообщение от администрации!"
                await context.bot.send_photo(
                    chat_id=int(uid),
                    photo=photo,
                    caption=caption
                )
            elif broadcast_type == 'video' and update.message.video:
                caption = update.message.caption or "📢 Важное сообщение от администрации!"
                await context.bot.send_video(
                    chat_id=int(uid),
                    video=update.message.video.file_id,
                    caption=caption
                )
            else:
                text = update.message.text or "📢 Важное сообщение от администрации!"
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=text,
                    parse_mode='Markdown'
                )
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Error broadcasting to {uid}: {e}")

        if i % 10 == 0:
            try:
                await progress_msg.edit_text(
                    f"📢 Рассылка в процессе... ({i}/{len(users)})\n"
                    f"✅ Отправлено: {sent}\n"
                    f"❌ Ошибок: {failed}"
                )
            except:
                pass

    await progress_msg.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📨 Отправлено: {sent} пользователям\n"
        f"❌ Ошибок: {failed}\n"
        f"📊 Всего: {len(users)} пользователей"
    )

    context.user_data['broadcast_mode'] = False
    context.user_data['broadcast_type'] = None


# ========== УПРАВЛЕНИЕ БАЛАНСОМ ==========
async def admin_balance(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Добавить монеты", callback_data="add_balance")],
        [InlineKeyboardButton("➖ Забрать монеты", callback_data="remove_balance")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "💎 *Управление балансом*\n\nВыбери действие:"
    await send_with_image(update, context, text, reply_markup)


async def add_balance_start(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['balance_action'] = 'add'
    context.user_data['awaiting_user_id'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_balance")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "💎 *Добавить монеты*\n\nОтправь ID пользователя и количество монет через пробел.\n\nПример: `7737148018 1000`"
    await send_with_image(update, context, text, reply_markup)


async def remove_balance_start(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['balance_action'] = 'remove'
    context.user_data['awaiting_user_id'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_balance")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "💎 *Забрать монеты*\n\nОтправь ID пользователя и количество монет через пробел.\n\nПример: `7737148018 500`"
    await send_with_image(update, context, text, reply_markup)


async def handle_balance_input(update, context):
    if not context.user_data.get('awaiting_user_id', False):
        return

    user_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data or not user_data[user_id].get('is_admin', False):
        return

    try:
        parts = update.message.text.split()
        target_user_id = parts[0]
        amount = int(parts[1])

        if target_user_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return

        action = context.user_data.get('balance_action', 'add')

        if action == 'add':
            user_data[target_user_id]["balance"] += amount
            save_json(USER_DATA_FILE, user_data)

            await update.message.reply_text(
                f"✅ Добавлено {amount} монет пользователю {target_user_id}\n"
                f"💰 Новый баланс: {user_data[target_user_id]['balance']}"
            )

            try:
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=f"✅ Администратор добавил тебе {amount} монет!\n"
                         f"💰 Твой баланс: {user_data[target_user_id]['balance']} монет"
                )
            except:
                pass

        elif action == 'remove':
            if user_data[target_user_id]["balance"] < amount:
                await update.message.reply_text(
                    f"❌ У пользователя недостаточно монет!\n"
                    f"💰 Баланс: {user_data[target_user_id]['balance']} монет"
                )
                return

            user_data[target_user_id]["balance"] -= amount
            save_json(USER_DATA_FILE, user_data)

            await update.message.reply_text(
                f"✅ Забрано {amount} монет у пользователя {target_user_id}\n"
                f"💰 Новый баланс: {user_data[target_user_id]['balance']}"
            )

            try:
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=f"⚠️ Администратор забрал у тебя {amount} монет!\n"
                         f"💰 Твой баланс: {user_data[target_user_id]['balance']} монет"
                )
            except:
                pass

        context.user_data['awaiting_user_id'] = False
        context.user_data['balance_action'] = None

    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Неверный формат!\n"
            "Отправь: `ID_пользователя количество`\n"
            "Пример: `7737148018 1000`"
        )


# ========== ДАРЕНИЕ ПРЕМИУМА ==========
async def admin_gift_premium(update, context):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user):
        await query.edit_message_text("❌ У тебя нет прав администратора!")
        return

    context.user_data['gift_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "⭐ *Подарить премиум*\n\n"
        "Отправь ID или @username пользователя, которому хочешь подарить премиум.\n\n"
        "Примеры:\n"
        "`7737148018`\n"
        "`@mil8kavpn`\n\n"
        "⚠️ Премиум будет выдан на 30 дней!"
    )

    await send_with_image(update, context, text, reply_markup)


async def handle_gift_premium(update, context):
    if not context.user_data.get('gift_mode', False):
        return

    admin_id = str(update.effective_user.id)
    user_data = load_json(USER_DATA_FILE)

    if admin_id not in user_data or not user_data[admin_id].get('is_admin', False):
        return

    user_input = update.message.text.strip()
    target_user_id = None
    target_username = None

    if user_input.startswith('@'):
        target_username = user_input[1:].lower()
        for uid, uinfo in user_data.items():
            if uinfo.get('username', '').lower() == target_username:
                target_user_id = uid
                break
    else:
        target_user_id = user_input

    if target_user_id not in user_data:
        await update.message.reply_text(
            "❌ Пользователь не найден!\n"
            "Проверь правильность ID или @username."
        )
        return

    user_data[target_user_id]["premium"] = True
    user_data[target_user_id]["premium_until"] = (datetime.now() + timedelta(days=30)).isoformat()

    save_json(USER_DATA_FILE, user_data)

    target_name = user_data[target_user_id].get('first_name', 'Пользователь')

    await update.message.reply_text(
        f"✅ *Премиум подарен!*\n\n"
        f"👤 Пользователь: {target_name}\n"
        f"🆔 ID: `{target_user_id}`\n"
        f"⏳ Действует 30 дней\n\n"
        f"Пользователь уведомлен."
    )

    try:
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=(
                f"⭐ *Поздравляем! Тебе подарили Премиум Статус!*\n\n"
                f"🔥 Теперь ты получаешь:\n"
                f"• 🪙 +5 монет за клик\n"
                f"• 💰 Скидка 50% на все товары\n"
                f"• 🌈 Радужный ник в профиле\n"
                f"• 👑 Эксклюзивный статус\n\n"
                f"⏳ Премиум активен 30 дней!"
            ),
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error notifying user {target_user_id}: {e}")

    context.user_data['gift_mode'] = False


# ========== ПОКУПКА VPN ЗА МОНЕТЫ ==========
async def buy_vpn_menu(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    is_premium = user_data[user_id].get('premium', False)
    price = VPN_PRICE_PREMIUM if is_premium else VPN_PRICE

    keyboard = [
        [InlineKeyboardButton(f"🔒 Купить VPN - {price}💰", callback_data="buy_vpn")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    discount_text = "⭐ *Скидка 50% активна!*" if is_premium else ""

    text = (
        f"🛒 *Купить VPN*\n\n"
        f"💰 Твой баланс: {user_data[user_id]['balance']} монет\n"
        f"{discount_text}\n\n"
        f"🔒 Цена VPN: {price} монет\n"
        f"⚡ Скорость до 100 Мбит/с\n"
        f"🌍 Безлимитный трафик\n"
        f"🔐 Анонимный и безопасный"
    )

    await send_with_image(update, context, text, reply_markup)


async def buy_vpn_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_json(USER_DATA_FILE)

    if user_id not in user_data:
        await query.edit_message_text("❌ Ошибка! Начни с /start")
        return

    if user_data[user_id].get('vpn_active', False):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "✅ *У тебя уже есть активный VPN!*"
        await send_with_image(update, context, text, reply_markup)
        return

    is_premium = user_data[user_id].get('premium', False)
    price = VPN_PRICE_PREMIUM if is_premium else VPN_PRICE

    if user_data[user_id]["balance"] < price:
        keyboard = [
            [InlineKeyboardButton("🪙 Заработать монеты!", callback_data="clicker")],
            [InlineKeyboardButton("🔙 Назад", callback_data="buy_vpn_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"❌ *Недостаточно монет!*\n\n"
            f"Нужно: {price} монет\n"
            f"У тебя: {user_data[user_id]['balance']} монет\n\n"
            f"Покликай, чтобы заработать! 🪙"
        )
        await send_with_image(update, context, text, reply_markup)
        return

    vpn_code = generate_vpn_code()
    bot_username = context.bot.username
    vpn_link = f"https://t.me/{bot_username}?start=vpn_{vpn_code}"

    user_data[user_id]["balance"] -= price
    user_data[user_id]["vpn_active"] = True
    user_data[user_id]["vpn_code"] = vpn_code

    save_json(USER_DATA_FILE, user_data)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ *VPN куплен!*\n\n"
             f"🔗 Твоя ссылка для входа:\n`{vpn_link}`\n\n"
             f"💰 Остаток: {user_data[user_id]['balance']} монет",
        parse_mode='Markdown'
    )

    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"✅ *VPN успешно куплен!*\n\n"
        f"💰 Остаток: {user_data[user_id]['balance']} монет\n\n"
        f"📨 Ссылка для входа отправлена в Telegram"
    )

    await send_with_image(update, context, text, reply_markup)


# ========== ОБРАБОТЧИК КНОПОК ==========
async def button_handler(update, context):
    query = update.callback_query
    data = query.data

    if data == "back":
        await main_menu(update, context)
    elif data == "back_to_sponsors":
        await back_to_sponsors(update, context)
    elif data == "enter_bot":
        await enter_bot(update, context)
    elif data == "clicker":
        await clicker_menu(update, context)
    elif data == "click":
        await handle_click(update, context)
    elif data == "stats":
        await show_stats(update, context)
    elif data == "referral":
        await referral_menu(update, context)
    elif data == "profile":
        await profile_menu(update, context)
    elif data == "edit_profile":
        await edit_profile_menu(update, context)
    elif data in ["edit_name", "edit_bio", "edit_city", "edit_age"]:
        await edit_field_start(update, context)
    elif data == "buy_premium":
        await buy_premium_menu(update, context)
    elif data == "pay_premium":
        await pay_premium(update, context)
    elif data == "buy_vpn_menu":
        await buy_vpn_menu(update, context)
    elif data == "buy_vpn":
        await buy_vpn_callback(update, context)
    elif data.startswith("copy_ref_"):
        await copy_ref_callback(update, context)
    elif data in ["sponsor1", "sponsor2"]:
        await handle_sponsor(update, context)
    elif data == "vpn_comment":
        await vpn_comment_menu(update, context)
    elif data == "vpn_complete":
        await vpn_complete(update, context)
    elif data == "send_screenshots":
        await send_screenshots(update, context)
    elif data.startswith("approve_vpn_"):
        await approve_vpn(update, context)
    elif data.startswith("reject_vpn_"):
        await reject_vpn(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_requests":
        await admin_requests(update, context)
    elif data.startswith("view_request_"):
        await view_request(update, context)
    elif data == "admin_broadcast":
        await admin_broadcast(update, context)
    elif data == "broadcast_text":
        await broadcast_text(update, context)
    elif data == "broadcast_photo":
        await broadcast_photo(update, context)
    elif data == "broadcast_video":
        await broadcast_video(update, context)
    elif data == "admin_balance":
        await admin_balance(update, context)
    elif data == "add_balance":
        await add_balance_start(update, context)
    elif data == "remove_balance":
        await remove_balance_start(update, context)
    elif data == "admin_gift_premium":
        await admin_gift_premium(update, context)
    elif data == "done":
        await query.answer()


# ========== ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT ==========
from flask import Flask

# Создаём Flask приложение
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "OK", 200

@web_app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port, debug=False)


# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    print("=" * 50)
    print("🤖 БОТ С VPN И АДМИН-ПАНЕЛЬЮ")
    print("=" * 50)

    if os.path.exists(IMAGE_PATH):
        print("✅ Картинка найдена!")
    else:
        print(f"⚠️ Картинка {IMAGE_PATH} не найдена!")

    print("=" * 50)
    print("⭐ Обычный пользователь: 100 ⭐")
    print("👑 Администратор: 1 ⭐")
    print(f"👑 Админы: {', '.join(ADMINS)}")
    print("=" * 50)

    # ✅ ЗАПУСКАЕМ ВЕБ-СЕРВЕР В ОТДЕЛЬНОМ ПОТОКЕ
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("✅ Веб-сервер запущен на порту 10000")

    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    
    # Обработка текста для редактирования
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_text))
    
    # Обработка скриншотов
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshots))
    
    # Обработка баланса
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_balance_input))
    
    # Обработка рассылки
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast))
    application.add_handler(MessageHandler(filters.PHOTO, handle_broadcast))
    
    # Обработка дарения премиума
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gift_premium))
    
    # Обработка оплаты
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    print("🚀 Бот запущен и работает!")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
