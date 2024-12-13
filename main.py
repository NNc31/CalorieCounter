import telebot
from db import Database
from dotenv import load_dotenv

load_dotenv()

import os

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

db = Database()
db.create_tables()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    db.add_user(message.chat.id)
    bot.reply_to(message, "Привет! Давай считать сколько ты нямкаешь. Вот что я умею:\n"
                          "/add_dish - добавить нямку\n"
                          "/summary - посмотреть сколько снямкала\n"
                          "/reset - сбросить все нямки за сегодня\n"
                          "/menu - список всех нямок\n"
                          "/remove_dish - удалить нямку\n\n"
                          "После добавления нямки в меню напиши `+панан` и я запишу, что ты снямкала панан\n"
                          "Если нямка весовая - вводи `+блинчик 200` и я запишу что ты снямкала 200г блинчиков")


@bot.message_handler(commands=['add_dish'])
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
        db.add_dish(message.chat.id, name, int(calories), float(protein), float(fat), float(carbs))
        bot.reply_to(message, f"Нямку '{name}' добавил!")
    except Exception as e:
        bot.reply_to(message, "Ошибка: убедиcm, что всё ввела правильно\nНапример: Панан, 100, 1.1, 5.5, 10.1")
        print(e)

@bot.message_handler(commands=['remove_dish'])
def remove_dish_init(message):
    bot.send_message(message.chat.id, "Напиши название нямки для удаления", parse_mode='Markdown')
    bot.register_next_step_handler(message, remove_dish)

def remove_dish(message):
    try:
        name = message.text
        db.remove_dish(message.chat.id, name)
        bot.reply_to(message, f"Удалил нямку '{name}'!")
    except Exception as e:
        bot.reply_to(message, "Ошибка: убедись что правильно записала нямку")
        print(e)

@bot.message_handler(commands=['summary'])
def daily_summary(message):
    summary = db.get_daily_summary(message.chat.id)
    if summary and summary['total_calories'] is not None:
        bot.reply_to(message, f"Сегодня ты снямкала:\n"
                              f"Калорий: {summary['total_calories']}\n"
                              f"Белков: {summary['total_protein']}\n"
                              f"Жиров: {summary['total_fat']}\n"
                              f"Углеводов: {summary['total_carbs']}")
    else:
        bot.reply_to(message, "Ты сегодня еще не нямкала")

@bot.message_handler(commands=['reset'])
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
        if db.add_consumed_dish(message.chat.id, dish_name, grams):
            bot.reply_to(message, f"Записал что ты снямкала '{dish_name}' сегодня")
        else:
            bot.reply_to(message, f"Не нашел '{dish_name}' в твоем меню\n"
            f"Добавь нямку через /add_dish.")
    except ValueError:
        bot.reply_to(message, "Ошибка: я тут циферки прикинул, не пойму сколько нямки ты слопала...")

@bot.message_handler(commands=['menu'])
def get_menu(message):
    menu_list = db.get_menu(message.chat.id)
    if menu_list and menu_list['menu_values'] is not None:
        bot.reply_to(message, menu_list['menu_values'])
    else:
        bot.reply_to(message, "Список нямок пуст!")

# Запуск бота
bot.polling()
