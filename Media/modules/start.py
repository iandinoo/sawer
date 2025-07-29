import os
import uuid
import json
import random
import logging
import asyncio
import requests
from PIL import Image
from io import BytesIO

from pyrogram import *
from pyromod import listen
from pyrogram.types import *
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Media import *
from Media.config import *
from Media.helper.tools import *
from Media.helper.database import *
from Media.helper.date_info import *
from httpx import AsyncClient, HTTPStatusError, TimeoutException, RequestError, ReadTimeout
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, UserDeactivatedBan

from datetime import timedelta
import datetime
import time
import httpx

logging.basicConfig(level=logging.INFO)

C10 = """
<b>ᴅᴇᴛᴀɪʟs ᴘᴇᴍʙᴀʏᴀʀᴀɴ : </b>
- ᴛᴏᴛᴀʟ : <b>{}</b>
- ᴄʀᴇᴀᴛᴇᴅ <b>{}</b>
sɪʟᴀʜᴋᴀɴ ʟᴀᴋᴜᴋᴀɴ ᴘᴇᴍʙᴀʏᴀʀᴀɴ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴍᴇᴛᴏᴅᴇ ᴘᴇᴍʙᴀʏᴀʀᴀɴ ǫʀɪs.
• sᴇᴛᴇʟᴀʜ ᴍᴇʟᴀᴋᴜᴋᴀɴ ᴘᴇᴍʙᴀʏᴀʀᴀɴ ʟɪɴᴋ ᴀᴋᴀɴ ᴏᴛᴏᴍᴀᴛɪs ᴅɪʙᴇʀɪᴋᴀɴ.

<b>ᴘᴀʏᴍᴇɴᴛ ɪɴᴠᴏɪᴄᴇ</b>
{}
"""

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    gcast = await get_gcast()
    welcome = await get_welcome()
    if message.from_user.id not in gcast:
        await add_gcast(message.from_user.id)

    start_button = InlineKeyboardButton("• ᴊᴏɪɴ ᴍᴇᴅɪᴀ •", callback_data="create_saweria")
    start_markup = InlineKeyboardMarkup([[start_button]])
        
    if not await get_maintenance():
        return await message.reply("ʙᴏᴛ sᴇᴅᴀɴɢ ᴅɪ ᴘᴇʀʙᴀɪᴋɪ ᴛᴏʟᴏɴɢ ʙᴇʀsᴀʙᴀʀ⏳")
    try:
        await message.reply(text=welcome, reply_markup=start_markup)
    except Exception as e:
        await message.reply(text=welcome, reply_markup=start_markup)

@bot.on_callback_query(filters.regex("create_saweria"))
async def create_saweria(client, cb):
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id

    if not await get_saweria():
        return await cb.answer("❌ Pasang Saweria Terlebih Dahulu", show_alert=True)
        
    maintenance = await get_maintenance()
    if not maintenance:
        return await cb.answer("🛠️ BOT SEDANG PERBAIKAN - KEMBALI LAGI NANTI", show_alert=True)

    if await check_pending_transaction(user_id):
        return await cb.answer("❌ Anda masih punya transaksi yang belum terselesaikan, harap selesaikan terlebih dahulu atau dibatalkan.", show_alert=True)
    
    try:
        user = await get_saweria()
        amount = await get_price()

        url = f"https://saweria.autsc.my.id/api/create?username={user.get('username')}&amount={amount}&email={user.get('email')}"
        
        async with httpx.AsyncClient() as req:
            response = await req.get(url)
            result = response.json()

        data = result["data"]
        qr_url = data["qrImageUrl"]
        timestamp = data["timestamp"]
        amount_str = data["amount"]
        transaction_id = data["transactionId"]
        
        success_button = InlineKeyboardButton("• sᴜᴅᴀʜ ᴍᴇᴍʙᴀʏᴀʀ •", callback_data=f"checkqr_{transaction_id}")
        cancel_button = InlineKeyboardButton("• ʙᴀᴛᴀʟᴋᴀɴ ᴛʀᴀɴsᴀᴋsɪ •", callback_data="cancel")
        start_markup = InlineKeyboardMarkup([[success_button], [cancel_button]])
        
        await cb.message.delete()
        qris_message = await cb.message.reply_photo(photo=qr_url, caption=C10.format(amount_str, timestamp, transaction_id), reply_markup=start_markup)

        await create_pending_transaction(user_id)
        LOGGER("INFO").info(f"🌀 Pembayaran Pending: {transaction_id}")
        
    except UserIsBlocked:
        return LOGGER("INFO").info(f"⛔ UserIsBlocked: {transaction_id}")
    except (UserDeactivatedBan, InputUserDeactivated):
        return LOGGER("INFO").info(f"⛔ UserDeactivatedBan InputUserDeactivated: {transaction_id}")
    except Exception as e:
        return await cb.message.reply(f"<b>Terjadi kesalahan:</b> `{str(e)}`")

