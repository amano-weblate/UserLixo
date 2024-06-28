import asyncio
import io

from hydrogram import Client, filters
from hydrogram.types import Message

from locales import use_lang


@Client.on_message(filters.command("cmd", prefixes=".") & filters.sudoers)
@use_lang()
async def cmd(_, m: Message, t):
    text = m.text[5:]
    proc = await asyncio.create_subprocess_shell(
        text, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    ex = await proc.communicate()
    res = ex[0].decode().rstrip() or t("cmd_no_output")
    if len(res) > 4096:
        with io.BytesIO(str.encode(res)) as out_file:
            out_file.name = "cmd.txt"
            await m.reply_document(out_file)
    else:
        await m.edit(res)
