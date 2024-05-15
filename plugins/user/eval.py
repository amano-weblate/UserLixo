import html
import traceback

from pyrogram import Client, filters
from pyrogram.types import Message

from utils import meval
import io


@Client.on_message(filters.command("eval", prefixes=".") & filters.sudoers)
async def evals(c: Client, m: Message):
    text = m.text.split(" ", 1)[1]
    try:
        res = await meval(text, locals())
    except:
        ev = traceback.format_exc()
        if m.from_user.id == c.me.id:
            await m.edit(ev)
        else:
            await m.reply(ev)
        return
    else:
        if len(str(res)) > 4000:
            with io.BytesIO(str.encode(str(res))) as out_file:
                out_file.name = "eval.txt"
                await m.reply_document(out_file)
        else:
            await m.edit(f"<code>{html.escape(str(res))}</code>")
