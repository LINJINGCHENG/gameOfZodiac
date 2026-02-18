import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from collections import Counter
import os
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 防休眠機制 (Keep Alive)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive! The bot is running."

def run():
    # 設定 Port 為 8080，這是雲端平台常用的 Port
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 🤖 機器人主程式
# ==========================================

# 設定 Intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- 詞庫設定 (全域變數) ---
SPY_WORDS_DATA = [
    # ==============================
    # 🍔 美食與飲品篇
    # ==============================
    ("麥當勞", "肯德基"), ("必勝客", "達美樂"), ("星巴克", "路易莎"),
    ("珍珠奶茶", "波霸奶茶"), ("可口可樂", "百事可樂"), ("雪碧", "七喜"),
    ("滷肉飯", "肉燥飯"), ("水餃", "鍋貼"), ("小籠包", "生煎包"),
    ("火鍋", "壽喜燒"), ("薑母鴨", "羊肉爐"), ("麻辣鍋", "臭臭鍋"),
    ("牛肉麵", "陽春麵"), ("義大利麵", "拉麵"), ("烏龍麵", "米苔目"),
    ("布丁", "奶酪"), ("冰淇淋", "霜淇淋"), ("鳳梨酥", "蛋黃酥"),
    ("紅豆餅", "雞蛋糕"), ("雞排", "鹹酥雞"), ("薯條", "薯餅"),
    ("奇異果", "火龍果"), ("柳丁", "橘子"), ("檸檬", "萊姆"),
    ("拿鐵", "卡布奇諾"), ("紅茶", "綠茶"), ("豆漿", "米漿"),
    ("布朗尼", "提拉米蘇"), ("泡麵", "乾拌麵"), ("自助餐", "便當"),

    # ==============================
    # 📱 生活與科技篇
    # ==============================
    ("臉書", "IG"), ("Threads", "Twitter"),
    ("LINE", "Messenger"), ("YouTube", "Netflix"), ("抖音", "Reels"),
    ("iPhone", "Android"), ("筆電", "桌機"), ("平板", "手機"),
    ("耳機", "喇叭"), ("滑鼠", "觸控板"), ("鍵盤", "打字機"),
    ("眼鏡", "隱形眼鏡"), ("墨鏡", "3D眼鏡"), ("手錶", "手環"),
    ("雨傘", "雨衣"), ("拖鞋", "涼鞋"), ("布鞋", "皮鞋"),
    ("牙刷", "電動牙刷"), ("洗髮精", "沐浴乳"), ("毛巾", "浴巾"),
    ("衛生紙", "濕紙巾"), ("棉被", "毛毯"), ("枕頭", "抱枕"),
    ("機車", "電動車"), ("腳踏車", "滑板車"),

    # ==============================
    # 🏫 地點與場所篇
    # ==============================
    ("7-11", "全家"), ("全聯", "家樂福"), ("好市多", "IKEA"),
    ("百貨公司", "Outlet"), ("夜市", "菜市場"), ("電影院", "歌劇院"),
    ("圖書館", "書店"), ("補習班", "學校"), ("幼稚園", "托兒所"),
    ("健身房", "運動中心"), ("公園", "遊樂園"), ("動物園", "水族館"),
    ("飯店", "民宿"), ("監獄", "看守所"), ("醫院", "診所"),

    # ==============================
    # 🦸 人物與角色篇
    # ==============================
    ("鋼鐵人", "蝙蝠俠"), ("蜘蛛人", "超人"), ("美國隊長", "雷神索爾"),
    ("哆啦A夢", "大雄"), ("蠟筆小新", "櫻桃小丸子"), ("海綿寶寶", "派大星"),
    ("柯南", "福爾摩斯"), ("哈利波特", "魔戒"), ("皮卡丘", "伊布"),
    ("YouTuber", "直播主"), ("藝人", "網紅"), ("歌手", "演員"),
    ("警察", "保全"), ("醫生", "護士"), ("老師", "教授"),
    ("班長", "風紀股長"), ("前男友", "前女友"), ("渣男", "暖男"),
    ("總經理", "董事長"), ("房東", "房客"),

    # ==============================
    # 🧠 抽象、狀態與行為篇
    # ==============================
    ("單身", "失戀"), ("初戀", "暗戀"), ("曖昧", "交往"),
    ("結婚", "訂婚"), ("離婚", "分居"), ("懷孕", "變胖"),
    ("自戀", "自信"), ("自大", "驕傲"), ("小氣", "節儉"),
    ("固執", "堅持"), ("隨便", "隨和"), ("活潑", "過動"),
    ("誠實", "老實"), ("說謊", "吹牛"), ("生氣", "暴怒"),
    ("開心", "興奮"), ("難過", "憂鬱"), ("緊張", "焦慮"),
    ("夢想", "幻想"), ("理想", "目標"), ("裸睡", "賴床"),
    ("遲到", "早退"), ("翹課", "請假"), ("加班", "值班"),
    ("中獎", "中籤")
]

