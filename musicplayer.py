import os
import glob
import json
import logging
import asyncio
import youtube_dl
from pytgcalls import StreamType
from pytube import YouTube
from youtube_search import YoutubeSearch
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import Update
from pyrogram.raw.base import Update
from pytgcalls.types import AudioPiped, AudioVideoPiped
from pytgcalls.types import (
    HighQualityAudio,
    HighQualityVideo,
    LowQualityVideo,
    MediumQualityVideo
)
from pytgcalls.types.stream import StreamAudioEnded, StreamVideoEnded
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import UserAlreadyParticipant, UserNotParticipant
from helpers.queues import QUEUE, add_to_queue, get_queue, clear_queue, pop_an_item
from helpers.admin_check import *
from helpers import database.mongo

bot = Client(
    "MusicPlayer",
    bot_token = os.environ["BOT_TOKEN"],
    api_id = int(os.environ["API_ID"]),
    api_hash = os.environ["API_HASH"]
    )

client = Client(os.environ["SESSION_NAME"], int(os.environ["API_ID"]), os.environ["API_HASH"])

aj = PyTgCalls(client)

OWNER_ID = int(os.environ["OWNER_ID"])
SUPPORT = os.environ["SUPPORT"]
BOT_USERNAME = int(os.environ["BOT_USERNAME"])
MONGO_DB = int(is.environ["MONGO_DB"])

LIVE_CHATS = []


# starting the bot in pm


START_TEXT = """Hello {firstname}, I am superfast music player made from open source code running
on lag free server which make me play music for you without any lag.

I am supported by [BlueCode](https://telegram.dog/TheBlueCode) ❤️✨

Type /help to know my abilities... Add me to your groups 🙂

"""

START_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                        "Add me to your Chat", url="https://t.me/{BOT_USERNAME}?startgroup=true")
        ],
        [
            InlineKeyboardButton("Help", callback_data="help_cb"),
            InlineKeyboardButton("Support", url=f"https://t.me/{SUPPORT}")
        ],
        [
            InlineKeyboardButton("Credits", url="https://t.me/akhilprs")
        ]
    ]
)


BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("resume", callback_data="resume"),
            InlineKeyboardButton("pause", callback_data="pause"),
            InlineKeyboardButton("skip", callback_data="skip"),
            InlineKeyboardButton("end", callback_data="end"),
        ],
        [
            InlineKeyboardButton("❌ Close ❌", callback_data="close")
        ]
    ]
)

async def skip_current_song(chat_id):
    if chat_id in QUEUE:
        chat_queue = get_queue(chat_id)
        if len(chat_queue) == 1:
            await app.leave_group_call(chat_id)
            clear_queue(chat_id)
            return 1
        else:
            title = chat_queue[1][0]
            duration = chat_queue[1][1]
            link = chat_queue[1][2]
            playlink = chat_queue[1][3]
            type = chat_queue[1][4]
            Q = chat_queue[1][5]
            thumb = chat_queue[1][6]
            if type == "Audio":
                await app.change_stream(
                    chat_id,
                    AudioPiped(
                        playlink,
                    ),
                )
            elif type == "Video":
                if Q == "high":
                    hm = HighQualityVideo()
                elif Q == "mid":
                    hm = MediumQualityVideo()
                elif Q == "low":
                    hm = LowQualityVideo()
                else:
                    hm = MediumQualityVideo()
                await app.change_stream(
                    chat_id, AudioVideoPiped(playlink, HighQualityAudio(), hm)
                )
            pop_an_item(chat_id)
            await bot.send_photo(chat_id, photo = thumb,
                                 caption = f"🕕 <b>Duration:</b> {duration}",
                                 reply_markup = BUTTONS)
            return [title, link, type, duration, thumb]
    else:
        return 0


async def skip_item(chat_id, lol):
    if chat_id in QUEUE:
        chat_queue = get_queue(chat_id)
        try:
            x = int(lol)
            title = chat_queue[x][0]
            chat_queue.pop(x)
            return title
        except Exception as e:
            print(e)
            return 0
    else:
        return 0


