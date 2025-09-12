import os
import requests
import threading
import asyncio
import cloudscraper
import time
from pyromod import listen
from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message
from config import CHANNEL_ID, THUMB_URL, BOT_TEXT
from Extractor import app
import textwrap
from datetime import datetime
import pytz

requests = cloudscraper.create_scraper()

ACCOUNT_ID = "6206459123001"
bc_url = f"https://edge.api.brightcove.com/playback/v1/accounts/{ACCOUNT_ID}/videos/"

# -------------------- Utility Functions ---------------------
def download_thumbnail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            thumb_path = "thumb_temp.jpg"
            with open(thumb_path, "wb") as f:
                f.write(response.content)
            return thumb_path
        return None
    except Exception:
        return None

# -------------------- Downloader Function ---------------------
async def careerdl(app, message, headers, batch_id, token, topic_ids, prog, batch_name):
    topic_list = topic_ids.split("&")
    total_videos = 0
    total_notes = 0
    start_time = time.time()
    thumb_path = download_thumbnail(THUMB_URL)
    result_text = ""

    for index, t_id in enumerate(topic_list, start=1):
        try:
            # Fetch class details
            details_url = f"https://elearn.crwilladmin.com/api/v9/batch-detail/{batch_id}?topicId={t_id}"
            response = requests.get(details_url, headers=headers).json()
            classes = response.get("data", {}).get("class_list", {}).get("classes", [])
            classes.reverse()

            # Get topic name
            topic_url = f"https://elearn.crwilladmin.com/api/v9/batch-topic/{batch_id}?type=class"
            topics_data = requests.get(topic_url, headers=headers).json().get("data", {})
            current_topic_name = next(
                (x["topicName"] for x in topics_data.get("batch_topic", []) if str(x["id"]) == t_id), "Unknown Topic"
            )

            # Progress calculation
            elapsed_time = time.time() - start_time
            avg_time = elapsed_time / index
            remaining = len(topic_list) - index
            eta = avg_time * remaining
            elapsed_str = f"{int(elapsed_time//60)}m {int(elapsed_time%60)}s"
            eta_str = f"{int(eta//60)}m {int(eta%60)}s"

            await prog.edit_text(
                f"🔄 <b>Processing Batch</b>\n"
                f"├─ Topic {index}/{len(topic_list)}: <code>{current_topic_name}</code>\n"
                f"├─ Videos Processed: {total_videos}\n"
                f"├─ Notes Processed: {total_notes}\n"
                f"├─ Elapsed: {elapsed_str}\n"
                f"└─ ETA: {eta_str}"
            )

            # Process classes
            for c in classes:
                vid_id = c.get("id")
                lesson_name = c.get("lessonName")
                lesson_ext = c.get("lessonExt")
                detail_url = f"https://elearn.crwilladmin.com/api/v9/class-detail/{vid_id}"
                lesson_data = requests.get(detail_url, headers=headers).json()
                lesson_url = lesson_data.get("data", {}).get("class_detail", {}).get("lessonUrl", "")

                if lesson_ext == "brightcove":
                    video_link = f"{bc_url}{lesson_url}/master.m3u8?bcov_auth={token}"
                    total_videos += 1
                elif lesson_ext == "youtube":
                    video_link = f"https://www.youtube.com/embed/{lesson_url}"
                    total_videos += 1
                else:
                    continue

                result_text += f"{lesson_name}: {video_link}\n"

            # Process notes
            notes_url = f"https://elearn.crwilladmin.com/api/v9/batch-topic/{batch_id}?type=notes"
            notes_data = requests.get(notes_url, headers=headers).json().get("data", {}).get("batch_topic", [])
            for note_topic in notes_data:
                n_id = note_topic.get("id")
                notes_detail_url = f"https://elearn.crwilladmin.com/api/v9/batch-notes/{batch_id}?topicId={n_id}"
                notes_resp = requests.get(notes_detail_url, headers=headers).json()
                for note in reversed(notes_resp.get("data", {}).get("notesDetails", [])):
                    title = note.get("docTitle", "")
                    url = note.get("docUrl", "").replace(" ", "%20")
                    line = f"{title}: {url}\n"
                    if line not in result_text:
                        result_text += line
                        total_notes += 1

        except Exception as e:
            await message.reply_text(f"❌ Error in topic {t_id}: {str(e)}")

    # Write to file
    file_name = f"{batch_name.replace('/', '')}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(result_text)

    # Send to user & channel
    current_date = datetime.now().strftime("%Y-%m-%d")
    caption = (
        f"🎓 <b>COURSE EXTRACTED</b>\n\n"
        f"📱 <b>APP:</b> CareerWill\n"
        f"📚 <b>BATCH:</b> {batch_name}\n"
        f"📅 <b>DATE:</b> {current_date} IST\n\n"
        f"📊 <b>CONTENT STATS</b>\n"
        f"├─ 🎬 Videos: {total_videos}\n"
        f"├─ 📄 PDFs/Notes: {total_notes}\n"
        f"└─ 📦 Total Links: {total_videos + total_notes}\n\n"
        f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n"
        f"<code>╾───• {BOT_TEXT} •───╼</code>"
    )

    try:
        await app.send_document(message.chat.id, document=file_name, caption=caption, thumb=thumb_path)
        await app.send_document(CHANNEL_ID, document=file_name, caption=caption, thumb=thumb_path)
    finally:
        await prog.delete()
        os.remove(file_name)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

