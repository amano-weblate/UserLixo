from dataclasses import dataclass
from datetime import datetime

from kink import inject
from hydrogram import Client
from hydrogram.enums import ChatAction
from hydrogram.types import Message

from userlixo.modules.abstract import MessageHandler
from userlixo.utils.services.language_selector import LanguageSelector


@inject
@dataclass
class PingMessageHandler(MessageHandler):
    language_selector: LanguageSelector

    async def handle_message(self, client: Client, message: Message):
        before = datetime.now()
        await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        after = datetime.now()
        diff_ms = (after - before).microseconds / 1000

        keyboard = [[("🏓", "ping")]]
        await message.reply(f"<b>Pong!</b> <code>{diff_ms}</code><code>ms</code>", keyboard)