@aj.on_stream_end()
async def on_end_handler(_, update: Update):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        await skip_current_song(chat_id)

@aj.on_closed_voice_chat()
async def close_handler(client: PyTgCalls, chat_id: int):
    if chat_id in QUEUE:
        clear_queue(chat_id)

async def yt_video(link):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-g",
        "-f",
        "best[height<=?720][width<=?1280]",
        f"{link}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if stdout:
        return 1, stdout.decode().split("\n")[0]
    else:
        return 0, stderr.decode()
    

async def yt_audio(link):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-g",
        "-f",
        "bestaudio",
        f"{link}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if stdout:
        return 1, stdout.decode().split("\n")[0]
    else:
        return 0, stderr.decode()


@bot.on_callback_query()
async def callbacks(_, cq: CallbackQuery):
    user_id = cq.from_user.id
    try:
        user = await cq.message.chat.get_member(user_id)
        admin_strings = ("creator", "administrator")
        if user.status not in admin_strings:
            is_admin = False
        else:
            is_admin = True
    except ValueError:
        is_admin = True        
    if not is_admin:
        return await cq.answer("You are missing the enough rights...")   
    chat_id = cq.message.chat.id
    data = cq.data
    if data == "close":
        return await cq.message.delete()
    if not chat_id in QUEUE:
        return await cq.answer("Nothing is playing...❌")

    if data == "pause":
        try:
            await app.pause_stream(chat_id)
            await cq.answer("Paused...")
        except:
            await cq.answer("Nothing is playing...❌")
      
    elif data == "resume":
        try:
            await app.resume_stream(chat_id)
            await cq.answer("Resumed...")
        except:
            await cq.answer("Nothing is playing...❌")   

    elif data == "end":
        await app.leave_group_call(chat_id)
        clear_queue(chat_id)
        await cq.answer("Ended the voice chat...❌")  

   elif data == "skip":
        ak = await skip_current_song(chat_id)
        if ak == 0:
            await cq.answer("Empty...")
        elif ak == 1:
            await cq.answer("Leaving.... Nothing found in the list...")
        else:
            await cq.answer("Skipped...")
            

@bot.on_message(filters.command("start") & filters.private)
async def start_private(_, message):
    msg = START_TEXT.format(message.from_user.mention, OWNER_ID)
    await message.reply_text(text = msg,
                             reply_markup = START_BUTTONS)
    

@bot.on_message(filters.command(["ping", "alive"]) & filters.group)
async def start_group(_, message):
    await message.delete()
    fuk = "<b>PONG</b>"
    await message.reply_photo(photo="https://te.legra.ph/file/f39b3713bda21fdb38e2d.jpg", caption=OKVAI)


@bot.on_message(filters.command(["join", "userbotjoin", "assistant", "ass"]) & filters.group)
@is_admin
async def join_chat(c: Client, m: Message):
    chat_id = m.chat.id
    try:
        invitelink = await c.export_chat_invite_link(chat_id)
        if invitelink.startswith("https://t.me/+"):
            invitelink = invitelink.replace(
                "https://t.me/+", "https://t.me/joinchat/"
            )
            await client.join_chat(invitelink)
            return await client.send_message(chat_id, "**Assistant Joined Successfully....**")
    except UserAlreadyParticipant:
        return await client.send_message(chat_id, "**Assistant already in the chat....**")

    
