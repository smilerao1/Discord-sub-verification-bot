import discord
import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN")
VERIFY_CHANNEL  = int(os.getenv("VERIFY_CHANNEL_ID"))
VERIFIED_ROLE   = int(os.getenv("VERIFIED_ROLE_ID"))
YOUR_CHANNEL    = os.getenv("YOUR_YOUTUBE_CHANNEL")
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

async def check_screenshot(image_bytes, media_type):
    img_b64 = base64.standard_b64encode(image_bytes).decode()

    async with httpx.AsyncClient() as http:
        response = await http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{img_b64}"
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
            },
            timeout=30
        )
        data = response.json()
        print(f"OpenRouter response: {data}")

    if "choices" not in data:
        error_msg = data.get("error", {}).get("message", str(data))
        raise Exception(f"API error: {error_msg}")

    result = data["choices"][0]["message"]["content"].strip()
    print(f"AI result: {result}")

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
        await message.channel.send("📸 Please share a screenshot of your YouTube subscription!")
        return

    attachment = message.attachments[0]
    if not attachment.content_type or "image" not in attachment.content_type:
        await message.channel.send("⚠️ Please send a PNG or JPG image.")
        return

    processing_msg = await message.channel.send("⏳ Checking your screenshot...")

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
