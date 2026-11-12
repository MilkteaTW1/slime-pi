# Social posts (drafts)

Status: drafts, nothing posted. Attach `docs/demo.en.gif` (X) or `docs/demo.zh-TW.gif` (Threads) unless noted. Put the GitHub link in the first reply on X rather than the main post, since link posts get less reach there.

Link: https://github.com/MilkteaTW1/slime-pi

---

## X / Twitter (English)

### 1. Launch post

My Raspberry Pi has a pet now.

It sweats when the CPU passes 65 °C, pants under load, sleeps after 11pm, and sulks if I don't SSH in for 3 days.

One Python file, no dependencies, runs as a user systemd service.

[GIF]

> Reply: Code and install (3 commands): https://github.com/MilkteaTW1/slime-pi

### 2. Feeding

You feed it by dragging files onto its web page.

It doesn't keep the file, only the name, size and extension. After 3 meals, whatever it ate most sets its personality.

Mostly .py: snakey, green.
Mostly images: dreamy, pink.
Mostly .exe: spicy.

[short screen recording of a drop]

### 3. The engineering bit

The rule I set for my Raspberry Pi pet: it must never be the reason the Pi struggles.

- capped at 10% of one core, 64 MB
- skips optional work when memory or load gets tight
- if the Pi stays critical for ~90 s, it says goodbye on the page and in `wall`, waits 30 s, and exits
- it does not restart itself

[screenshot of the goodbye bubble, from SLIME_FORCE_PRESSURE=memory]

---

## Threads（繁體中文）

### 1. 上線

我的樹莓派現在住了一隻史萊姆。

CPU 超過 65 度牠會流汗，負載高會喘，晚上 11 點後沒事就睡覺，我 3 天沒 SSH 進去牠就鬧彆扭。

整個程式只有一個 Python 檔，不用裝任何套件。原始碼放 GitHub，連結在留言。

[GIF]

### 2. 餵檔案

養法是把檔案拖到牠的網頁上餵牠吃。

檔案本身不會留下來，只記檔名、大小和副檔名。吃滿 3 餐後，吃最多的類型會決定個性：

一直餵 .py → 蛇味，綠色
一直餵照片 → 愛作夢，粉紅色
一直餵 .exe → 嗆辣

你們覺得自己的電腦會養出哪一種？

### 3. 每天的探險報告

每天第一次登入，牠會在家裡網路繞一圈，回來寫一份報告：今天遇到誰、誰是新來的、誰不見了。

只看你自己的 /24 網段，用最低優先權、一次 8 個 ping，結果只存在 Pi 上，不會傳到任何地方。

上週牠回報一台我不認得的裝置，查了才知道是新買的掃地機器人。

> 注意：第 3 則最後一句是範例，請換成你自己真的遇到的情況，或刪掉。