@bot.on_message(filters.command(["play", "vplay"]) & filters.group)
async def video_play(_, message):
    await message.delete()
    user_id = message.from_user.id
    state = message.command[0].lower()
    try:
        query = message.text.split(None, 1)[1]
    except:
        return await message.reply_text(f"<b>Usage:</b> <code>/{state} [query]</code>")
    chat_id = message.chat.id
    if chat_id in LIVE_CHATS:
        return await message.reply_text("Please send <code>/end</code> to end the currently playing stream and to start new...")
    
    m = await message.reply_text("**🔱 Searching...**")
    if state == "play":
        damn = AudioPiped
        ded = yt_audio
        doom = "Audio"
    elif state == "vplay":
        damn = AudioVideoPiped
        ded = yt_video
        doom = "Video"
    if "low" in query:
        Q = "low"
    elif "mid" in query:
        Q = "mid"
    elif "high" in query:
        Q = "high"
    else:
        Q = "0"
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        link = f"https://youtube.com{results[0]['url_suffix']}"
        thumb = results[0]["thumbnails"][0]
        duration = results[0]["duration"]
        yt = YouTube(link)
        cap = f"» <b>Title :</b> [{yt.title}]({link})\n✨ <b>Streaming type:</b> `{doom}` \n🕕 <b>Duration:</b> {duration}"
        try:
            ydl_opts = {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]"}
            ydl = youtube_dl.YoutubeDL(ydl_opts)
            info_dict = ydl.extract_info(link, download=False)
            p = json.dumps(info_dict)
            a = json.loads(p)
            playlink = a['formats'][1]['manifest_url']
        except:
            ice, playlink = await ded(link)
            if ice == "0":
                return await m.edit("❗️YTDL ERROR !!!")               
    except Exception as e:
        return await m.edit(str(e))
    
    try:
        if chat_id in QUEUE:
            position = add_to_queue(chat_id, yt.title, duration, link, playlink, doom, Q, thumb)
            caps = f"⚡[{yt.title}]({link}) <b>Will by playing after{position}</b>query\n\n🕕 <b>Duration:</b> {duration}"
            await message.reply_photo(thumb, caption=caps)
            await m.delete()
        else:            
            await app.join_group_call(
                chat_id,
                damn(playlink),
                stream_type=StreamType().pulse_stream
            )
            add_to_queue(chat_id, yt.title, duration, link, playlink, doom, Q, thumb)
            await message.reply_photo(thumb, caption=cap, reply_markup=BUTTONS)
            await m.delete()
    except Exception as e:
        return await m.edit(str(e))
    
    
@bot.on_message(filters.command(["stream", "vstream"]) & filters.group)
@is_admin
async def stream_func(_, message):
    await message.delete()
    state = message.command[0].lower()
    try:
        link = message.text.split(None, 1)[1]
    except:
        return await message.reply_text(f"<b>Usage:</b> <code>/{state} [link]</code>")
    chat_id = message.chat.id
    
    if state == "stream":
        damn = AudioPiped
        emj = "🎶"
    elif state == "vstream":
        damn = AudioVideoPiped
        emj = "📷"
    m = await message.reply_text("PLEASE Wait....")
    try:
        if chat_id in QUEUE:
            return await m.edit("❗️Please send <code>/end</code> to end voice chat before live streaming.")
        elif chat_id in LIVE_CHATS:
            await app.change_stream(
                chat_id,
                damn(link)
            )
            await m.edit(f"{emj} Started streaming: [Link]({link})", disable_web_page_preview=True)
        else:    
            await app.join_group_call(
                chat_id,
                damn(link),
                stream_type=StreamType().pulse_stream)
            await m.edit(f"{emj} Started streaming: [Link]({link})", disable_web_page_preview=True)
            LIVE_CHATS.append(chat_id)
    except Exception as e:
        return await m.edit(str(e))


@bot.on_message(filters.command("skip") & filters.group)
@is_admin
async def skip(_, message):
    await message.delete()
    chat_id = message.chat.id
    if len(message.command) < 2:
        op = await skip_current_song(chat_id)
        if op == 0:
            await message.reply_text("Queue is empty...")
        elif op == 1:
            await message.reply_text("Leaving voice chat... Queue is empty...")
    else:
        skip = message.text.split(None, 1)[1]
        out = "🗑 <b>Removed the following song(s) from the queue:</b> \n"
        if chat_id in QUEUE:
            items = [int(x) for x in skip.split(" ") if x.isdigit()]
            items.sort(reverse=True)
            for x in items:
                if x == 0:
                    pass
                else:
                    hm = await skip_item(chat_id, x)
                    if hm == 0:
                        pass
                    else:
                        out = out + "\n" + f"<b>» {x}</b> - {hm}"
            await message.reply_text(out)
            
            
