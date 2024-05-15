import html
import io
import re
import traceback
from contextlib import redirect_stdout

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from locales import use_lang

@Client.on_message(filters.command("exec", prefixes=".") & filters.sudoers)
@use_lang()
async def execs(c: Client, m: Message, t):
    strio = io.StringIO()
    code = re.split(r"[\n ]+", m.text, 1)[1]
    exec(
        "async def __ex(c: Client, m: Message): "
        + " ".join("\n " + l for l in code.split("\n"))
    )
    with redirect_stdout(strio):
        try:
            await locals()["__ex"](c, m)
        except:
            return await m.reply_text(
                html.escape(traceback.format_exc()), parse_mode=ParseMode.HTML
            )

    if strio.getvalue():
        out = html.escape(strio.getvalue())
    else:
        out = t("exec_seucess")
    if len(out) > 4096:
        with io.BytesIO(str.encode(out)) as out_file:
            out_file.name = "exec.txt"
            await m.reply_document(out_file)
    else:
        await m.edit(f"<code>{out}</code>", parse_mode=ParseMode.HTML)

