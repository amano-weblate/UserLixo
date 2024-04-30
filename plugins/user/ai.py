import json
import os
import re

from EdgeGPT.EdgeGPT import Chatbot, ConversationStyle
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from BingImageCreator import ImageGen
import io
from tempfile import NamedTemporaryFile
from utils import http
from locales import use_lang
from gemini import Gemini
import markdown
from telegraph.aio import Telegraph
from config import plugins, bot
from db import Config

bing_instances = {}
bard_instances = {}

async def filter_bing_logic(flt, client:Client, message: Message):
    if message:
        if message.reply_to_message_id and message.reply_to_message_id in bing_instances:
            return True
        else:
            return False

filter_bing = filters.create(filter_bing_logic)

async def filter_bard_logic(flt, client:Client, message: Message):
    if message:
        if message.reply_to_message_id and message.reply_to_message_id in bard_instances:
            return True
        else:
            return False

filter_bard = filters.create(filter_bard_logic)

async def update_page(taccount, path, page_title, page_content, author_info):
    if path:
        oldt = (await taccount.get_page(path))["content"]
        page = await taccount.edit_page(path, title=page_title, html_content=oldt+page_content, **author_info)
    else:
        page = await taccount.create_page(page_title, html_content=page_content, **author_info)
    return page

async def process_mode(mtext, mmode):
    if mtext.startswith("-m"):
        mmode = "message"
        mtext = mtext[3:]
    elif mtext.startswith("-t"):
        mmode = "telegraph"
        mtext = mtext[3:]
    elif mtext.startswith("-v"):
        mmode = "voice"
        mtext = mtext[3:]
    elif not mmode:
        mmode = (await Config.get_or_create(id="bard"))[0].value
        if not mmode:
            mmode = "message"
    return mmode, mtext

# This function is triggered when the ".bing" command is sent by a sudoer
@Client.on_message((filters.command("bing", prefixes=".") | filter_bing) & filters.sudoers)
@use_lang()
async def bing(c: Client, m: Message, t):
    mmode = None
    try:
        if m.reply_to_message_id and m.reply_to_message_id in bing_instances:
            bot, taccount, path, mmode = bing_instances.pop(m.reply_to_message_id)
            mtext = m.text
        else:
            bot = await Chatbot.create(cookies=json.load(open('./cookies.json', 'r', encoding='utf-8'))) if os.path.exists('./cookies.json') else await Chatbot.create()
            taccount = Telegraph()
            await taccount.create_account(short_name="EdgeGPT")
            path = None
            if m.reply_to_message and m.reply_to_message.text:
                mtext = m.reply_to_message.text
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            elif m.reply_to_message and m.reply_to_message.caption:
                mtext = m.reply_to_message.caption
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            elif m.reply_to_message and m.reply_to_message.poll:
                mtext = m.reply_to_message.poll.question+"\n"
                for n, option in enumerate(m.reply_to_message.poll.options):
                    mtext += f"\n{n+1}) {option.text}"
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            else:
                mtext = m.text.split(" ", maxsplit=1)[1]

        mmode, mtext = await process_mode(mtext, mmode)
        await m.edit(t("ai_bing_searching").format(text=f"<pre>{mtext}</pre>"))
        style = ConversationStyle.creative
        if await Config.filter(id="bing").exists():
            mode = (await Config.get(id="bing")).value
            style = ConversationStyle.balanced if mode == "balanced" else ConversationStyle.precise
        response = await bot.ask(prompt=mtext, conversation_style=style, simplify_response=True)
        links = re.findall(r'\[(\d+)\.\s(.*?)\]\((.*?)\)', response["sources_text"])
        text = response["text"]
        for link in links:
            text = text.replace(f"[^{link[0]}^]", f'<a href="{link[2]}">[{link[0]}]</a>')
        ttext = markdown.markdown(response["text"])

        page_content = f'<blockquote>{mtext}</blockquote>\n\n{ttext}'
        page_title = f"EdgeGPT-userlixo-{c.me.first_name}"
        author_info = {"author_name": "EdgeGPT", "author_url": "https://t.me/UserLixo"}

        page = await update_page(taccount, path, page_title, page_content, author_info)
        
        if len(text) > 4096 or mmode == "telegraph":
            newm = await m.edit(f'<pre>{mtext}</pre>\n\n{page["url"]}')
        else:
            newm = await m.edit(f"<pre>{mtext}</pre>\n\n{text[:4096]}")
        
        bing_instances[newm.id] = [bot, taccount, page["path"], mmode]
    except Exception as e:
        await m.edit(str(e))

