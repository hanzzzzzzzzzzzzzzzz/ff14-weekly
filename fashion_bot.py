import discord
from discord.ext import commands
import requests
import json
import base64
import os
from datetime import datetime, timezone
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

@bot.tree.command(name="時尚評鑑", description="更新時尚評鑑資訊（全部欄位都選填，只填你要改/補的，其他維持原樣）")
@discord.app_commands.describe(
    content="穿搭建議（選填，不填就維持原本內容）",
    notes="注意事項或備註（選填，不填就維持原本內容）",
    hakka_index="客家指數 1-5（選填，不填就維持原本評分）",
    image_url="圖片連結（選填，不填就維持原本圖片）",
    image_url2="第二張圖片連結（選填）",
    author="評鑑者名稱（選填，不填就維持原本填的人）",
    threads_link="貼文連結（選填）"
)
async def fashion_judging(
    interaction: discord.Interaction,
    content: str = None,
    notes: str = None,
    hakka_index: int = None,
    image_url: str = None,
    image_url2: str = None,
    author: str = None,
    threads_link: str = None
):
    await interaction.response.defer()

    if hakka_index is not None and not (1 <= hakka_index <= 5):
        await interaction.followup.send("❌ 客家指數必須是 1-5 之間的數字", ephemeral=True)
        return

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        sha = None
        existing = {}
        if response.status_code == 200:
            sha = response.json().get('sha')
            try:
                existing = json.loads(base64.b64decode(response.json()['content']).decode('utf-8'))
            except Exception:
                existing = {}

        # 只有這次真的有填的欄位才覆蓋，沒填的欄位沿用 GitHub 上原本的值——
        # 這樣打錯字只要重打那一欄重送就好，之後想補圖或改內容也不用整份重打
        data = {
            "content": content if content is not None else existing.get("content", ""),
            "notes": notes if notes is not None else existing.get("notes", ""),
            "hakkaIndex": hakka_index if hakka_index is not None else existing.get("hakkaIndex", 0),
            "imageUrl": image_url if image_url is not None else existing.get("imageUrl", ""),
            "imageUrl2": image_url2 if image_url2 is not None else existing.get("imageUrl2", ""),
            "author": author if author is not None else existing.get("author", ""),
            "threadsLink": threads_link if threads_link is not None else existing.get("threadsLink", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }

        content_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_encoded = base64.b64encode(content_str.encode()).decode()

        body = {
            "message": f"🎨 更新時尚評鑑：客家指數 {data['hakkaIndex']}⭐",
            "content": content_encoded
        }

        if sha:
            body["sha"] = sha

        response = requests.put(url, headers=headers, json=body)

        if response.status_code in [200, 201]:
            star_emoji = "⭐" * data['hakkaIndex']
            await interaction.followup.send(
                f"✅ 時尚評鑑已更新！（沒填的欄位維持原樣）\n"
                f"客家指數：{star_emoji}\n"
                f"By. {data['author'] or '（未填）'}\n"
                f"建議：{data['content'] or '（未填）'}\n"
                f"備註：{data['notes'] or '（未填）'}"
            )
        else:
            error_msg = response.json().get('message', response.text)
            await interaction.followup.send(f"❌ 更新失敗：{error_msg}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ 發生錯誤：{str(e)}", ephemeral=True)
        print(f"錯誤詳情：{e}")

bot.run(DISCORD_TOKEN)