@bot.on_callback_query(filters.regex(r"checkqr_"))
async def check_saweria(client, callback_query):
    user_id = callback_query.from_user.id

    if "_" in callback_query.data:
        data_parts = callback_query.data.split("_", 1)
        pay_invoice = data_parts[1]
    else:
        await callback_query.message.delete()
        await callback_query.answer('Terjadi kesalahan. ID transaksi tidak ditemukan.', show_alert=True)
        return

    try:
        url = f"https://saweria.autsc.my.id/check-payment?idtransaksi={pay_invoice}"

        async with httpx.AsyncClient() as req:
            response = await req.get(url)
            result = response.json()

        data = result["data"]
        is_paid = data.get("isPaid", False)

        if is_paid:
            await callback_query.message.delete()
            await delete_pending_transaction(user_id)
            LOGGER("INFO").info(f"✅ Pembayaran Berhasil: {pay_invoice}")
            await create_chat_invite(callback_query, pay_invoice)
            await create_logger_link(callback_query, pay_invoice)
        else:
            text = (
                f"⌛ <b>Pembayaran Belum Diterima</b>\n"
                f"🧾 ID Transaksi: <code>{pay_invoice}</code>\n\n"
                f"Silakan selesaikan pembayaran melalui QR yang sudah diberikan."
            )

        await callback_query.message.reply(text)

    except UserIsBlocked:
        LOGGER("INFO").info(f"⛔ UserIsBlocked: {pay_invoice}")
    except (UserDeactivatedBan, InputUserDeactivated):
        LOGGER("INFO").info(f"⛔ UserDeactivatedBan/InputUserDeactivated: {pay_invoice}")
    except Exception as e:
        await callback_query.message.reply(f'<b>❌ Terjadi kesalahan:</b> {str(e)}', parse_mode="HTML")
        
@bot.on_callback_query(filters.regex("cancel"))
async def cancel(client, cb):
    user_id = cb.from_user.id
    await cb.message.delete()
    LOGGER("INFO").info(f"❌ Pembayaran Dibatalkan.")
    await delete_pending_transaction(user_id)
    await cb.message.reply("<b>ᴘᴇᴍʙᴀʏᴀʀᴀɴ ᴅɪʙᴀᴛᴀʟᴋᴀɴ.</b>")

@bot.on_message(filters.command("cancel") & filters.private)
async def cancel(client, message):
    user_id = message.from_user.id
    await delete_pending_transaction(user_id)
    await message.reply("<b>Pembayaran dibatalkan.</b>")

@bot.on_message(filters.command("clear") & filters.private)
async def clear(client, message):
    await clear_gcast()
    await message.reply("sukses")
    
async def create_chat_invite(cb, pay_invoice):
    chat_id = int(await get_chat_id())
    try:
        welcome = await get_text_two()
        expire_time = datetime.datetime.now() + timedelta(hours=1)
        invite_link = await bot.create_chat_invite_link(chat_id, member_limit=1, expire_date=expire_time)
        await cb.message.reply(
            f"{welcome}\n\n"
            f"{invite_link.invite_link}",
            disable_web_page_preview=True
        )
    except UserIsBlocked:
        LOGGER("INFO").info(f"⛔ UserIsBlocked: {pay_invoice}")
        return
    except (UserDeactivatedBan, InputUserDeactivated):
        LOGGER("INFO").info(f"⛔ UserDeactivatedBan InputUserDeactivated: {pay_invoice}")
        return
    except Exception as e:
        await cb.message.reply(f"<b>Terjadi kesalahan:</b> `{str(e)}`")
        return
        
async def create_logger_link(cb, pay_invoice):
    if not await get_status_logger():
        return
        
    chat = await bot.get_chat(await get_logger())
    price = float(await get_price())
    nominal = f"Rp.{price:,.2f}".replace(",", ".")
    mention = f"@{cb.from_user.username}" if cb.from_user.username else cb.from_user.mention

    view_profile_button = InlineKeyboardButton(
        "Profile", 
        url=f"t.me/{cb.from_user.username}"
    )
    
    try:
        message = await bot.send_message(
            chat_id=chat.id,
            text=(
                f"<b>ᴘᴇɴɢɢᴜɴᴀ ʙᴇʀɢᴀʙᴜɴɢ</b>\n"
                f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {mention}\n"
                f"<b>ʜᴀʀɢᴀ :</b> {nominal}\n"
                f"<b>ɪɴᴠᴏɪᴄᴇ</b> `{pay_invoice}`\n"             
            ),
        )
    except UserIsBlocked:
        LOGGER("INFO").info(f"⛔ UserIsBlocked: {pay_invoice}")
        return
    except (UserDeactivatedBan, InputUserDeactivated):
        LOGGER("INFO").info(f"⛔ UserDeactivatedBan InputUserDeactivated: {pay_invoice}")
        return
    except Exception as e:
        await cb.message.reply(f"<b>Terjadi kesalahan:</b> `{str(e)}`")
        return

@bot.on_message(filters.command("id") & filters.user(OWNER_ID))
async def id(client, message):
    user_id = message.from_user.id
    await delete_pending_transaction(user_id)
    await message.reply(f"🆔 {message.chat.title} : `{message.chat.id}`")
    