# This function is triggered when the ".bingimg" command is sent by a sudoer
@Client.on_message(filters.command("bingimg", prefixes=".") & filters.sudoers)
@use_lang()
async def bingimg(c: Client, m: Message, t):
    text = m.text.split(" ", maxsplit=1)[1] if len(m.text.split(" ", maxsplit=1)) >= 2 else m.reply_to_message.text if m.reply_to_message else None
    if not text:
        return await m.edit(t("ai_no_text"))

    await m.edit(t("ai_making_image").format(text=text))
    cookies = json.load(open('./cookies.json', 'r', encoding='utf-8'))
    cookie_u = next((cookie["value"] for cookie in cookies if cookie["name"] == "_U"), None)
    cookie_SRCHHPGUSR = next((cookie["value"] for cookie in cookies if cookie["name"] == "SRCHHPGUSR"), None)
    img_gen = ImageGen(auth_cookie=cookie_u, auth_cookie_SRCHHPGUSR=cookie_SRCHHPGUSR, quiet=True, all_cookies=cookies)

    try:
        urls = img_gen.get_images(str(text))
        for aurl in urls:
            if aurl.endswith('.svg'):
                urls.remove(aurl)

    except Exception as e:
        return await m.edit(str(e))

    photos = [InputMediaPhoto(io.BytesIO((await http.get(i)).content), caption=text if n == 0 else None) for n, i in enumerate(urls)]
    if m.reply_to_message:
        if m.from_user.is_self:
            await m.delete()
        await m.reply_to_message.reply_media_group(photos)
    else:
        await m.reply_media_group(photos)

@Client.on_message((filters.command(["bard", "gemini"], prefixes=".") | filter_bard) & filters.sudoers)
@use_lang()
async def bardc(c: Client, m: Message, t):
    teleimg = None
    mmode = None
    try:
        if m.reply_to_message_id and m.reply_to_message_id in bard_instances:
            bot, taccount, path, mmode = bard_instances.pop(m.reply_to_message_id)
            mtext = m.text
        else:
            taccount = Telegraph()
            await taccount.create_account(short_name="Gemini")
            path = None
            cookies = json.load(open("bard_coockies.json", "r"))
            cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
            bot = Gemini(cookies=cookies)
            if m.reply_to_message and m.reply_to_message.text:
                mtext = m.reply_to_message.text
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            elif m.reply_to_message and m.reply_to_message.caption:
                mtext = m.reply_to_message.caption
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            elif m.reply_to_message and m.reply_to_message.poll:
                mtext = m.reply_to_message.poll.question+"\n"
                for n, option in enumerate(m.reply_to_message.poll.options):
                    mtext += f"\n{n+1}) {option.text}"
                if len(m.text.split(" ", maxsplit=1)) >= 2:
                    mtext = m.text.split(" ", maxsplit=1)[1] + "\n" + f"\"{mtext}\""
            else:
                mtext = m.text.split(" ", maxsplit=1)[1]
        
        mmode, mtext = await process_mode(mtext, mmode)
        await m.edit(t("ai_bard_searching").format(text=f"<pre>{mtext}</pre>"))
        if m.reply_to_message and (m.reply_to_message.photo or m.reply_to_message.sticker):
            file = await c.download_media(m.reply_to_message, in_memory=True)
            file_bytes = bytes(file.getbuffer())
            try:
                with NamedTemporaryFile() as f:
                    f.write(file_bytes)
                    teleimg = await taccount.upload_file(f.name)
            except:
                pass
        else:
            file_bytes = None
        response = bot.generate_content(mtext, image=file_bytes)
        text = f'<pre>{mtext}</pre>\n\n{response.text}'

        ttext = markdown.markdown(response.text)
        for i in response.web_images:
            ttext = ttext.replace(i.title, f"<img src='{str(i.url)}'>")

        page_content =  f"<img src='https://telegra.ph{teleimg[0]['src']}'><br>\n\n" if teleimg else ""
        page_content += f'<blockquote>{mtext}</blockquote>\n\n{ttext}'
        page_title = f"Gemini-userlixo-{c.me.first_name}"
        author_info = {"author_name": "Gemini", "author_url": "https://t.me/UserLixo"}

        page_content = re.sub(r'<h2.*?>(.*?)</h2>', r'<h3>\1</h3>', page_content)
        page = await update_page(taccount, path, page_title, page_content, author_info)
        if len(text) > 4096 or mmode == "telegraph":
            newm = await m.edit(f'<pre>{mtext}</pre>\n\n{page["url"]}')
        elif response.web_images:
            photos = [InputMediaPhoto(str(i.url), caption=text[:4096] if n == 0 else None) for n, i in enumerate(response.web_images)]
            newm = (await m.reply_media_group(photos))[0]
        else:
            newm = await m.edit(text[:4096])

        bard_instances[newm.id] = [bot, taccount, page["path"], mmode]
    except Exception as e:
        await m.edit(str(e))