# 遊戲狀態 Enum
class GamePhase:
    SETUP = 0
    SPEAKING = 1
    VOTING = 2
    GAME_OVER = 3
    WAITING_FOR_HOST_INPUT = 4 
    WHITEBOARD_GUESS = 5 

# 遊戲狀態儲存
class GameState:
    def __init__(self):
        self.reset_lobby()

    def reset_lobby(self):
        self.is_lobby_open = False
        self.game_type = None 
        self.players = [] 
        self.god_mode = False
        self.host = None
        self.game_channel = None
        self.god_channel = None
        self.phase = GamePhase.SETUP
        self.used_words = [] 
        self.reset_round_data()

    def reset_round_data(self):
        self.turn_index = 0
        self.alive_players = [] 
        self.spoken_players = [] 
        self.round_losers = [] 
        self.voting_unlocked = False 
        self.voting_task = None 
        self.votes = {} 
        self.password_number = 0
        self.password_range = [1, 100]
        self.spy_player = None
        self.whiteboard_player = None 
        self.civilian_word = ""
        self.spy_word = ""

current_game = GameState()
ALLOWED_CHANNEL_ID = 1472525156336275476 

@bot.event
async def on_ready():
    print(f'Bot 已登入: {bot.user}')
    print('-------------------------------------------')
    print('⚠️ 請務必在 Discord 頻道輸入 !sync 來載入指令！')
    print('-------------------------------------------')

# --- 強制同步指令 ---
@bot.command()
async def sync(ctx):
    await ctx.send(f"🔄 正在同步指令...")
    ctx.bot.tree.clear_commands(guild=ctx.guild)
    ctx.bot.tree.copy_global_to(guild=ctx.guild)
    synced = await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ 成功同步 {len(synced)} 個指令！")

# --- 第一階段：大廳與加入 ---

@bot.tree.command(name="open_game", description="開啟遊戲大廳")
@app_commands.describe(game_type="選擇遊戲類型")
@app_commands.choices(game_type=[
    app_commands.Choice(name="終極密碼", value="password"),
    app_commands.Choice(name="誰是臥底 (單票制)", value="spy")
])
async def open_game(interaction: discord.Interaction, game_type: app_commands.Choice[str]):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        return await interaction.response.send_message("❌ 此頻道無法開啟遊戲。", ephemeral=True)
    
    current_game.reset_lobby()
    current_game.is_lobby_open = True
    current_game.game_type = game_type.value
    current_game.host = interaction.user
    
    game_name = "💣 終極密碼" if game_type.value == 'password' else "🕵️ 誰是臥底 (單票制)"
    
    # 隱藏了 God Mode 的提示
    await interaction.response.send_message(
        f"📢 **{game_name}** 準備開啟！\n"
        f"想玩的請輸入 `/join` 或打 `+1`\n"
        f"人數到齊後主持人請用 `/start` 開始"
    )

@bot.tree.command(name="join", description="加入遊戲")
async def join(interaction: discord.Interaction):
    if not current_game.is_lobby_open:
        return await interaction.response.send_message("❌ 大廳尚未開啟。", ephemeral=True)
    if interaction.user in current_game.players:
        return await interaction.response.send_message("你已經在名單內了。", ephemeral=True)
    current_game.players.append(interaction.user)
    await interaction.response.send_message(f"✅ {interaction.user.display_name} 加入了遊戲！")

