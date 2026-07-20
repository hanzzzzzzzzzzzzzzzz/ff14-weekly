import discord
from discord.ext import commands
import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_OWNER = "hanzzzzzzzzzzzzzzzz"
GITHUB_REPO = "ff14-weekly"
GITHUB_FILE = "fashion-judging.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} 已連接到 Discord！')
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個指令")
    except Exception as e:
        print(f"同步指令時出錯：{e}")

@bot.tree.command(name="時尚評鑑", description="更新時尚評鑑資訊")
@discord.app_commands.describe(
    content="穿搭建議（例如：推薦搭配 XX 裝備）",
    notes="注意事項或備註",
    hakka_index="客家指數（1-5）",
    image_url="圖片連結",
    author="評鑑者名稱",
    threads_link="貼文連結（Discord Threads 或其他）- 選填"
)
async def fashion_judging(
    interaction: discord.Interaction,
    content: str,
    notes: str,
    hakka_index: int,
    image_url: str,
    author: str,
    threads_link: str = None
):
    await interaction.response.defer()

    if not (1 <= hakka_index <= 5):
        await interaction.followup.send("❌ 客家指數必須是 1-5 之間的數字", ephemeral=True)
        return

    data = {
        "content": content,
        "notes": notes,
        "hakkaIndex": hakka_index,
        "imageUrl": image_url,
        "author": author,
        "threadsLink": threads_link or ""
    }

    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')

        content_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_encoded = base64.b64encode(content_str.encode()).decode()

        body = {
            "message": f"🎨 更新時尚評鑑：客家指數 {hakka_index}⭐",
            "content": content_encoded
        }

        if sha:
            body["sha"] = sha

        response = requests.put(url, headers=headers, json=body)

        if response.status_code in [200, 201]:
            star_emoji = "⭐" * hakka_index
            await interaction.followup.send(
                f"✅ 時尚評鑑已更新！\n"
                f"客家指數：{star_emoji}\n"
                f"By. {author}\n"
                f"建議：{content}\n"
                f"備註：{notes}"
            )
        else:
            error_msg = response.json().get('message', response.text)
            await interaction.followup.send(f"❌ 更新失敗：{error_msg}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ 發生錯誤：{str(e)}", ephemeral=True)
        print(f"錯誤詳情：{e}")

bot.run(DISCORD_TOKEN)