# -------------------- Main Command ---------------------
@app.on_message(filters.command("cw") & filters.private)
async def career_will(app: Client, message: Message):
    try:
        # Welcome & input
        welcome = (
            "🔹 <b>CAREERWILL EXTRACTOR</b> 🔹\n\n"
            "Send <b>ID*Password</b> or Token directly.\n\n"
            "<b>Example:</b>\n"
            "- 6969696969*password123\n"
            "- Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )
        inp = await app.ask(message.chat.id, welcome)
        raw = inp.text.strip()

        # Login or token
        if "*" in raw:
            email, pwd = raw.split("*")
            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
            device_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

            headers = {
                "Host": "wbspec.crwilladmin.com",
                "accept": "application/json, text/plain, */*",
                "appver": "1",
                "apptype": "web",
                "cwkey": "Qw4NwDs7nEZ6BukUATJqKMeJdzzVzS4xrTjN0zDjcuI=",
                "content-type": "application/json",
                "origin": "https://web.careerwill.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            }

            data = {
                "userid": email,
                "pwd": pwd,
                "deviceType": "web",
                "deviceModel": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N)",
                "deviceVersion": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N)",
                "deviceIMEI": "fake_imei_123456",
                "deviceDateTime": device_datetime,
                "timezone": "+05:30"
            }

            resp = requests.post("https://wbspec.crwilladmin.com/api/v1/login", headers=headers, json=data).json()
            token = resp.get("data", {}).get("token")
            if not token:
                await message.reply_text(f"❌ Login failed:\n{resp}")
                return
            await message.reply_text(f"✅ Login successful. Token: {token[:60]}...")
        else:
            token = raw

        # Fetch batches
        headers = {
            "Host": "wbspec.crwilladmin.com",
            "accept": "application/json, text/plain, */*",
            "appver": "1",
            "apptype": "web",
            "token": token,
            "cwkey": "Qw4NwDs7nEZ6BukUATJqKMeJdzzVzS4xrTjN0zDjcuI=",
            "content-type": "application/json",
            "origin": "https://web.careerwill.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }

        batches_json = requests.get("https://wbspec.crwilladmin.com/api/v1/batches", headers=headers).json()
        batches = batches_json.get("data", {}).get("batchData", [])
        if not batches:
            await message.reply_text("❌ No batches found.")
            return

        msg = "📚 <b>Available Batches</b>\n\n"
        for b in batches:
            msg += f"<code>{b['id']}</code> - <b>{b['batchName']}</b>\n"
        await message.reply_text(msg)

        batch_input = await app.ask(message.chat.id, "<b>Send Batch ID to download:</b>")
        batch_id = batch_input.text.strip()

        # Fetch topics
        topic_json = requests.get(f"https://elearn.crwilladmin.com/api/v9/batch-topic/{batch_id}?type=class", headers=headers).json()["data"]
        batch_name = topic_json["batch_detail"]["name"]
        topics = topic_json["batch_topic"]

        id_list = "&".join([str(t["id"]) for t in topics])
        topic_msg = "📑 <b>Available Topics</b>\n\n"
        for t in topics:
            topic_msg += f"<code>{t['id']}</code> - <b>{t['topicName']}</b>\n"
        await message.reply_text(topic_msg)

        topic_input = await app.ask(
            message.chat.id,
            f"📝 <b>Send topic IDs</b>\nFormat: <code>1&2&3</code>\nAll: <code>{id_list}</code>"
        )
        topic_ids = topic_input.text.strip()

        prog_msg = await message.reply("🔄 <b>Processing content...</b>\nPlease wait...")
        threading.Thread(target=lambda: asyncio.run(careerdl(app, message, headers, batch_id, token, topic_ids, prog_msg, batch_name))).start()

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