@bot.tree.command(name="god_mode", description="開啟上帝視角 (僅限主持人)")
async def god_mode(interaction: discord.Interaction):
    if interaction.user != current_game.host:
        return await interaction.response.send_message("❌ 只有主持人可以開啟。", ephemeral=True)
    current_game.god_mode = True
    await interaction.response.send_message("👁️ 上帝模式已啟用 (遊戲開始時生效)。", ephemeral=True)

# --- 第二階段：開始遊戲 ---

@bot.tree.command(name="start", description="開始遊戲 (僅限主持人)")
async def start(interaction: discord.Interaction):
    if not current_game.is_lobby_open or interaction.user != current_game.host:
        return await interaction.response.send_message("❌ 你不是主持人或大廳未開啟。", ephemeral=True)

    min_players = 4 if current_game.game_type == 'spy' else 2
    if len(current_game.players) < min_players:
        return await interaction.response.send_message(f"⚠️ 人數不足！{current_game.game_type} 模式至少需要 {min_players} 人！", ephemeral=True)

    current_game.is_lobby_open = False
    guild = interaction.guild
    
    await interaction.response.send_message("🚀 遊戲開始！正在建立私人頻道...")

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
        }
        for player in current_game.players:
            overwrites[player] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"遊戲室-{random.randint(1000,9999)}"
        game_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        current_game.game_channel = game_channel

        # 只有在啟用 god_mode 時才建立上帝視角頻道
        if current_game.god_mode:
            god_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                current_game.host: discord.PermissionOverwrite(read_messages=True)
            }
            god_channel = await guild.create_text_channel(f"上帝視角-{random.randint(1000,9999)}", overwrites=god_overwrites)
            current_game.god_channel = god_channel
        else:
            current_game.god_channel = None
            
    except Exception as e:
        print(f"Error: {e}")
        return await interaction.followup.send("❌ 建立頻道失敗，請檢查權限。")

    await init_game_logic()

# --- 遊戲邏輯初始化 ---

async def init_game_logic():
    current_game.reset_round_data()
    current_game.alive_players = current_game.players.copy()
    random.shuffle(current_game.alive_players)
    
    if current_game.game_type == 'password':
        current_game.phase = GamePhase.SPEAKING
        await setup_password_game()
    elif current_game.game_type == 'spy':
        await setup_spy_game()

async def setup_password_game():
    target = random.randint(1, 100)
    current_game.password_number = target
    if current_game.god_channel:
        await current_game.god_channel.send(f"💣 **爆炸數字是：{target}**")
    await current_game.game_channel.send(f"💣 **終極密碼開始！**\n範圍：1 ~ 100\n由 {current_game.alive_players[0].mention} 開始。")

async def setup_spy_game():
    available_indices = [i for i in range(len(SPY_WORDS_DATA)) if i not in current_game.used_words]
    
    if not available_indices:
        current_game.phase = GamePhase.WAITING_FOR_HOST_INPUT
        await current_game.game_channel.send("🔄 **內建詞庫已用完！**\n請主持人在 **上帝視角** 輸入 `平民詞 臥底詞`。")
        if current_game.god_channel:
            await current_game.god_channel.send("📝 **請輸入自訂題目！**\n格式：`蘋果 香蕉`")
        return

    selected_index = random.choice(available_indices)
    current_game.used_words.append(selected_index)
    pair = SPY_WORDS_DATA[selected_index]
    await start_spy_round(pair)

