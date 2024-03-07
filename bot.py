import os
import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters
from CloudFlare import CloudFlare
import random
import string

# Ganti dengan token bot Telegram Anda
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_TOKEN'

# Ganti dengan API Key Cloudflare Anda
CLOUDFLARE_API_KEY = 'YOUR_CLOUDFLARE_API'
CLOUDFLARE_EMAIL = 'YOUR_CLOUDFLARE_EMAIL'
DOMAIN1= 'DOMAIN1.COM'
DOMAIN2 = 'DOMAIN2.COM'
ZONEID = 'ZONEID_DOMAIN1'
ZONEID2 = 'ZONEID_DOMAIN2'

# Dictionary untuk menyimpan alamat IP server pengguna
user_ips = {}

def start(update, context):
    user_id = update.message.from_user.id

    # Pilihan domain
    reply_keyboard = [[DOMAIN1, DOMAIN2, '/Cancel']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=user_id, text="Pilih domain:", reply_markup=markup)

    # Mengatur state agar bot tahu kita sedang menunggu pemilihan domain
    return 'wait_domain'

def cancel(update, context):
    user_id = update.message.from_user.id
    context.bot.send_message(chat_id=user_id, text="/start untuk daftar subdomain\n/delete_subdomain untuk hapus subdomain", reply_markup=ReplyKeyboardRemove())
    # Hapus data pengguna dari kamus jika ada
    if user_id in user_ips:
        del user_ips[user_id]
    return ConversationHandler.END

def wait_domain(update, context):
    user_id = update.message.from_user.id
    selected_domain = update.message.text.lower()

    if selected_domain not in [DOMAIN1, DOMAIN2, 'cancel']:
        context.bot.send_message(chat_id=user_id, text="Pilihan domain tidak valid. Silakan pilih domain yang benar.")
        return 'wait_domain'
    elif selected_domain == 'cancel':
        return cancel(update, context)

    # Initialize user_data with 'domain' key
    user_ips[user_id] = {'domain': selected_domain}

    # Menggunakan keyboard khusus untuk memudahkan input subdomain
    reply_keyboard = [['/Cancel']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=user_id, text="Masukkan subdomain :", reply_markup=markup)

    # Mengatur state agar bot tahu kita sedang menunggu subdomain
    return 'wait_subdomain'


def wait_subdomain(update, context):
    user_id = update.message.from_user.id
    user_data = user_ips[user_id]
    user_data['subdomain'] = update.message.text

    if 'domain' not in user_data:
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan. Silakan coba lagi.")
        return cancel(update, context)

    # Menggunakan keyboard khusus untuk memudahkan input IP
    reply_keyboard = [['/Cancel']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=user_id, text="Masukkan IP server Anda:", reply_markup=markup)

    # Mengatur state agar bot tahu kita sedang menunggu IP
    return 'wait_ip'

