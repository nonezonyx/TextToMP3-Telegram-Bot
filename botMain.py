import configparser #for config file
import asyncio #for async computing
from telebot.async_telebot import AsyncTeleBot #telegram bot api
from gtts import gTTS #spech syntesis
import time
from langdetect import detect #detectin language
import os #files manipulating
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.asyncio_storage import StateMemoryStorage
from telebot import asyncio_filters

#read config data
config = configparser.ConfigParser()
config.read("config.ini")

#variables
token=str(config["bot"]["token"])
bot=AsyncTeleBot(token)
headers={'User-Agent':str(config["bot"]["header"])}

class lang(StatesGroup):
    lang=State()
    str=State()

@bot.message_handler(commands='setfixedlanguage')
async def setlang_command(message):
    await bot.set_state(message.from_user.id, lang.lang, message.chat.id)
    await bot.send_message(message.chat.id, "Send me language code. For instance 'en', 'ru'")
@bot.message_handler(state=lang.lang)
async def set_fixed_lang(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
       data['lang'] = message.text.lower()
    await bot.send_message(message.chat.id, f"Current language is <b>{data['lang']}</b>.", parse_mode='HTML')
    await bot.set_state(message.from_user.id, lang.str, message.chat.id)
@bot.message_handler(state=lang.str, commands='language')
async def getlang_command(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
       await bot.send_message(message.chat.id, f"Current language is <b>{data['lang']}</b>.", parse_mode='HTML')
@bot.message_handler(commands='language')
async def getlang_command(message):
    await bot.send_message(message.chat.id, f"Language is not fixed.", parse_mode='HTML')
#cancel
@bot.message_handler(state="*", commands='cancel')
async def any_state(message):
    await bot.send_message(message.chat.id, "You cancelled operation.")
    await bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(state=lang.str)
async def process_fixed(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        lang=data['lang']
        result_message = await bot.send_message(message.chat.id, f'<i>Processing...</i> <b>{lang}</b>', parse_mode='HTML',disable_web_page_preview=True,reply_to_message_id=message.id)
        gTTS(text=message.text.replace('/n',''), lang=lang).save(f'tmp/{message.chat.id}-{message.id}.mp3')
        with open(f'tmp/{message.chat.id}-{message.id}.mp3', 'rb') as doc:
            await bot.send_document(message.chat.id, doc, reply_to_message_id=message.id, caption=f"<b>{lang}</b>", parse_mode='HTML')
    await bot.delete_message(chat_id=message.chat.id, message_id=result_message.id, timeout=180)
    os.remove(f'tmp/{message.chat.id}-{message.id}.mp3')


@bot.message_handler()
async def process_message(message):
    lang =  message.text.split('@∆=')[-1] if '@∆=' in message.text else detect(message.text)
    result_message = await bot.send_message(message.chat.id, f'<i>Processing...</i> {lang}', parse_mode='HTML', disable_web_page_preview=True,reply_to_message_id=message.id)
    text = message.text.split('@∆=')[0]
    gTTS(text=text.replace('/n',''), lang=lang).save(f'tmp/{message.chat.id}-{message.id}.mp3')
    with open(f'tmp/{message.chat.id}-{message.id}.mp3', 'rb') as doc:
        await bot.send_voice(message.chat.id, doc, reply_to_message_id=message.id, caption=f"<b>{lang}</b>", parse_mode='HTML')
    await bot.delete_message(chat_id=message.chat.id, message_id=result_message.id, timeout=180)
    os.remove(f'tmp/{message.chat.id}-{message.id}.mp3')

#boot
def main():
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    bot.add_custom_filter(asyncio_filters.IsDigitFilter())
    while True:
        try:
            #text_to_mp3().save('audio.mp3')
            asyncio.run(bot.polling(none_stop=True, timeout=180, interval=1))
        except Exception as e:
            print(e)
            time.sleep(10)

if __name__ == '__main__':
    main()