async def start_spy_round(pair):
    current_game.phase = GamePhase.SPEAKING
    current_game.civilian_word = pair[0]
    current_game.spy_word = pair[1]

    spy = random.choice(current_game.alive_players)
    current_game.spy_player = spy
    
    remaining = [p for p in current_game.alive_players if p != spy]
    whiteboard = random.choice(remaining)
    current_game.whiteboard_player = whiteboard
    
    if current_game.god_channel:
        msg = (f"🕵️ **角色分配**\n😈 臥底：{spy.display_name} ({pair[1]})\n"
               f"⬜ 白板：{whiteboard.display_name} (無詞)\n😇 平民詞：{pair[0]}")
        await current_game.god_channel.send(msg)

    for p in current_game.alive_players:
        try:
            if p == spy:
                await p.send(f"🤫 你的身分是 **臥底**！\n你的詞彙是：**{current_game.spy_word}**\n(若猜到平民詞，可用 `/answer` 自爆搶答)")
            elif p == whiteboard:
                await p.send(f"⬜ 你的身分是 **白板**！\n你 **沒有詞彙**。請假裝你知道。\n(若猜到平民詞，可用 `/answer` 搶答)")
            else:
                await p.send(f"😇 你的身分是 **平民**。\n你的詞彙是：**{current_game.civilian_word}**")
        except:
            await current_game.game_channel.send(f"⚠️ 無法私訊 {p.mention}，請開啟私訊功能！")

    msg = (f"🕵️ **誰是臥底 (單票制) 開始！**\n由 {current_game.alive_players[0].mention} 開始。\n"
           f"🗣️ 發言：`/speak`\n🗳️ 投票：`/vote <玩家>` (每人一票，票高者死)")
    await current_game.game_channel.send(msg)

# --- 核心指令：發言 ---

@bot.tree.command(name="speak", description="輸入發言")
async def speak(interaction: discord.Interaction, content: str):
    if not current_game.game_channel or interaction.channel_id != current_game.game_channel.id: return
    if current_game.phase != GamePhase.SPEAKING: return await interaction.response.send_message("❌ 非發言階段", ephemeral=True)
    if interaction.user not in current_game.alive_players: return await interaction.response.send_message("👻 你已出局", ephemeral=True)
    
    current_player = current_game.alive_players[current_game.turn_index]
    if interaction.user != current_player: return await interaction.response.send_message(f"🤫 輪到 {current_player.mention}", ephemeral=True)

    await interaction.response.defer() 

    if current_game.game_type == 'password':
        try:
            guess = int(content)
            low, high = current_game.password_range
            if not (low < guess < high): return await interaction.followup.send(f"⚠️ 請輸入 {low}~{high} 之間")
            
            await interaction.followup.send(f"🗣️ {interaction.user.display_name} 猜：**{guess}**")
            if guess == current_game.password_number:
                current_game.round_losers.append(interaction.user)
                await current_game.game_channel.send(f"💥 **BOOM！** {interaction.user.mention} 踩到炸彈！數字是 {guess}！\n遊戲結束！")
                current_game.phase = GamePhase.GAME_OVER
                return
            
            if guess < current_game.password_number: current_game.password_range[0] = guess
            else: current_game.password_range[1] = guess
            next_turn()
            await current_game.game_channel.send(f"範圍縮小：**{current_game.password_range[0]} ~ {current_game.password_range[1]}**\n換 {current_game.alive_players[current_game.turn_index].mention}")
        except ValueError: await interaction.followup.send("⚠️ 請輸入數字")

    elif current_game.game_type == 'spy':
        await interaction.followup.send(f"🗣️ {interaction.user.display_name}：**{content}**")
        if current_game.god_channel:
            role = "平民"
            if interaction.user == current_game.spy_player: role = "😈臥底"
            if interaction.user == current_game.whiteboard_player: role = "⬜白板"
            await current_game.god_channel.send(f"{role} {interaction.user.display_name}：{content}")

        if interaction.user not in current_game.spoken_players: current_game.spoken_players.append(interaction.user)
        if not current_game.voting_unlocked and len(current_game.spoken_players) >= len(current_game.alive_players):
            current_game.voting_unlocked = True
            await current_game.game_channel.send("✅ **第一輪結束，可開始投票！**")

        next_turn()
        await current_game.game_channel.send(f"換 {current_game.alive_players[current_game.turn_index].mention} 發言")

# --- 投票系統 (單票制) ---