def wait_ip(update, context):
    user_id = update.message.from_user.id
    user_data = user_ips[user_id]
    user_data['ip'] = update.message.text

    if 'domain' not in user_data:
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan. Silakan coba lagi.")
        return cancel(update, context)


    # Mengelola subdomain di Cloudflare
    cf = CloudFlare(email=CLOUDFLARE_EMAIL, token=CLOUDFLARE_API_KEY)

    # Menentukan zone id berdasarkan pilihan domain
    if user_data['domain'] == DOMAIN1:
        zone_id = ZONEID
    elif user_data['domain'] == DOMAIN2:
        zone_id = ZONEID2
    else:
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan. Silakan coba lagi.")
        return cancel(update, context)

    record = {
        'type': 'A',
        'name': f"{user_data['subdomain']}.{user_data['domain']}",
        'content': user_data['ip'],
    }

    try:
        cf.zones.dns_records.post(zone_id, data=record)
        # Mengirimkan pesan ke pengguna dengan subdomain yang dibuat
        message = f"DOMAIN : `{user_data['domain']}`\nIP : `{user_data['ip']}`\n Subdomain : `{user_data['subdomain']}`\n\nSubdomain Anda :\n`{user_data['subdomain']}.{user_data['domain']}`"
        context.bot.send_message(chat_id=user_id, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error creating DNS record: {e}")
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan saat menciptakan rekaman DNS. Silakan coba lagi.")

    # Menghapus data pengguna dari kamus setelah digunakan
    del user_ips[user_id]

    return cancel(update, context)
   
def delete_subdomain(update, context):
    user_id = update.message.from_user.id

    # Pilihan domain untuk dihapus
    reply_keyboard = [[DOMAIN1, DOMAIN2, '/Cancel']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=user_id, text="Pilih domain untuk menghapus subdomain:", reply_markup=markup)

    # Mengatur state agar bot tahu kita sedang menunggu pemilihan domain
    return 'wait_delete_domain'


def wait_delete_domain(update, context):
    user_id = update.message.from_user.id
    selected_domain = update.message.text.lower()

    if selected_domain not in [DOMAIN1, DOMAIN2, 'cancel']:
        context.bot.send_message(chat_id=user_id, text="Pilihan domain tidak valid. Silakan pilih domain yang benar.")
        return 'wait_delete_domain'
    elif selected_domain == 'cancel':
        return cancel(update, context)

    user_ips[user_id] = {'domain': selected_domain}

    # Menggunakan keyboard khusus untuk memudahkan input subdomain yang akan dihapus
    reply_keyboard = [['/Cancel']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.bot.send_message(chat_id=user_id, text="Masukkan subdomain yang akan dihapus:", reply_markup=markup)

    # Mengatur state agar bot tahu kita sedang menunggu subdomain yang akan dihapus
    return 'wait_delete_subdomain'

def wait_delete_subdomain(update, context):
    user_id = update.message.from_user.id
    user_data = user_ips[user_id]
    subdomain_to_delete = update.message.text.lower()

    if 'domain' not in user_data:
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan. Silakan coba lagi.")
        return cancel(update, context)

    # Mengelola subdomain di Cloudflare
    cf = CloudFlare(email=CLOUDFLARE_EMAIL, token=CLOUDFLARE_API_KEY)

    # Menentukan zone id berdasarkan pilihan domain
    if user_data['domain'] == DOMAIN1:
        zone_id = ZONEID
    elif user_data['domain'] == DOMAIN2:
        zone_id = ZONEID2
    else:
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan. Silakan coba lagi.")
        return cancel(update, context)

    try:
        # Mengambil informasi DNS records untuk subdomain yang akan dihapus
        records = cf.zones.dns_records.get(zone_id, params={'name': f"{subdomain_to_delete}.{user_data['domain']}"})
        if records:
            # Menghapus subdomain sesuai permintaan pengguna
            cf.zones.dns_records.delete(zone_id, records[0]['id'])
            context.bot.send_message(chat_id=user_id, text=f"Subdomain `{subdomain_to_delete}` berhasil dihapus.", parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            context.bot.send_message(chat_id=user_id, text=f"Tidak dapat menemukan subdomain '{subdomain_to_delete}'.")
    except Exception as e:
        print(f"Error deleting DNS record: {e}")
        context.bot.send_message(chat_id=user_id, text="Terjadi kesalahan saat menghapus rekaman DNS. Silakan coba lagi.")

    # Menghapus data pengguna dari kamus setelah digunakan
    del user_ips[user_id]

    return cancel(update, context)

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
           'wait_domain': [MessageHandler(Filters.text & ~Filters.command, wait_domain)],
           'wait_subdomain': [MessageHandler(Filters.text & ~Filters.command, wait_subdomain)],
           'wait_ip': [MessageHandler(Filters.text & ~Filters.command, wait_ip)],
      },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    conv_handler_delete = ConversationHandler(
    entry_points=[CommandHandler('delete_subdomain', delete_subdomain)],
    states={
        'wait_delete_domain': [MessageHandler(Filters.text & ~Filters.command, wait_delete_domain)],
        'wait_delete_subdomain': [MessageHandler(Filters.text & ~Filters.command, wait_delete_subdomain)],
        'wait_domain': [MessageHandler(Filters.text & ~Filters.command, wait_domain)],
      },
      fallbacks=[CommandHandler('cancel', cancel)],
   )

    dp.add_handler(conv_handler)
    dp.add_handler(conv_handler_delete)
    
    # Mulai bot
    updater.start_polling()

    # Jalankan bot sampai pengguna menekan Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
    