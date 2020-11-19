import asyncio
import html
import os
import re

from config import sudoers
from pyrogram import Client, filters
from utils import shell_exec

@Client.on_message(filters.su_cmd(r"(?P<command>cmd|sh)\s+(?P<code>.+)", flags=re.S))
async def cmd(c, m):
    lang = m.lang
    act = m.edit if await filters.me(c,m) else m.reply
    
    code = m.matches[0]['code']
    command = m.matches[0]['command']
    
    result, process = await shell_exec(code)
    output = result or lang.executed_cmd
    output = html.escape(output) # escape html special chars
    
    text = ''
    for line in output.splitlines():
        text += f"<code>{line}</code>\n"
    
    if command == 'cmd':
        return await act(text)
    await m.reply(text)