@bot.tree.command(name="call_vote", description="發起投票 (限時5分鐘)")
async def call_vote(interaction: discord.Interaction):
    if not current_game.game_channel or interaction.channel_id != current_game.game_channel.id: return
    if current_game.game_type != 'spy': return
    if not current_game.voting_unlocked: return await interaction.response.send_message("❌ 第一輪未結束", ephemeral=True)
    if current_game.phase == GamePhase.VOTING: return await interaction.response.send_message("⚠️ 投票進行中", ephemeral=True)

    current_game.phase = GamePhase.VOTING
    current_game.votes = {}
    await interaction.response.send_message(f"🗳️ {interaction.user.display_name} 發起投票！")
    current_game.voting_task = bot.loop.create_task(voting_timer())
    await current_game.game_channel.send("📢 **投票開始！限時 5 分鐘！**\n請使用 `/vote <玩家>` 投出你覺得是壞人(臥底或白板)的人！")

async def voting_timer():
    try:
        await asyncio.sleep(300)
        if current_game.phase == GamePhase.VOTING:
            await current_game.game_channel.send("⏰ **時間到！強制結算！**")
            await process_voting_results_final()
    except asyncio.CancelledError: pass

@bot.tree.command(name="vote", description="投票淘汰某人")
@app_commands.describe(target="你覺得誰是壞人？")
async def vote(interaction: discord.Interaction, target: discord.Member):
    if current_game.phase != GamePhase.VOTING: return await interaction.response.send_message("❌ 非投票階段", ephemeral=True)
    if interaction.user not in current_game.alive_players: return await interaction.response.send_message("👻 死人無法投票", ephemeral=True)
    if target not in current_game.alive_players: return await interaction.response.send_message("⚠️ 目標已出局", ephemeral=True)

    # 記錄投票 (覆蓋舊票)
    current_game.votes[interaction.user] = target
    await interaction.response.send_message(f"🗳️ 你投給了 {target.display_name}。", ephemeral=True)
    await check_voting_progress()

async def check_voting_progress():
    finished = len(current_game.votes)
    total = len(current_game.alive_players)
    await current_game.game_channel.send(f"📊 投票進度：{finished}/{total}")
    if finished >= total and total > 0:
        if current_game.voting_task: current_game.voting_task.cancel()
        await process_voting_results_final()

# --- 結算與垂死掙扎邏輯 (單票制版) ---

async def process_voting_results_final():
    """投票結束，計算最高票者並處決"""
    await current_game.game_channel.send("🛑 **投票截止！統計中...**")
    await asyncio.sleep(2)

    if not current_game.votes:
        await current_game.game_channel.send("⚠️ 無人投票，本局無人淘汰。")
        await check_win_condition(from_voting=True)
        return

    # 統計票數
    vote_counts = Counter(current_game.votes.values())
    most_voted_player, count = vote_counts.most_common(1)[0]
    
    # 檢查平票
    if list(vote_counts.values()).count(count) > 1:
        await current_game.game_channel.send(f"⚖️ **平票！** (最高票數 {count})，無人被淘汰。")
        await check_win_condition(from_voting=True)
        return

    await current_game.game_channel.send(f"💀 **{most_voted_player.mention}** 以 {count} 票被處決了！")
    
    # 處理被處決者的身分
    real_wb = current_game.whiteboard_player
    real_spy = current_game.spy_player
    
    if most_voted_player == real_wb:
        # 白板被投死 -> 觸發垂死掙扎
        await current_game.game_channel.send(f"🚨 **他是白板！**\n但還沒結束... **你有 30 秒的時間在聊天室輸入平民詞！**\n猜對直接獲勝！")
        
        def check_guess(m):
            return m.author == real_wb and m.channel == current_game.game_channel

        try:
            msg = await bot.wait_for('message', check=check_guess, timeout=30.0)
            if msg.content.strip() == current_game.civilian_word:
                await current_game.game_channel.send(f"🎉 **白板猜對了！** 平民詞是 `{current_game.civilian_word}`！\n🏆 **白板逆轉獲勝！**")
                current_game.phase = GamePhase.GAME_OVER
                return 
            else:
                # 修正：如果臥底還活著，不公佈答案
                spy_alive = current_game.spy_player in current_game.alive_players
                if spy_alive:
                    await current_game.game_channel.send(f"❌ **猜錯了！**\n💀 白板正式出局。\n(為防止劇透，暫不公佈平民詞)")
                else:
                    await current_game.game_channel.send(f"❌ **猜錯了！** (正確是 `{current_game.civilian_word}`)\n💀 白板正式出局。")

        except asyncio.TimeoutError:
            await current_game.game_channel.send("⏰ **時間到！** 白板放棄掙扎。\n💀 白板正式出局。")
            
    elif most_voted_player == real_spy:
        await current_game.game_channel.send(f"🔫 **漂亮！** 你們抓到了一隻 **臥底**！")
    else:
        await current_game.game_channel.send(f"😭 **抓錯人了！** 他是無辜的 **平民**...")

    # 移除玩家
    current_game.round_losers.append(most_voted_player)
    if most_voted_player in current_game.alive_players:
        current_game.alive_players.remove(most_voted_player)

    # 檢查勝利條件
    await check_win_condition(from_voting=True)

