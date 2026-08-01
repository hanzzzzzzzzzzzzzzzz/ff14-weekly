import discord
from discord.ext import commands
import requests
import json
import base64
import os
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_OWNER = "hanzzzzzzzzzzzzzzzz"
GITHUB_REPO = "ff14-weekly"
GITHUB_FILE = "fashion-judging.json"

# 被 Discord/Cloudflare 限流時，重試前要等多久（秒）。可用環境變數覆蓋。
RATE_LIMIT_SLEEP = int(os.getenv('RATE_LIMIT_SLEEP', '900'))   # 15 分鐘
GENERIC_ERROR_SLEEP = int(os.getenv('GENERIC_ERROR_SLEEP', '60'))

# 這個 bot 只用 slash command，不讀訊息內容。
# message_content 是「特權意圖」，沒用到就別開——一旦在 Developer Portal 被關掉，
# 開著它會讓 bot 一啟動就崩潰，變成另一個重啟迴圈。
intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def github_file_url():
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}"


def fetch_existing():
    """回傳 (existing_dict, sha)；抓不到就回傳空字典跟 None。"""
    response = requests.get(github_file_url(), headers=github_headers())
    if response.status_code == 200:
        sha = response.json().get('sha')
        try:
            existing = json.loads(base64.b64decode(response.json()['content']).decode('utf-8'))
        except Exception:
            existing = {}
        return existing, sha
    return {}, None


