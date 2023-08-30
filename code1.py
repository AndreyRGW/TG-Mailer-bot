from telegram import Update, Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, ContextTypes
import re

# Here you need to specify your bot token
BOT_TOKEN = '1234:ABCD'

# This is where the list of chats to be sent out will be stored
# chat_ids = set([-1001414736207])
# todo: use dictionary instead of set, so we can store chat title too
# explicitly determine types for better readability
chat_dict: dict[int, str] = {-id: 'name'}

# This will store the list of users on the whitelist
whitelist = ['username', 'username', 'username']  # Replace with real @username

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['waiting_for_reply'] = False
    
    user = update.effective_user
    
    
    if user.username in whitelist:
        keyboard = [
            [InlineKeyboardButton('Send out messages', callback_data='send_messages')],
            [InlineKeyboardButton('Settings', callback_data='settings')],
            ]

            
        # keyboard = [[InlineKeyboardButton("settings", callback_data='settings')]] 
        if update.message.chat.type == 'private':
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('Hi! You are on the whitelist.', reply_markup=reply_markup)
        else:
            await update.message.reply_text('Chat added.')
            add_chat(chat=update.message.chat)
            print(user.username,  'added bot to the chat ', update.message.chat.title)
    else:
        await update.message.reply_text('Verification failed.')

# Adds the group's chat to the list of maintained chats if it has not been added yet
def add_chat(chat: Chat):
    
    # check if its a group and not a dm chat
    if str(chat.id)[:4] == '-100':
        # database.add_chat(id=chat.id, title=chat.title)
        # check if dictionary already contains this chat id

        if chat.id not in chat_dict:
            title = (chat.title[:30] + '..') if len(chat.title) > 30 else chat.title
            chat_dict.update({chat.id: title})
            print(f'added chat {chat.id} to chat_dict')
        else:
            print(f'chat {chat.id} already in chat_dict')


# Handler for pressing the "Settings" button
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    keyboard = []
    for chat_id, chat_title in chat_dict.items():
        checked = '✅' if chat_id in context.user_data.get('selected_chats', []) else ''
        callback = f'selected_chat_{str(chat_id)}'
        keyboard.append([InlineKeyboardButton(f"{checked} Chat: {chat_title}", callback_data=callback)]) 

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Select chats to send:', reply_markup=reply_markup)

# Handler for selecting chats for mailing
async def chat_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print('chat_selected')

    query = update.callback_query
    await query.answer()
    chat_id = int(query.data[14:])
    selected_chats = context.user_data.get('selected_chats', [])
    if chat_id in selected_chats:
        selected_chats.remove(chat_id)
    else:
        selected_chats.append(chat_id)
    context.user_data['selected_chats'] = selected_chats
    await settings(update, context)

# Handler for text messages
async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'selected_chats' in context.user_data and context.user_data['waiting_for_reply']:
        context.user_data['message_to_send'] = update.effective_message
        print('call forward_message')
        await forward_message(update, context)  # Call the mailer handler
        context.user_data['waiting_for_reply'] = False
    else:
        if 'selected_chats' not in context.user_data:
            return
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text='Reply to this message to mail it.')
        context.user_data['waiting_for_reply'] = True

# Old message response handler ▼
# Mailing list message response handler
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'selected_chats' in context.user_data and 'message_to_send' in context.user_data:
        message: Message = context.user_data['message_to_send']
        selected_chats = context.user_data['selected_chats']
        for chat_id in selected_chats:
            print('trying to send message to chat_id ', chat_id)
            if message.text:
                await context.bot.send_message(chat_id, text=message.text)
            elif message.photo:
                largest_photo = message.photo[-1]
                await context.bot.send_photo(chat_id, photo=largest_photo.file_id, caption=message.caption)
            elif message.media_group:
                for media in message.media_group:
                    if media.photo:
                        largest_photo = media.photo[-1]
                        await context.bot.send_photo(chat_id, photo=largest_photo.file_id, caption=media.caption)
                    elif media.document:
                        await context.bot.send_document(chat_id, document=media.document.file_id, caption=media.caption)
            elif message.document:
                await message.send_document(chat_id, document=message.document.file_id, caption=message.caption)
            print('sent message to chat_id ', chat_id)
        await context.bot.send_message(update.message.chat.id, text='The mailing is complete.')
            # del context.user_data['selected_chats']
            # del context.user_data['message_to_send']


def main() -> None:
    # Create an instance of Updater and add the handlers
    # updater = Updater(token=BOT_TOKEN, use_context=True)
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(settings, pattern='settings'))
    application.add_handler(CallbackQueryHandler(chat_selected, pattern=r'selected_chat_-\d+'), group=1)
    application.add_handler(CallbackQueryHandler(text_message, pattern='^send_messages'), group=2)

    application.add_handler(MessageHandler(filters.TEXT and ~filters.COMMAND, text_message))
    # dispatcher.add_handler(MessageHandler(Filters.all, forward_message), group=1)


    # Launch the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    # application.idle()

if __name__ == '__main__':
    main()