# --- 勝利判定函式 ---

async def check_win_condition(from_voting=False):
    """檢查遊戲是否結束"""
    
    real_spy = current_game.spy_player
    real_wb = current_game.whiteboard_player
    
    spy_dead = real_spy not in current_game.alive_players
    wb_dead = real_wb not in current_game.alive_players
    
    # 1. 平民勝利：壞人全滅
    if spy_dead and wb_dead:
        await current_game.game_channel.send(f"🎉 **臥底和白板都死了！**\n平民詞：`{current_game.civilian_word}`\n臥底詞：`{current_game.spy_word}`\n🏆 **平民陣營獲勝！**")
        current_game.phase = GamePhase.GAME_OVER
        return

    # 2. 壞人勝利：壞人數 >= 平民數
    bad_guys_count = 0
    if not spy_dead: bad_guys_count += 1
    if not wb_dead: bad_guys_count += 1
    
    civilians_count = len(current_game.alive_players) - bad_guys_count
    
    if bad_guys_count >= civilians_count or civilians_count == 0:
        await current_game.game_channel.send("💀 **平民人數不足！壞人控場！**")
        if not wb_dead:
            await current_game.game_channel.send("🏆 **白板存活到最後，白板獲勝！**")
        else:
            await current_game.game_channel.send("🏆 **臥底獲勝！**")
        
        await current_game.game_channel.send(f"平民詞：`{current_game.civilian_word}`\n臥底詞：`{current_game.spy_word}`")
        current_game.phase = GamePhase.GAME_OVER
        return

    # 3. 遊戲繼續
    if from_voting:
        current_game.phase = GamePhase.SPEAKING
        current_game.turn_index = 0 
        await current_game.game_channel.send("🔄 **遊戲繼續！** 壞人尚未全滅。")
        if current_game.alive_players:
            await current_game.game_channel.send(f"現在輪到 {current_game.alive_players[0].mention} 發言。")

# --- 搶答與踢人 ---

@bot.tree.command(name="answer", description="臥底/白板搶答 (平民禁用)")
async def answer(interaction: discord.Interaction, guess: str):
    if not current_game.game_channel or interaction.channel_id != current_game.game_channel.id: return
    if interaction.user not in current_game.alive_players: return await interaction.response.send_message("👻 你已出局", ephemeral=True)
    
    is_spy = interaction.user == current_game.spy_player
    is_wb = interaction.user == current_game.whiteboard_player
    if not (is_spy or is_wb): return await interaction.response.send_message("❌ 平民不能搶答", ephemeral=True)

    await interaction.response.send_message(f"📢 {interaction.user.mention} 發起搶答：**{guess}**")
    
    if guess.strip() == current_game.civilian_word:
        role = "臥底" if is_spy else "白板"
        await current_game.game_channel.send(f"🎉 **猜對了！** {role} 猜到了平民詞！\n🏆 **壞人陣營獲勝！**")
        current_game.phase = GamePhase.GAME_OVER
    else:
        # 修正：猜錯不公佈答案，防止劇透
        await current_game.game_channel.send(f"🚫 **猜錯！** {interaction.user.mention} 自殺出局。")
        current_game.round_losers.append(interaction.user)
        current_game.alive_players.remove(interaction.user)
        
        if interaction.user in current_game.votes:
            del current_game.votes[interaction.user]
        
        # 檢查是否結束，如果沒結束，需要確保遊戲流程繼續
        await check_win_condition(from_voting=False)
        
        # 修正：如果遊戲沒結束，需要明確提示下一位，防止卡住
        if current_game.phase != GamePhase.GAME_OVER:
            if current_game.turn_index >= len(current_game.alive_players):
                 current_game.turn_index = 0
            
            # 提示下一位發言者
            next_player = current_game.alive_players[current_game.turn_index]
            await current_game.game_channel.send(f"🔄 遊戲繼續！下一位發言：{next_player.mention}")

