import asyncio #for async computing
from telebot.async_telebot import AsyncTeleBot #telegram bot api
from gtts import gTTS #spech syntesis
import time
import langid #detectin language
import os #files manipulating
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.asyncio_storage import StateMemoryStorage
from telebot import asyncio_filters
import music_tag
import logging
import requests as rq
import pdfplumber #pdf support

#variables
cwd = os.getcwd()
adds=False
token=str(os.environ.get("token"))
bot=AsyncTeleBot(token)
headers={'User-Agent':str(os.environ.get("headers"))}
max_letters=int(os.environ.get("max_letters", 7500))
thumb_path=str(os.environ.get("thumb_path", f'{cwd}/resources/thumb2.jpg'))
botName=str(os.environ.get("botName", '@TextIntoAudio_Bot'))
inlineAd=f'Ad: {adds}' if adds else ''

#states
class lang(StatesGroup):
    lang=State()
    str=State()

#functions
async def text_to_mp3(text, lang, message):
    result_message = await bot.send_message(message.chat.id, f'<i>Processing...</i> {lang = }', parse_mode='HTML', disable_web_page_preview=True,reply_to_message_id=message.id)
    path=f'{cwd}/tmp/{message.chat.id}-{message.id}.mp3'
    if len(text)>max_letters:
        e=f'Too many letters in text! Limit is {max_letters}'
        send_error(e, result_message)
        return(e)
    try:
        start_time = time.time()
        gTTS(text=text.replace('/n',''), lang=lang).save(path)
        logging.info(f"Processing time = {time.time()-start_time}")
    except Exception as e:
        send_error(e, result_message)
        os.remove(path)
        return(e)
    f = music_tag.load_file(path)
    f['artist'] = botName
    f['title'] = f'{lang}TextToMP3'
    f['lyrics'] = text
    f.save()
    with open(path, 'rb') as doc, open(thumb_path, 'rb') as thumb:
        await bot.send_document(message.chat.id, doc,thumb=thumb, caption=f"Made by {botName}\n{inlineAd}",parse_mode='HTML',reply_to_message_id=message.id)
    await bot.delete_message(chat_id=message.chat.id, message_id=result_message.id, timeout=180)
    os.remove(path)

def download_file(url,name): #file download from url
    with rq.get(url, stream=True, timeout=3600,headers=headers) as r:
        r.raise_for_status()
        with open(name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)
    return name

async def send_error(e, result_message):
    logging.error(e)
    await bot.edit_message_text(chat_id=message.chat.id, message_id=result_message.id, text=f"<b>Something went wrong!</b>\n<i>Error: </i>Too many letters in text! Limit is <u>{max_letters}</u>", parse_mode='HTML')

# message handlers
@bot.message_handler(commands=['start'])
async def start_message(message):
    await bot.send_message(message.chat.id, "Hi! Send me text/.txt/.pdf and i'll convert it to audio")

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
        await text_to_mp3(message.text, data['lang'], message)


@bot.message_handler()
async def process_message(message):
    lang =  message.text.split('@∆=')[-1] if '@∆=' in message.text else langid.classify(message.text)[0]
    text = message.text.split('@∆=')[0]
    await text_to_mp3(text, lang, message)

@bot.message_handler(content_types=['document'])
async def process_document(message):
    file_id = message.document.file_id
    file_path = await bot.get_file(file_id)
    extension = file_path.file_path.split('.')[-1].lower()
    name=f'{cwd}/tmp/{file_id}.{extension}'
    download_file(f'https://api.telegram.org/file/bot{token}/{file_path.file_path}',name)
    if extension == 'txt':
        with open(name, 'rb') as file:
            text =' '.join(l.decode() for l in file.readlines())
    elif extension == 'pdf':
        with pdfplumber.PDF(open(name, 'rb')) as file:
            text=' '.join([page.extract_text() for page in file.pages])
    os.remove(name)
    await text_to_mp3(text, langid.classify(text)[0], message)


#boot
def main():
    if not os.path.exists(f'{os.getcwd()}/tmp'):
        try:
            os.mkdir(f'{os.getcwd()}/tmp')
        except Exception as e:
            logging.error(e)
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    while True:
        try:
            asyncio.run(bot.polling(none_stop=True, timeout=180, interval=1))
        except Exception as e:
            logging.error(e)
            time.sleep(10)

if __name__ == '__main__':
    main()


