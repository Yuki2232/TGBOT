import telebot
from telebot import types
import database
import random
import re
import configparser
import psycopg2
 
config = configparser.ConfigParser()
config.read('config.ini', encoding = 'utf-8')
 
TOKEN = config['configs']['token']
password = config['configs']['password']
 
 
bot = telebot.TeleBot(TOKEN)
 
# Состояния для FSM (Finite State Machine)
STATE_MAIN = 0
STATE_ADD_WORD = 1
STATE_DELETE_WORD = 2
user_states = {0: "STATE_MAIN", 1: "STATE_ADD_WORD", 2: "STATE_DELETE_WORD"}


# Клавиатура главного меню
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('Новое слово 🆕'),
        types.KeyboardButton('Добавить слово ➕'),
        types.KeyboardButton('Удалить слово ❌')
    )
    return markup
 
 
# Клавиатура с вариантами ответов
def options_keyboard(options):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for option in options:
        markup.add(types.KeyboardButton(option))
    markup.add(types.KeyboardButton('Пропустить ⏩'), types.KeyboardButton('Главное меню 🏠'))
    return markup
 

# Кнопка старт 
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    database.add_user_if_not_exists(user.id, user.first_name)
    user_states[user.id] = STATE_MAIN
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {user.first_name}!\n\n"
        "Я помогу тебе учить английские слова.\n"
        "Используй кнопки ниже для управления:",
        reply_markup=main_keyboard()
    )
 

# Кнопла главное меню 
@bot.message_handler(func=lambda m: m.text == 'Главное меню 🏠')
def main_menu(message):
    user_states[message.from_user.id] = STATE_MAIN
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=main_keyboard()
    )
 

# Новое слово 
@bot.message_handler(func=lambda m: m.text == 'Новое слово 🆕' and user_states.get(m.from_user.id) == STATE_MAIN)
def new_word(message):
    user_id = message.from_user.id
    word_data = database.get_random_user_word(user_id)
    
    if word_data:
        word_id, rus_word, target, opt1, opt2, opt3 = word_data
        
        # Создаем и перемешиваем варианты
        options = [target, opt1, opt2, opt3]
        random.shuffle(options)
        
        # Сохраняем правильный ответ в callback data
        msg = bot.send_message(
            message.chat.id,
            f"📖 Слово: <b>{rus_word}</b>\n\n"
            "Выбери правильный перевод:",
            reply_markup=options_keyboard(options),
            parse_mode='HTML'
        )
        
        # Регистрируем следующий шаг
        bot.register_next_step_handler(
            msg, 
            check_answer,
            word_id=word_id,
            correct_answer=target,
            russian_word=rus_word,
            attempt = 1
        )
    else:
        bot.send_message(
            message.chat.id,
            "🎉 Поздравляю! Ты выучил все слова!",
            reply_markup=main_keyboard()
        )
 
