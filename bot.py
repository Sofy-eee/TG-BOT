import telebot
import datetime
import re
from dateparser import parse
import time

TOKEN = "7781837661:AAHXKNm-M2TrNlaS9h0QmSaSXCmiIbKODDY"
bot = telebot.TeleBot(TOKEN)

reminders = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Напиши: 'через 5 часов встреча' (я спрошу про сборы и дорогу) или 'напомни завтра в 12:30 написать маме' (я просто сохраню напоминание)!")

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, "Команды бота:\n/start - Начать работу с ботом\n/list - Показать все напоминания\n/delete - Удалить напоминание\n/help - Показать это сообщение")

@bot.message_handler(commands=['list'])
def list_reminders(message):
    user_id = message.chat.id
    if user_id not in reminders or not reminders[user_id]:
        bot.send_message(user_id, "У тебя нет активных напоминаний.")
    else:
        response = "Твои напоминания:\n"
        for idx, reminder in enumerate(reminders[user_id], start=1):
            time_str = reminder[0].strftime('%d.%m.%Y %H:%M')
            response += f"{idx}. {reminder[1]} - {time_str}\n"
        bot.send_message(user_id, response)

@bot.message_handler(commands=['delete'])
def delete_reminder(message):
    user_id = message.chat.id
    if user_id not in reminders or not reminders[user_id]:
        bot.send_message(user_id, "У тебя нет активных напоминаний.")
    else:
        response = "Какое напоминание удалить? Укажи номер:\n"
        for idx, reminder in enumerate(reminders[user_id], start=1):
            time_str = reminder[0].strftime('%d.%m.%Y %H:%M')
            response += f"{idx}. {reminder[1]} - {time_str}\n"
        bot.send_message(user_id, response)
        bot.register_next_step_handler(message, confirm_delete)

def confirm_delete(message):
    user_id = message.chat.id
    try:
        idx = int(message.text) - 1
        if 0 <= idx < len(reminders[user_id]):
            deleted = reminders[user_id].pop(idx)
            bot.send_message(user_id, f"Напоминание '{deleted[1]}' удалено.")
        else:
            bot.send_message(user_id, "Неверный номер напоминания.")
    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введи номер напоминания.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()
    user_id = message.chat.id

    time_match = re.search(r'через (\d+)\s*(минут|час|часа|часов|день|дня|дней)', text)
    date_match = re.search(r'напомни\s+(\d{2}\.\d{2}\.\d{4}|сегодня|завтра|послезавтра|через \d+ (дня|дней))', text)
    
    if time_match:
        num = int(time_match.group(1))
        unit = time_match.group(2)
        
        delta = {'минут': datetime.timedelta(minutes=num),
                 'час': datetime.timedelta(hours=num),
                 'часа': datetime.timedelta(hours=num),
                 'часов': datetime.timedelta(hours=num),
                 'день': datetime.timedelta(days=num),
                 'дня': datetime.timedelta(days=num),
                 'дней': datetime.timedelta(days=num)}.get(unit)
        
        if delta:
            reminder_time = datetime.datetime.now() + delta
        else:
            bot.send_message(user_id, "Не понял время, попробуй ещё раз.")
            return
        
        event_text = re.sub(r'через\s+\d+\s*(минут|час|часа|часов|день|дня|дней)', '', text).strip()
        if not event_text:
            bot.send_message(user_id, "Что нужно напомнить?")
            return
        
        bot.send_message(user_id, "Сколько времени нужно на сборы и дорогу?")
        bot.register_next_step_handler(message, lambda msg: set_reminder(user_id, reminder_time, event_text, msg.text))
    
    elif date_match:
        now = datetime.datetime.now()
        date_text = date_match.group(1)
        event_text = text.replace(date_match.group(0), '').strip()
        
        if date_text == "послезавтра":
            reminder_time = now + datetime.timedelta(days=2)
        elif "через" in date_text:
            days = int(re.search(r'\d+', date_text).group(0))
            reminder_time = now + datetime.timedelta(days=days)
        else:
            reminder_time = datetime.datetime.strptime(date_text, "%d.%m.%Y")
            if now > reminder_time:
                bot.send_message(user_id, "Нельзя ставить напоминание в прошлом! Попробуй другую дату.")
                return
        
        if reminder_time and event_text:
            set_reminder(user_id, reminder_time, event_text)
        else:
            bot.send_message(user_id, "Не понял время, попробуй ещё раз.")
    else:
        bot.send_message(user_id, "Не понял время, попробуй ещё раз.")

def set_reminder(user_id, reminder_time, event_text, extra_time=None):
    if extra_time:
        try:
            extra_minutes = int(re.search(r'(\d+)', extra_time).group(1))
            reminder_time -= datetime.timedelta(minutes=extra_minutes)
        except AttributeError:
            bot.send_message(user_id, "Не понял время, попробуй ещё раз.")
            return
    
    reminders.setdefault(user_id, []).append((reminder_time, event_text))
    bot.send_message(user_id, f"Напоминание сохранено: '{event_text}' в {reminder_time.strftime('%H:%M %d.%m.%Y')}")

def check_reminders():
    while True:
        now = datetime.datetime.now()
        for user_id, events in list(reminders.items()):
            for event in events[:]:
                if event[0] <= now:
                    bot.send_message(user_id, f"Напоминание: {event[1]}")
                    events.remove(event)
            if not events:
                del reminders[user_id]
        time.sleep(30)

import threading
threading.Thread(target=check_reminders, daemon=True).start()

bot.polling(none_stop=True)
