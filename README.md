# 光戰每週小手帳

FF14（繁體中文服）每週／每日固定事項的追蹤小工具，玩家自製。

**正式網站**：https://hanzzzzzzzzzzzzzzzz.github.io/ff14-weekly/

跟 SQUARE ENIX／FINAL FANTASY XIV 官方沒有任何關係。

---

## 這個 repo 有什麼

| 檔案 | 用途 |
|---|---|
| `index.html` | **網站本體**。畫面、樣式、功能全部在這一個檔案裡，沒有任何外部相依。 |
| `fashion_bot.py` | 時尚評鑑的 Discord Bot。跑在另外的雲端主機上，不是網站的一部分。 |
| `fashion-judging.json` | Bot 寫入、網站讀取的資料檔。**不要手動編輯**，由 Bot 維護。 |
| `requirements.txt` | Bot 的 Python 套件清單。 |
| `Procfile` | Bot 的啟動指令（部署平台用）。 |
| `.gitignore` | 上傳排除清單，主要用來擋掉 `.env` 之類含金鑰的檔案。 |

---

## 網站

單一 HTML 檔，用 GitHub Pages 直接提供服務。

- **所有使用者資料都只存在瀏覽器的 localStorage**，不會傳到任何地方。
  也因此換裝置、換瀏覽器、清快取都會遺失，站上有「匯出備份 / 匯入備份」可以搬移。
- 所有時間換算統一以**台灣時間**為準（做法是把 UTC epoch 加 8 小時，
  再用 `getUTC*()` 讀出來當台灣的牆上時間）。
- 更新方式：把新版內容整份貼上來覆蓋 `index.html`。

站內功能：週間事項、時尚評鑑、仙人彩、日隨、籌備任務、友好部族、自訂清單、
行事曆，以及今日運勢、解答之書、擲骰器、工具箱、鬧鐘、便利貼等小工具。

---

## 時尚評鑑 Bot

朋友在 Discord 打 `/時尚評鑑` → 跳出表單（會帶出目前已存的內容）→ 送出後
Bot 把資料寫回這個 repo 的 `fashion-judging.json` → 網站讀取後顯示在卡片上。

### 執行環境

需要兩個環境變數，**一律由部署平台的環境變數提供，絕對不寫進程式碼**：

| 變數 | 用途 |
|---|---|
| `DISCORD_TOKEN` | Discord Bot 的 token |
| `GITHUB_TOKEN` | 寫入 `fashion-judging.json` 用的 GitHub token |

可選：`RATE_LIMIT_SLEEP`（被限流後等待秒數，預設 900）、
`GENERIC_ERROR_SLEEP`（其他錯誤等待秒數，預設 60）。

### 部署注意事項

**同一時間只能跑一份。** 兩份同時跑會導致同一個指令被回應兩次，
而且加倍觸發 Discord 的連線限制。

**啟動失敗時程式會先等待再結束，這是刻意的。** 部署平台看到程式結束會立刻重開，
如果失敗當下直接結束就會變成每秒數次的重試風暴；而 Discord 前面的 Cloudflare
是**按 IP** 計算次數的，重試風暴只會不斷延長該 IP 的封鎖時間（錯誤 1015），
讓它永遠解不開。所以 `sleep_then_exit()` 一定要保留。

部署平台若有重啟間隔設定（例如 systemd 的 `RestartSec`），建議設 60 秒以上當第二層保險。

### 疑難排解

| 症狀 | 意義 |
|---|---|
| `429` + `Cloudflare Error 1015` | 這台主機的**對外 IP** 被暫時封鎖，不是 token 問題。停掉重試，等它自己解開。 |
| `401` / `LoginFailure` | `DISCORD_TOKEN` 錯誤或已失效。 |
| `PrivilegedIntentsRequired` | 程式要求了 Developer Portal 沒開啟的特權意圖。 |
| 指令回應兩次 | 有兩份 bot 同時在跑。 |

---

## 安全

- Token 一律走環境變數，repo 內不含任何金鑰。
- 本機測試若建立 `.env`，已由 `.gitignore` 擋住，不要 commit。
- `index.html` 內只有公開的署名與公開的 JSON 網址。
