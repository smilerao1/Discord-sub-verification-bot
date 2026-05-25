import discord
import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN")
VERIFY_CHANNEL = int(os.getenv("VERIFY_CHANNEL_ID"))
VERIFIED_ROLE  = int(os.getenv("VERIFIED_ROLE_ID"))
YOUR_CHANNEL   = os.getenv("YOUR_YOUTUBE_CHANNEL")
GEMINI_KEY     = os.getenv("GEMINI_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

async def check_screenshot(image_bytes, media_type):
    img_b64 = base64.standard_b64encode(image_bytes).decode()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": media_type,
                        "data": img_b64
                    }
                },
                {
                    "type": "text",
                    "text": f"""Look at this screenshot carefully.
Does it clearly show that someone is SUBSCRIBED to a YouTube channel named '{YOUR_CHANNEL}'?
Look for: Subscribe button showing 'Subscribed', channel name visible, YouTube interface.

Reply ONLY with:
VERIFIED - if clearly subscribed to {YOUR_CHANNEL}
REJECTED - [reason] if not valid proof"""
                }
            ]
        }]
    }

    async with httpx.AsyncClient() as http:
        response = await http.post(url, json=payload, timeout=30)
        data = response.json()

    result = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    if result.startswith("VERIFIED"):
        return True, "✅ Subscription verified!"
    else:
        return False, f"❌ {result.replace('REJECTED - ', '')}"

@client.event
async def on_ready():
    print(f"Bot ready: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != VERIFY_CHANNEL:
        return
    if not message.attachments:
        await message.reply("📸 Please share a screenshot of your YouTube subscription!")
        return

    attachment = message.attachments[0]
    if not attachment.content_type or "image" not in attachment.content_type:
        await message.reply("⚠️ Please send a PNG or JPG image.")
        return

    processing_msg = await message.reply("⏳ Checking your screenshot...")

    try:
        image_bytes = await attachment.read()
        media_type = attachment.content_type.split(";")[0]
        verified, reason = await check_screenshot(image_bytes, media_type)

        if verified:
            role = message.guild.get_role(VERIFIED_ROLE)
            member = message.author
            if role not in member.roles:
                await member.add_roles(role)
                await processing_msg.edit(content=f"🎉 {member.mention} You're now a verified subscriber! ✅")
            else:
                await processing_msg.edit(content="✅ You already have the Subscriber role!")
        else:
            await processing_msg.edit(content=f"{reason}\n\nMake sure your screenshot shows:\n• 'Subscribed' button on YouTube\n• Channel name: **{YOUR_CHANNEL}**")
    except Exception as e:
        await processing_msg.edit(content=f"⚠️ Error: {e}")
        print(f"Error: {e}")

client.run(BOT_TOKEN)