@bot.tree.command(name="kick_player", description="踢人")
async def kick_player(interaction: discord.Interaction, target: discord.Member):
    if interaction.user != current_game.host: return await interaction.response.send_message("❌ 限主持人", ephemeral=True)
    if target not in current_game.alive_players: return await interaction.response.send_message("⚠️ 玩家不在名單", ephemeral=True)
    
    current_speaker = current_game.alive_players[current_game.turn_index]
    current_game.alive_players.remove(target)
    if target in current_game.players: current_game.players.remove(target)
    
    msg = f"👢 **{target.display_name}** 被踢出！"
    if current_game.phase == GamePhase.SPEAKING:
        if target in current_game.spoken_players: current_game.spoken_players.remove(target)
        if target == current_speaker:
            if current_game.turn_index >= len(current_game.alive_players): current_game.turn_index = 0
            msg += f"\n⏩ 換 {current_game.alive_players[current_game.turn_index].mention} 發言"
        else:
            try: current_game.turn_index = current_game.alive_players.index(current_speaker)
            except: current_game.turn_index = 0
    elif current_game.phase == GamePhase.VOTING:
        if target in current_game.votes: del current_game.votes[target]
        msg += "\n票作廢"
        await interaction.response.send_message(msg)
        await check_voting_progress()
        return

    await interaction.response.send_message(msg)
    if len(current_game.alive_players) < 2:
        await current_game.game_channel.send("⚠️ 人數不足，結束")
        current_game.phase = GamePhase.GAME_OVER

@bot.tree.command(name="pass_turn", description="跳過回合")
async def pass_turn(interaction: discord.Interaction):
    if interaction.user != current_game.host: return
    next_turn()
    await interaction.response.send_message(f"⏩ 換 {current_game.alive_players[current_game.turn_index].mention}")

@bot.tree.command(name="restart", description="重新開始")
async def restart(interaction: discord.Interaction):
    if interaction.user != current_game.host: return
    if current_game.voting_task: current_game.voting_task.cancel()
    
    msg = "🔄 **重新洗牌...**"
    if current_game.round_losers: msg += f"\n💀 上局輸家：{', '.join([p.display_name for p in current_game.round_losers])}"
    await interaction.response.send_message(msg)
    
    min_p = 4 if current_game.game_type == 'spy' else 2
    if len(current_game.players) < min_p: return await current_game.game_channel.send("⚠️ 人數不足")
    await init_game_logic()

def next_turn():
    if not current_game.alive_players: return
    current_game.turn_index = (current_game.turn_index + 1) % len(current_game.alive_players)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if current_game.is_lobby_open and message.content.strip() == "+1" and message.channel.id == ALLOWED_CHANNEL_ID:
        if message.author not in current_game.players:
            current_game.players.append(message.author)
            await message.add_reaction("✅")
        return
    
    if current_game.phase == GamePhase.WAITING_FOR_HOST_INPUT and message.channel == current_game.god_channel and message.author == current_game.host:
        parts = message.content.strip().split()
        if len(parts) == 2:
            await message.channel.send("✅ 題目已設定！")
            await start_spy_round((parts[0], parts[1]))
        else: await message.channel.send("⚠️ 格式錯：`詞1 詞2`")
        return

    await bot.process_commands(message)

# ==========================================
# 🚀 啟動機器人 (使用環境變數)
# ==========================================
keep_alive() # 啟動防休眠網站
bot.run(os.getenv('DISCORD_TOKEN')) # 從環境變數讀取 Token