def check_answer(message, word_id, correct_answer, russian_word, attempt=1):
    user_id = message.from_user.id
    
    if message.text == 'Главное меню 🏠':
        main_menu(message)
        return
    elif message.text == 'Пропустить ⏩':
        bot.send_message(
            message.chat.id,
            f"Правильный ответ: <b>{correct_answer}</b>",
            parse_mode='HTML',
            reply_markup=main_keyboard()
        )
        return
    
    if message.text == correct_answer:
        # Создаем клавиатуру для выбора действия
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('Удалить слово ✅'),
            types.KeyboardButton('Оставить слово 🔄'),
            types.KeyboardButton('Главное меню 🏠')
        )
        
        bot.send_message(
            message.chat.id,
            f"🎉 <b>Правильно!</b>\nЧто сделать со словом '{russian_word}'?",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        # Регистрируем следующий шаг для обработки выбора
        bot.register_next_step_handler(
            message, 
            handle_word_action,
            word_id=word_id,
            russian_word=russian_word
        )
    else:
        if attempt < 2:  # Даем 2 попытки
            # Формируем новый вопрос с тем же словом
            word_data = database.get_word_by_id(word_id)
            if word_data:
                word_id, rus_word, target, opt1, opt2, opt3 = word_data
                options = [target, opt1, opt2, opt3]
                random.shuffle(options)
                
                markup = options_keyboard(options)
                markup.add(types.KeyboardButton('Пропустить ⏩'))
                
                bot.send_message(
                    message.chat.id,
                    f"❌ Неправильно! Попытка {attempt} из 2.\n\n"
                    f"Как переводится слово: <b>{rus_word}</b>?",
                    parse_mode='HTML',
                    reply_markup=markup
                )
                
                # Повторно регистрируем обработчик с увеличением счетчика попыток
                bot.register_next_step_handler(
                    message, 
                    check_answer,
                    word_id=word_id,
                    correct_answer=correct_answer,
                    russian_word=russian_word,
                    attempt=attempt+1
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "⚠️ Ошибка при получении слова. Попробуйте другое слово.",
                    reply_markup=main_keyboard()
                )
        else:
            # После 2 неудачных попыток показываем правильный ответ
            bot.send_message(
                message.chat.id,
                f"❌ Неправильно! Правильный ответ: <b>{correct_answer}</b>",
                parse_mode='HTML',
                reply_markup=main_keyboard()
            )
 

def handle_word_action(message, word_id, russian_word):
    user_id = message.from_user.id
    
    if message.text == 'Удалить слово ✅':
        database.remove_user_word(user_id, word_id)
        bot.send_message(
            message.chat.id,
            f"🗑 Слово '{russian_word}' удалено из вашего списка для изучения.",
            reply_markup=main_keyboard()
        )
    elif message.text == 'Оставить слово 🔄':
        bot.send_message(
            message.chat.id,
            f"🔄 Слово '{russian_word}' осталось в вашем списке для повторения.",
            reply_markup=main_keyboard()
        )
    else:
        main_menu(message)
 

@bot.message_handler(func=lambda m: m.text == 'Добавить слово ➕' and user_states.get(m.from_user.id) == STATE_MAIN)
def add_word_start(message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_ADD_WORD
    
    msg = bot.send_message(
        message.chat.id,
        "📝 Введи новое слово в формате:\n"
        "<b>Русское слово : Правильный перевод : Неправильный1 : Неправильный2 : Неправильный3</b>\n\n"
        "Пример: <i>Яблоко : Apple : Orange : Banana : Pear</i>",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    bot.register_next_step_handler(msg, add_word_process)
 
def add_word_process(message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_MAIN
    
    if message.text == 'Главное меню 🏠':
        main_menu(message)
        return
    
    # Парсим ввод с разделением по двоеточию
    parts = [part.strip() for part in message.text.split(':')]
    
    if len(parts) != 5:
        bot.send_message(
            message.chat.id,
            "❌ Неправильный формат. Нужно 5 значений, разделенных двоеточиями.\n"
            "Пример: <i>Яблоко : Apple : Orange : Banana : Pear</i>",
            parse_mode='HTML',
            reply_markup=main_keyboard()
        )
        return
    
    russian, target, wrong1, wrong2, wrong3 = parts
    
    # Проверяем, что все поля заполнены
    if not all([russian, target, wrong1, wrong2, wrong3]):
        bot.send_message(
            message.chat.id,
            "❌ Все поля должны быть заполнены!",
            reply_markup=main_keyboard()
        )
        return
    
    if database.add_custom_word(user_id, russian, target, wrong1, wrong2, wrong3):
        bot.send_message(
            message.chat.id,
            f"✅ Слово <b>{russian}</b> успешно добавлено!",
            parse_mode='HTML',
            reply_markup=main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Слово <b>{russian}</b> уже существует!",
            parse_mode='HTML',
            reply_markup=main_keyboard()
        )

 
@bot.message_handler(func=lambda m: m.text == 'Удалить слово ❌' and user_states.get(m.from_user.id) == STATE_MAIN)
def delete_word_start(message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_DELETE_WORD
    
    bot.send_message(
        message.chat.id,
        "✏️ Введите русское слово, которое хотите удалить:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    bot.register_next_step_handler(message, process_word_deletion)
 
def process_word_deletion(message):
    user_id = message.from_user.id
    word_to_delete = message.text.strip()
    
    # Проверяем существование слова у пользователя
    conn = psycopg2.connect(**database.DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT w.id 
            FROM words w
            JOIN user_word uw ON w.id = uw.words_id
            WHERE uw.user_id = %s AND w.russian_word = %s
        """, (user_id, word_to_delete))
        result = cur.fetchone()
    
    if not result:
        bot.send_message(
            message.chat.id,
            f"⚠️ Слово '{word_to_delete}' не найдено в вашем словаре.\n"
            "Проверьте правильность написания и попробуйте снова.",
            reply_markup=main_keyboard()
        )
        user_states[user_id] = STATE_MAIN
        return
    
    word_id = result[0]
    
    # Клавиатура подтверждения
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Да, удалить ✅'),
        types.KeyboardButton('Нет, оставить ❎')
    )
    
    # Сохраняем данные для следующего шага
    global deletion_data
    deletion_data[user_id] = {"word_id": word_id, "word": word_to_delete}
    
    bot.send_message(
        message.chat.id,
        f"Вы точно хотите удалить слово '{word_to_delete}'?",
        reply_markup=markup
    )
    
    bot.register_next_step_handler(message, confirm_deletion)
 
deletion_data = {}


def confirm_deletion(message):
    user_id = message.from_user.id
    data = deletion_data.get(user_id)
    
    if not data:
        bot.send_message(
            message.chat.id,
            "⚠️ Сессия удаления истекла. Начните заново.",
            reply_markup=main_keyboard()
        )
        user_states[user_id] = STATE_MAIN
        return
    
    if message.text == 'Нет, оставить ❎':
        bot.send_message(
            message.chat.id,
            f"Слово '{data['word']}' осталось в вашем словаре.",
            reply_markup=main_keyboard()
        )
    elif message.text == 'Да, удалить ✅':
        if database.remove_user_word(user_id, data["word_id"]):
            bot.send_message(
                message.chat.id,
                f"✅ Слово '{data['word']}' успешно удалено!",
                reply_markup=main_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ Ошибка при удалении. Попробуйте позже.",
                reply_markup=main_keyboard()
            )
    
    # Очищаем данные
    if user_id in deletion_data:
        del deletion_data[user_id]
    
    user_states[user_id] = STATE_MAIN
 
 
if __name__ == "__main__":
    database.create_database()
    bot.polling()