import telebot
from db import Database
from dotenv import load_dotenv
from telebot import types
from datetime import date, datetime

load_dotenv()

import os

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

db = Database()
db.create_tables()

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add_dish = types.KeyboardButton("Добавить нямку")
    btn_remove_dish = types.KeyboardButton("Убрать нямку")
    btn_show_menu = types.KeyboardButton("Мое меню")
    btn_reset = types.KeyboardButton("Сбросит усьо")
    btn_show_summary = types.KeyboardButton("Нанямканое")
    btn_show_history = types.KeyboardButton("История нямканья")
    markup.add(btn_add_dish, btn_remove_dish)
    markup.add(btn_show_summary, btn_show_history)
    markup.add(btn_show_menu, btn_reset)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    db.add_user(message.chat.id)
    welcome_text  = "Привет! Давай считать сколько ты нямкаешь. \n Сначала добавь нямку в меню кнопкой 'Добавить нямку'. Вдруг добавила что-то не то - используй 'Убрать нямку'\nПосмотреть список нямок - 'Мое меню'. 'Сбросить усьо' - сбросить всё что нямкала за день\nПосле добавления нямки в меню напиши '+панан' и я запишу, что ты снямкала панан\nЕсли нямка весовая - вводи '+блинчик 200' и я запишу что ты снямкала 200г блинчиков\n'Нанямканое' - посмотреть сколько и чего нанямкала за день\n'История нямканья' - посмотреть список нямканья за один из прошлых дней"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "Добавить нямку")
def add_dish(message):
    bot.send_message(message.chat.id, "Запиши новую нямку в формате:\n"
                                      "`Название, калории, белки, жиры, углеводы`\n"
                                      "Запиши калорийность и БЖУ на 100 грам или на готовую нямку",
                     parse_mode='Markdown')
    bot.register_next_step_handler(message, save_dish)

def save_dish(message):
    try:
        data = message.text.split(',')
        name, calories, protein, fat, carbs = map(str.strip, data)
        db.add_dish(message.chat.id, name.lower(), int(calories), float(protein), float(fat), float(carbs))
        bot.reply_to(message, f"Нямку '{name}' добавил!")
    except Exception as e:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDdnXrD9kxPdxxnq_L2Py1iZxZOrngACkWMAAr3OWUqVmkfU6UBnezYE")
        bot.reply_to(message, "Ошибка: убедись, что всё ввела правильно\nНапример: Панан, 100, 1.1, 5.5, 10.1")
        print(e)

@bot.message_handler(func=lambda message: message.text == "Убрать нямку")
def remove_dish_init(message):
    bot.send_message(message.chat.id, "Напиши название нямки для удаления", parse_mode='Markdown')
    bot.register_next_step_handler(message, remove_dish)

def remove_dish(message):
    try:
        name = message.text
        db.remove_dish(message.chat.id, name.lower())
        bot.reply_to(message, f"Удалил нямку '{name}'!")
    except Exception as e:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDdnXrD9kxPdxxnq_L2Py1iZxZOrngACkWMAAr3OWUqVmkfU6UBnezYE")
        bot.reply_to(message, "Ошибка: убедись что правильно записала нямку")
        print(e)

@bot.message_handler(func=lambda message: message.text == "Нанямканое")
def daily_summary(message):
    summary = db.get_daily_summary(message.chat.id)
    if summary and summary['total_calories'] is not None:
        bot.reply_to(message, f"Сегодня ты снямкала:\n"
                              f"Калорий: {summary['total_calories']}\n"
                              f"Белков: {summary['total_protein']}\n"
                              f"Жиров: {summary['total_fat']}\n"
                              f"Углеводов: {summary['total_carbs']}\n"
                              f"Нямки: {summary['consumed_dishes']}")
    else:
        bot.reply_to(message, "Ты сегодня еще не нямкала")

@bot.message_handler(func=lambda message: message.text == "Сбросит усьо")
def reset_data(message):
    db.reset_daily_data(message.chat.id)
    bot.reply_to(message, "Сбросил список нямок")
    
@bot.message_handler(func=lambda message: message.text.startswith('+'))
def add_consumed(message):
    try:
        input_text = message.text[1:].strip()
        if ' ' in input_text:
            dish_name, grams = input_text.rsplit(' ', 1)
            grams = float(grams)
        else:
            dish_name = input_text
            grams = 100
        if db.add_consumed_dish(message.chat.id, dish_name.lower(), grams):
            bot.reply_to(message, f"Записал что ты снямкала '{dish_name}' сегодня")
        else:
            bot.reply_to(message, f"Не нашел '{dish_name}' в твоем меню\n"
            f"Добавь нямку через кнопочку")
    except ValueError:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDdnXrD9kxPdxxnq_L2Py1iZxZOrngACkWMAAr3OWUqVmkfU6UBnezYE")
        bot.reply_to(message, "Ошибка: я тут циферки прикинул, не пойму сколько нямки ты слопала...")

@bot.message_handler(func=lambda message: message.text == "Мое меню")
def get_menu(message):
    menu_list = db.get_menu(message.chat.id)
    if menu_list and menu_list['menu_values'] is not None:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDVnXrDgrBvabxkVE3Gk7iObN9kPFwAC5FsAAnJ1eUpg2xpQRRYGsjYE")
        bot.reply_to(message, menu_list['menu_values'])
    else:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDdnXrD9kxPdxxnq_L2Py1iZxZOrngACkWMAAr3OWUqVmkfU6UBnezYE")
        bot.reply_to(message, "Список нямок пуст!")

@bot.message_handler(func=lambda message: message.text in ["Кусь", "кусь"])
def remove_dish_init(message):
    bot.reply_to(message,  "Эээ, это тя кусь!")
    bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDNnXrDVPowE35DdskQWJmvDrrS5hwACh1gAAlx2YUpfskIKeOiQ4zYE")
    
@bot.message_handler(func=lambda message: message.text == "История нямканья")
def select_history_date(message):
    bot.send_message(message.chat.id, "Напиши день, за который ты хочешь узнать нямки в формате `дд.мм.гггг`",
                     parse_mode='Markdown')
    bot.register_next_step_handler(message, history_summary)

def history_summary(message):
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y").date()
        summary = db.get_history_summary(message.chat.id, date)
        if summary and summary['total_calories'] is not None:
            bot.reply_to(message, f"За {message.text} ты снямкала:\n"
                              f"Калорий: {summary['total_calories']}\n"
                              f"Белков: {summary['total_protein']}\n"
                              f"Жиров: {summary['total_fat']}\n"
                              f"Углеводов: {summary['total_carbs']}\n"
                              f"Нямки: {summary['consumed_dishes']}")
        else:
            bot.reply_to(message, f"Нет инфы за {message.text} (((")
    except ValueError as e:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAENVDdnXrD9kxPdxxnq_L2Py1iZxZOrngACkWMAAr3OWUqVmkfU6UBnezYE")
        bot.reply_to(message, "Ошибка: шось дата неправильная... Правильно введи дату, например `01.01.1001`")

bot.polling()
