import logging
import subprocess
import pytz
import sqlite3
from os import name

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.ext.dispatcher import Dispatcher

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
DEVELOPER_ID = '1395019328'
DEVELOPER_TIMEZONE = pytz.timezone('Europe/Moscow')

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
def start(update: Update, context: CallbackContext) -> None:
    """Sends explanation on how to use the bot."""
    update.message.reply_text('''
        Xin chào!
/help - danh sách lệnh
/set <seconds> - lên lịch đăng bài channel
/unset - hủy lịch
/list - xem danh sách lịch
/current_rate - xem tỷ giá chi tiết
/set_profit <vnd2rub_profit> <rub2vnd_profit> - thay đổi tỷ lệ lợi nhuận
    ''')


def get_info(context: CallbackContext) -> None:
    """
    Run subprocess to scrapy
    """
    job = context.job
    to_dev = job.context.get('to_dev', '')
    to_channel = job.context.get('to_channel', '')
    
    # context.bot.send_message(job.context, text='Bắt đầu lấy dữ liệu!')
    subprocess.run(['scrapy','crawl','autoBinanceRate','-a',f'to_dev={to_dev}','-a',f'to_channel={to_channel}'])
    # context.bot.send_message(job.context, text='Đã lấy dữ liệu xong!')


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        interval = int(context.args[0])
        if interval < 2:
            update.message.reply_text('Xin lỗi mỗi lần lấy dữ liệu phải cách nhau ít nhất 2s!')
            return

        job_name = "Update_"+str(chat_id)
        job_context = {
            'to_dev': 'n',
            'to_channel': 'y'
        }
        job_removed = remove_job_if_exists(job_name, context)
        context.job_queue.run_repeating(get_info, interval=interval, first=2, context=job_context, name=job_name)

        text = 'Lên lịch thành công!'
        if job_removed:
            text += ' Lịch cũ đã bị hủy.'
        text += f'\nĐăng bài channel mỗi {interval}s'
        text += '\nBắt đầu thực thi sau 2s ...'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')

def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_name = "Update_"+str(chat_id)
    job_removed = remove_job_if_exists(job_name, context)
    text = 'Đã hủy lịch thành công!' if job_removed else 'Hiện không có lịch nào.'
    update.message.reply_text(text)

def list_job(update: Update, context: CallbackContext) -> None:
    """List time run of all current jobs"""
    jobs = list(context.job_queue.jobs())
    msg = f'Hiện có {len(jobs)} lịch đang chạy'
    for job in jobs:
        msg += f'\n{job.name} sẽ chạy lúc {job.next_t.astimezone(DEVELOPER_TIMEZONE).strftime("%d %b %Y, %H:%M:%S")}'
    update.message.reply_text(msg)

def get_rate(update: Update, context: CallbackContext )-> None:
    """Get detail rate for dev"""
    chat_id = update.message.chat_id
    try:
        # username = context.args[0]
        job_name = "GetInfo_" + str(chat_id)
        job_removed = remove_job_if_exists(job_name, context)
        job_context = {
            'to_dev': 'y',
            'to_channel': 'n'
        }
        context.job_queue.run_once(get_info, when=2, context=job_context, name=job_name)

        text = ''
        if job_removed:
            text += 'Job cũ đã bị hủy.'
        text += '\nBắt đầu lấy dữ liệu sau 2s ...'
        update.message.reply_text(text)
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /current_rate')

def set_profit(update: Update, context: CallbackContext )-> None:
    """Set the profit for exchange"""
    try:
        vnd2rub_profit = context.args[0]
        rub2vnd_profit = context.args[1]
        # Connect to database
        connection = sqlite3.connect("data.db")
        cursor = connection.cursor()

        # Try to create table
        cursor.execute( '''
            CREATE TABLE IF NOT EXISTS vars(
                name TEXT UNIQUE,
                value INTEGER
            )
        ''' )

        # Try to update or insert variable
        cursor.execute('''
            INSERT OR REPLACE INTO vars (name, value)
            VALUES  ('vnd2rub_profit', ?)
        ''', vnd2rub_profit)

        cursor.execute('''
            INSERT OR REPLACE INTO vars (name, value)
            VALUES  ('rub2vnd_profit', ?)
        ''', rub2vnd_profit)

        connection.commit()
        connection.close()
        logging.info('Disconnected from database!')
        update.message.reply_text(f'🎉 Thay đổi tỷ lệ lợi nhuận thành công!!! 🎉\n\nTỷ lệ lợi nhuận hiện tại là: \n\n     VND-RUB: {vnd2rub_profit}%\n     RUB-VND: {rub2vnd_profit}%')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set_profit <vnd2rub_profit> <rub2vnd_profit>')

def auto_start_crawl(updater:Updater, dispatcher:Dispatcher):
    msg = '''
Server đã khởi động lại
Tự động lên lịch đăng bài channel sau mỗi 300s
Bắt đầu thực thi sau 2s ...
    '''
    updater.bot.send_message(chat_id=DEVELOPER_ID, text=msg)

    interval = 300
    job_name = "Update_"+str(DEVELOPER_ID)
    job_context = {
        'to_dev': 'n',
        'to_channel': 'y'
    }
    dispatcher.job_queue.run_repeating(get_info, interval=interval, first=2, context=job_context, name=job_name)

def main() -> None:
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("5225045930:AAHo07BayUikgm2JHyS17ArY0iryUlkR7wI")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("set", set_timer))
    dispatcher.add_handler(CommandHandler("unset", unset))
    dispatcher.add_handler(CommandHandler("list", list_job))
    dispatcher.add_handler(CommandHandler("current_rate", get_rate))
    dispatcher.add_handler(CommandHandler("set_profit", set_profit))

    # Start the Bot
    updater.start_polling()
    
    auto_start_crawl(updater, dispatcher)
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()