@bot.on_message(filters.command(["playlist", "queue"]) & filters.group)
@is_admin
async def playlist(_, message):
    chat_id = message.chat.id
    if chat_id in QUEUE:
        chat_queue = get_queue(chat_id)
        if len(chat_queue) == 1:
            await message.delete()
            await message.reply_text(
                f"🔱 <b>Currently Playing :</b> [{chat_queue[0][0]}]({chat_queue[0][2]}) | `{chat_queue[0][4]}`",
                disable_web_page_preview=True,
            )
        else:
            out = f"<b>🚶Queue:</b> \n\n⚡ <b>Playing :</b> [{chat_queue[0][0]}]({chat_queue[0][2]}) | `{chat_queue[0][4]}` \n"
            l = len(chat_queue)
            for x in range(1, l):
                title = chat_queue[x][0]
                link = chat_queue[x][2]
                type = chat_queue[x][4]
                out = out + "\n" + f"<b>» {x}</b> - [{title}]({link}) | `{type}` \n"
            await message.reply_text(out, disable_web_page_preview=True)
    else:
        await message.reply_text("Nothing is playing...")
    

@bot.on_message(filters.command(["end", "stop"]) & filters.group)
@is_admin
async def end(_, message):
    await message.delete()
    chat_id = message.chat.id
    if chat_id in LIVE_CHATS:
        await app.leave_group_call(chat_id)
        LIVE_CHATS.remove(chat_id)
        return await message.reply_text("Ended...")
        

if chat_id in QUEUE:
        await app.leave_group_call(chat_id)
        clear_queue(chat_id)
        await message.reply_text("Ended...")
    else:
        await message.reply_text("Nothing is playing...")
        

@bot.on_message(filters.command("pause") & filters.group)
@is_admin
async def pause(_, message):
    await message.delete()
    chat_id = message.chat.id
    if chat_id in QUEUE:
        try:
            await app.pause_stream(chat_id)
            await message.reply_text("Paused...")
        except:
            await message.reply_text("Nothing is playing...")
    else:
        await message.reply_text("Nothing is playing...")
        
        
@bot.on_message(filters.command("resume") & filters.group)
@is_admin
async def resume(_, message):
    await message.delete()
    chat_id = message.chat.id
    if chat_id in QUEUE:
        try:
            await app.resume_stream(chat_id)
            await message.reply_text("Resumed...")
        except:
            await message.reply_text("Nothing is playing...")
    else:
        await message.reply_text("Nothing is playing...")


@bot.on_callback_query(filters.regex("help_cb"))
async def help_cmds(_, query: CallbackQuery):
    await query.answer("Commands Menu")
    await query.edit_message_text(
        f"""<b>🥀Main Commands</b>
• /play (song/link/query) : To play the request stream as audio.
• /vplay (song/link/query) : To play the request stream as video.
• /pause : to stop the stream.
• /resume : to restart the stream.
• /skip : ok lol.
• /end : Ok clear the queue and leaving VC chat.
• /playlist : Show the list of queued stream.
• /join or /userbotjoin - Request the Assistant to join the chat.
• /restart - You are not enough noob ??

⚡ <b><u>Powered by [BlueCode](https://t.me/TheBlueCode)...</u></b> ⚡""")

        
@bot.on_message(filters.command("restart"))
async def restart(_, message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    await message.reply_text("» <i>RESTARTING...</i>")
    os.system(f"kill -9 {os.getpid()} && python3 app.py")
            

app.start()
bot.run()
idle()


# © @akhilprs