plugins.append("bing")

@bot.on_callback_query(filters.regex(r"\bconfig_plugin_bing\b"))
@use_lang()
async def config_bing(c: Client, cq: CallbackQuery, t):
    await cq.edit(t("bing_settings"), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t("ai_mode"),
                callback_data="config_plugin_ai_mode"
            )
        ], [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugins"
            )
        ]
    ]))

@bot.on_callback_query(filters.regex(r"\bconfig_plugin_ai_mode\b"))
@use_lang()
async def config_ai_mode(c: Client, cq: CallbackQuery, t):
    await cq.edit(t("ai_mode_choose"), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t("ai_mode_creative"),
                callback_data="config_plugin_ai_mode_creative"
            ),
            InlineKeyboardButton(
                text=t("ai_mode_balanced"),
                callback_data="config_plugin_ai_mode_balanced"
            ),
            InlineKeyboardButton(
                text=t("ai_mode_precise"),
                callback_data="config_plugin_ai_mode_precise"
            )
        ] , [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugin_bing"
            )
        ]
    ]))

@bot.on_callback_query(filters.regex(r"config_plugin_ai_mode_"))
@use_lang()
async def config_ai_modes(c: Client, cq: CallbackQuery, t):
    await Config.get_or_create(id="bing")
    mode = cq.data.split("_")[-1]
    if mode == "creative":
        await Config.filter(id="bing").update(value="creative")
    elif mode == "balanced":
        await Config.filter(id="bing").update(value="balanced")
    elif mode == "precise":
        await Config.filter(id="bing").update(value="precise")
    await cq.edit(t("ai_mode_changed").format(style=t(f"ai_mode_{mode}")), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugin_bing"
            )
        ]
    ]))

plugins.append("bard")

@bot.on_callback_query(filters.regex(r"\bconfig_plugin_bard\b"))
@use_lang()
async def config_bard(c: Client, cq: CallbackQuery, t):
    await cq.edit(t("bard_settings"), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t("ai_mode"),
                callback_data="config_plugin_bard_mode"
            )
        ],[
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugins"
            )
        ]
    ]))

@bot.on_callback_query(filters.regex(r"\bconfig_plugin_bard_mode\b"))
@use_lang()
async def config_bard_mode(c: Client, cq: CallbackQuery, t):
    bc = await Config.get_or_create(id="bard")
    if bc[0].value:
        mode = bc[0].value
    else:
        mode = "message"
    await cq.edit(t("ai_mode_choose"), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t(f"ai_mode_{mode}"),
                callback_data="config_plugin_bard_mode_toggle"
            ),
        ], [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugin_bard"
            )
        ]
    ]))

@bot.on_callback_query(filters.regex(r"\bconfig_plugin_bard_mode_toggle\b"))
@use_lang()
async def config_bard_mode_toggle(c: Client, cq: CallbackQuery, t):
    bc = await Config.get(id="bard")
    if bc.value:
        mode = bc.value
    else:
        mode = "message"
    modes = ["message", "voice", "telegraph"]
    mode = modes[(modes.index(mode)+1)%len(modes)]
    
    await Config.filter(id="bard").update(value=mode)
    await cq.edit(t("ai_mode_choose"), reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=t(f"ai_mode_{mode}"),
                callback_data="config_plugin_bard_mode_toggle"
            ),
        ], [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="config_plugin_bard"
            )
        ]
    ]))