# 彈出視窗（Modal）的文字輸入框在 Discord 裡本來就支援換行（多行文字），
# 跟 slash command 參數的單行輸入框不一樣，所以「穿搭建議」「注意事項」這種長文字
# 都改用 Modal 收集。開啟表單時會直接帶出目前 GitHub 上已經存的內容，
# 直接在原本文字上改就好，不用背哪些要留空哪些要重打。
# Discord 一個 Modal 最多只能放 5 個欄位，所以圖片連結維持放在 slash command 參數
# （本來就是單行網址，不需要多行，也不擠 Modal 的欄位額度）。
class FashionJudgingModal(discord.ui.Modal, title="更新時尚評鑑"):
    def __init__(self, image_url: str = None, image_url2: str = None):
        super().__init__()
        self.image_url = image_url
        self.image_url2 = image_url2
        existing, self.sha = fetch_existing()
        self.existing = existing

        self.content_input = discord.ui.TextInput(
            label="穿搭建議（可換行，留空＝清空）",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=existing.get("content", "")
        )
        self.notes_input = discord.ui.TextInput(
            label="注意事項（可換行，留空＝清空）",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=existing.get("notes", "")
        )
        self.hakka_index_input = discord.ui.TextInput(
            label="客家指數 1-5",
            style=discord.TextStyle.short,
            required=False,
            max_length=1,
            default=str(existing.get("hakkaIndex", "") or "")
        )
        self.author_input = discord.ui.TextInput(
            label="評鑑者名稱（留空＝清空）",
            style=discord.TextStyle.short,
            required=False,
            max_length=50,
            default=existing.get("author", "")
        )
        self.threads_link_input = discord.ui.TextInput(
            label="貼文連結（留空＝清空）",
            style=discord.TextStyle.short,
            required=False,
            max_length=300,
            default=existing.get("threadsLink", "")
        )
        for item in (self.content_input, self.notes_input, self.hakka_index_input,
                     self.author_input, self.threads_link_input):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        hakka_index_raw = self.hakka_index_input.value.strip()
        if hakka_index_raw and (not hakka_index_raw.isdigit() or not (1 <= int(hakka_index_raw) <= 5)):
            await interaction.followup.send("❌ 客家指數必須是 1-5 之間的數字", ephemeral=True)
            return
        hakka_index_val = int(hakka_index_raw) if hakka_index_raw else 0

        try:
            # 表單欄位開啟時已經帶出原本內容了，這裡直接照表單上的值寫回去就好——
            # 使用者沒改就是照原樣送回，有改就是新值，留空就是真的清空這欄。
            # 圖片連結例外：因為不在 Modal 裡（單獨在 slash command 參數），
            # 沒有帶就維持 GitHub 上原本的值。
            data = {
                "content": self.content_input.value.strip(),
                "notes": self.notes_input.value.strip(),
                "hakkaIndex": hakka_index_val,
                "imageUrl": self.image_url if self.image_url is not None else self.existing.get("imageUrl", ""),
                "imageUrl2": self.image_url2 if self.image_url2 is not None else self.existing.get("imageUrl2", ""),
                "author": self.author_input.value.strip(),
                "threadsLink": self.threads_link_input.value.strip(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }

            content_str = json.dumps(data, ensure_ascii=False, indent=2)
            content_encoded = base64.b64encode(content_str.encode()).decode()

            body = {
                "message": f"🎨 更新時尚評鑑：客家指數 {data['hakkaIndex']}⭐",
                "content": content_encoded
            }
            if self.sha:
                body["sha"] = self.sha

            response = requests.put(github_file_url(), headers=github_headers(), json=body)

            if response.status_code in [200, 201]:
                star_emoji = "⭐" * data['hakkaIndex']
                await interaction.followup.send(
                    f"✅ 時尚評鑑已更新！\n"
                    f"客家指數：{star_emoji}\n"
                    f"By. {data['author'] or '（未填）'}\n"
                    f"建議：{data['content'] or '（未填）'}\n"
                    f"備註：{data['notes'] or '（未填）'}\n"
                    f"貼文連結：{data['threadsLink'] or '（未填）'}\n"
                    f"圖片1：{data['imageUrl'] or '（未填）'}\n"
                    f"圖片2：{data['imageUrl2'] or '（未填）'}"
                )
            else:
                error_msg = response.json().get('message', response.text)
                await interaction.followup.send(f"❌ 更新失敗：{error_msg}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤：{str(e)}", ephemeral=True)
            print(f"錯誤詳情：{e}")


@bot.event
async def on_ready():
    print(f'{bot.user} 已連接到 Discord！', flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個指令", flush=True)
    except Exception as e:
        print(f"同步指令時出錯：{e}", flush=True)


@bot.tree.command(name="時尚評鑑", description="更新時尚評鑑資訊（會跳出表單，直接帶出目前內容，穿搭建議/注意事項可以換行）")
@discord.app_commands.describe(
    image_url="圖片連結（選填，不填就維持原本圖片）",
    image_url2="第二張圖片連結（選填，不填就維持原本圖片）"
)
async def fashion_judging(
    interaction: discord.Interaction,
    image_url: str = None,
    image_url2: str = None
):
    await interaction.response.send_modal(FashionJudgingModal(image_url=image_url, image_url2=image_url2))


def sleep_then_exit(seconds, reason):
    """在容器裡「睡著」等一段時間，再讓程式結束。

    重點是「睡在程式結束之前」。部署平台看到程式結束就會馬上重開一份，
    如果登入失敗當下直接結束，就會變成每秒好幾次的重試風暴——而 Discord 前面的
    Cloudflare 是用 IP 計算次數的，重試風暴只會不斷延長那個 IP 的封鎖時間，
    讓它永遠解不開。先睡再結束，重試頻率就被壓成「每 N 秒一次」。
    """
    print(f"[啟動失敗] {reason}", flush=True)
    print(f"[啟動失敗] 等待 {seconds} 秒後再重試，避免把限流時間越拖越長。", flush=True)
    time.sleep(seconds)
    sys.exit(1)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        # token 沒設定的話重試幾百次也不會變好，直接停下來等人去修設定
        print("[設定錯誤] 找不到 DISCORD_TOKEN 環境變數，請到部署平台的環境變數設定。", flush=True)
        sleep_then_exit(3600, "缺少 DISCORD_TOKEN")

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        # token 是錯的，重試沒有意義，睡久一點避免無意義的請求
        sleep_then_exit(3600, "DISCORD_TOKEN 無效或已失效，請重新產生後更新環境變數。")
    except discord.PrivilegedIntentsRequired:
        sleep_then_exit(3600, "程式要求了未在 Developer Portal 開啟的特權意圖。")
    except discord.HTTPException as e:
        if e.status == 429:
            sleep_then_exit(
                RATE_LIMIT_SLEEP,
                "被 Discord/Cloudflare 限流（429 / Cloudflare 1015）。"
                "這通常是這台主機的對外 IP 被暫時封鎖，等一段時間就會自己解開。"
            )
        sleep_then_exit(GENERIC_ERROR_SLEEP, f"Discord 回傳 HTTP {e.status}：{e}")
    except Exception as e:
        sleep_then_exit(GENERIC_ERROR_SLEEP, f"未預期的錯誤：{type(e).__name__}: {e}")
