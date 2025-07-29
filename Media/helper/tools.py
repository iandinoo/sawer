import json
import asyncio
import datetime
import requests

from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup

from pyrogram import *
from pytz import timezone
from datetime import datetime

from Media.helper.database import *
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, UserDeactivatedBan

async def get_readable_time(seconds: int) -> str:    
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "d"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "

    time_list.reverse()
    up_time += ":".join(time_list)

    return up_time
    
def get_arg(message):
    msg = message.text
    msg = msg.replace(" ", "", 1) if msg[1] == " " else msg
    split = msg[1:].replace("\n", " \n").split(" ")
    if " ".join(split[1:]).strip() == "":
        return ""
    return " ".join(split[1:])
  
async def send_msg(chat_id, message):
    try:
        broadcast = await get_broadcast()
        if broadcast == False:
            await message.forward(chat_id=chat_id)
        elif broadcast == True:
            await message.copy(chat_id=chat_id)
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(int(e.value))
        return await send_msg(chat_id, message)
    except UserIsBlocked:
        await increment_bot_removed_users()
        await remove_gcast(chat_id)
        return 403, "Pengguna diblokir"
    except (UserDeactivatedBan, InputUserDeactivated):
        await increment_deleted_accounts()
        await remove_gcast(chat_id)
        return 410, "Akun pengguna dinonaktifkan"
        
async def remove_duplicates(users):
    seen = set()
    unique_users = []
    
    for user in users:
        if user not in seen:
            seen.add(user)
            unique_users.append(user)
        else:
            print(f"ID pengguna duplikat ditemukan dan dihapus: {user}")
            await remove_gcast(user)
    return unique_users

def create_payment_string(saweria_username: str, amount: int, sender: str, email: str, message: str, ) -> dict:
    if not saweria_username or not amount or not sender or not email or not message:
        raise ValueError("Parameter is missing!")

    response = requests.get(f"https://saweria.co/{saweria_username}")
    soup = BeautifulSoup(response.text, "html.parser")
    
    next_data_script = soup.find(id='__NEXT_DATA__')
    if not next_data_script:
        raise ValueError("Saweria account not found")
    
    next_data = json.loads(next_data_script.text)
    user_id = next_data.get("props", {}).get("pageProps", {}).get("data", {}).get("id")
    if not user_id:
        raise ValueError("Saweria account not found")
    
    payload = {
        "agree": True,
        "notUnderage": True,
        "message": message,
        "amount": int(amount),
        "payment_type": "qris",
        "vote": "",
        "currency": "IDR",
        "customer_info": {
            "first_name": sender,
            "email": email,
            "phone": ""
        }
    }
    ps = requests.post(f"https://backend.saweria.co/donations/{user_id}", json=payload)
    pc = ps.json()["data"]
    return pc

def create_payment_qr(saweria_username: str, amount: int, sender: str, email: str, pesan: str) -> list:
    payment_details = create_payment_string(saweria_username, amount, sender, email, pesan)  
    return [payment_details["qr_string"], payment_details["id"]]
    
def cek_status(pay_invoice):
    url = f"https://backend.saweria.co/donations/qris/{pay_invoice}"
    response = requests.get(url)
    result = response.text
    try:
        hasil = json.loads(result)
        status = hasil['data']['qr_string']
        amount = hasil['data']['amount_raw']
        create_at = hasil['data']['created_at']
        if status == "":
            return "SUKSES", amount, create_at
        else:
            return "PENDING", amount, create_at
    except Exception as e:
        return "❌ Pembayaran Gagal"
        
