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
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 🤖 機器人主程式
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- 詞庫設定 (全域變數) ---
SPY_WORDS_DATA = [
    # 🔥 陷阱題：外觀或動作相似，但後果不同
    ("牙刷", "馬桶刷"), ("雨傘", "降落傘"), ("口香糖", "保險套"),
    ("內褲", "尿布"), ("救生圈", "甜甜圈"), ("麥克風", "霜淇淋"),
    ("香水", "殺蟲劑"), ("唇膏", "印章"), ("手銬", "手鐲"),

    # 🧠 燒腦題：抽象概念與狀態
    ("緣分", "巧合"), ("獎金", "薪水"), ("裸睡", "泡湯"),
    ("自戀", "自信"), ("曖昧", "劈腿"), ("初戀", "前任"),
    ("夢想", "幻想"), ("固執", "堅持"), ("小氣", "節儉"),
    ("流浪", "旅遊"), ("整容", "化妝"), ("八卦", "新聞"),

    # 🍔 食物題：成分相似但地位不同
    ("水餃", "小籠包"), ("生魚片", "壽司"), ("拿鐵", "奶茶"),
    ("火鍋", "麻辣燙"), ("自助餐", "辦桌"), ("牛肉麵", "牛排"),
    ("可樂", "醬油"), ("白酒", "米酒"), ("榴槤", "臭豆腐"),

    # 🦸 人物題：身分微妙差異
    ("富二代", "暴發戶"), ("渣男", "中央空調"), ("女神", "女漢子"),
    ("保全", "保鑣"), ("魔術師", "騙子"), ("總裁", "老闆"),
    ("房東", "管家"), ("間諜", "狗仔"), ("駭客", "工程師"),
    ("女朋友", "乾妹妹"), ("男朋友", "男閨蜜"), ("媽媽", "婆婆"),

    # 🏠 生活與物品：容易混淆
    ("鏡子", "相機"), ("枕頭", "布偶"), ("鉛筆", "眉筆"),
    ("這裡", "那裡"), ("今天", "明天"), ("左邊", "右邊"),
    ("臉書", "日記"), ("手機", "對講機"), ("眼鏡", "放大鏡"),
    ("電梯", "手扶梯"), ("斑馬線", "起跑線"), ("監獄", "學校")
]


# 遊戲狀態 Enum
class GamePhase:
    SETUP = 0
    SPEAKING = 1
    VOTING = 2
    GAME_OVER = 3
    WAITING_FOR_HOST_INPUT = 4 
    WHITEBOARD_GUESS = 5
    # --- 狼人殺階段 ---
    WEREWOLF_NIGHT = 10
    WEREWOLF_DAY = 11

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
        self.wolf_channel = None 
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
        # 臥底相關
        self.spy_player = None
        self.whiteboard_player = None 
        self.civilian_word = ""
        self.spy_word = ""
        # 狼人殺相關
        self.roles = {} 
        self.night_actions = {"wolf_kill": None, "witch_save": False, "witch_poison": None}
        self.witch_inventory = {"antidote": True, "poison": True}

current_game = GameState()
ALLOWED_CHANNEL_ID = 1472525156336275476 

@bot.event
async def on_ready():
    print(f'Bot 已登入: {bot.user}')
    print('-------------------------------------------')
    print('⚠️ 請務必在 Discord 頻道輸入 !sync 來載入指令！')
    print('-------------------------------------------')

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
    app_commands.Choice(name="誰是臥底 (單票制)", value="spy"),
    app_commands.Choice(name="狼人殺 (標準局)", value="werewolf")
])
async def open_game(interaction: discord.Interaction, game_type: app_commands.Choice[str]):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        return await interaction.response.send_message("❌ 此頻道無法開啟遊戲。", ephemeral=True)
    
    current_game.reset_lobby()
    current_game.is_lobby_open = True
    current_game.game_type = game_type.value
    current_game.host = interaction.user
    
    game_names = {
        "password": "💣 終極密碼",
        "spy": "🕵️ 誰是臥底 (單票制)",
        "werewolf": "🐺 狼人殺 (標準局)"
    }
    
    await interaction.response.send_message(
        f"📢 **{game_names[game_type.value]}** 準備開啟！\n"
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

    min_players = 2
    if current_game.game_type == 'spy': min_players = 4
    if current_game.game_type == 'werewolf': min_players = 6 
    
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

        if current_game.game_type == 'werewolf':
            # 修正：不把主持人加入狼人頻道
            wolf_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            current_game.wolf_channel = await guild.create_text_channel(f"🐺狼人窩-{random.randint(1000,9999)}", overwrites=wolf_overwrites)
            
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
    elif current_game.game_type == 'werewolf':
        await setup_werewolf_game()

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
            if p == spy: await p.send(f"🤫 你的身分是 **臥底**！\n你的詞彙是：**{current_game.spy_word}**")
            elif p == whiteboard: await p.send(f"⬜ 你的身分是 **白板**！\n你 **沒有詞彙**。")
            else: await p.send(f"😇 你的身分是 **平民**。\n你的詞彙是：**{current_game.civilian_word}**")
        except: pass

    msg = (f"🕵️ **誰是臥底 (單票制) 開始！**\n由 {current_game.alive_players[0].mention} 開始。\n"
           f"🗣️ 發言：`/speak`\n🗳️ 投票：`/vote <玩家>`")
    await current_game.game_channel.send(msg)

# --- 🐺 狼人殺邏輯 ---

async def setup_werewolf_game():
    players = current_game.alive_players
    count = len(players)
    
    roles_list = []
    if count < 9:
        roles_list = ["狼人"]*2 + ["村民"]*2 + ["預言家", "女巫"]
        while len(roles_list) < count: roles_list.append("村民")
    else:
        roles_list = ["狼人"]*3 + ["村民"]*3 + ["預言家", "女巫", "獵人"]
        while len(roles_list) < count: roles_list.append("村民")
        
    random.shuffle(roles_list)
    current_game.roles = {p: r for p, r in zip(players, roles_list)}
    
    wolves = [p for p, r in current_game.roles.items() if r == "狼人"]
    
    if current_game.wolf_channel:
        for wolf in wolves:
            await current_game.wolf_channel.set_permissions(wolf, read_messages=True, send_messages=True)

    for p, role in current_game.roles.items():
        try:
            msg = f"📜 你的身分是：**{role}**"
            if role == "狼人":
                teammates = [w.display_name for w in wolves if w != p]
                msg += f"\n你的隊友：{', '.join(teammates) if teammates else '無'}"
                msg += f"\n請在 **{current_game.wolf_channel.mention}** 討論戰術。"
            await p.send(msg)
        except:
            await current_game.game_channel.send(f"⚠️ 無法私訊 {p.mention}，請自行確認身分。")

    if current_game.god_channel:
        role_info = "\n".join([f"{p.display_name}: {r}" for p, r in current_game.roles.items()])
        await current_game.god_channel.send(f"🐺 **狼人殺配置**\n{role_info}")

    current_game.phase = GamePhase.WEREWOLF_NIGHT
    await current_game.game_channel.send(
        "🐺 **狼人殺遊戲開始！**\n"
        "現在進入 **夜晚** 🌑\n"
        "請主持人在所有動作完成後，輸入 `/next_phase` 進入白天。"
    )
    await start_night_phase()

async def start_night_phase():
    current_game.night_actions = {"wolf_kill": None, "witch_save": False, "witch_poison": None}
    
    await current_game.game_channel.set_permissions(current_game.game_channel.guild.default_role, send_messages=False)
    for p in current_game.players:
        await current_game.game_channel.set_permissions(p, send_messages=False)
    
    await current_game.game_channel.send("🌙 **天黑請閉眼**... 狼人請殺人，神職請行動。")
    if current_game.wolf_channel:
        await current_game.wolf_channel.send("🐺 **狼人請殺人**\n輸入 `/wolf_kill <玩家>` 選擇目標。")

# --- 狼人殺指令 ---

@bot.tree.command(name="next_phase", description="推進遊戲階段 (天黑/天亮)")
async def next_phase(interaction: discord.Interaction):
    if interaction.user != current_game.host: return await interaction.response.send_message("❌ 限主持人", ephemeral=True)
    if current_game.game_type != 'werewolf': return await interaction.response.send_message("❌ 非狼人殺模式", ephemeral=True)

    await interaction.response.defer()

    if current_game.phase == GamePhase.WEREWOLF_NIGHT:
        current_game.phase = GamePhase.WEREWOLF_DAY
        
        dead_players = []
        wolf_target = current_game.night_actions["wolf_kill"]
        
        if wolf_target and current_game.night_actions["witch_save"]:
            wolf_target = None 
        
        if wolf_target: dead_players.append(wolf_target)
        
        poison_target = current_game.night_actions["witch_poison"]
        if poison_target: dead_players.append(poison_target)
        
        dead_names = []
        for p in dead_players:
            if p in current_game.alive_players:
                current_game.alive_players.remove(p)
                dead_names.append(p.display_name)
        
        for p in current_game.players:
            await current_game.game_channel.set_permissions(p, send_messages=True)
            
        await current_game.game_channel.send("☀️ **天亮了！**")
        if dead_names:
            await current_game.game_channel.send(f"昨晚死亡的是：**{', '.join(dead_names)}**")
        else:
            await current_game.game_channel.send("昨晚是 **平安夜**！")
            
        await check_werewolf_win()
        if current_game.phase != GamePhase.GAME_OVER:
            await current_game.game_channel.send("🗣️ 請開始討論！\n討論結束後主持人請輸入 `/call_vote` 進行投票。")

    elif current_game.phase == GamePhase.WEREWOLF_DAY:
        current_game.phase = GamePhase.WEREWOLF_NIGHT
        await start_night_phase()
        await interaction.followup.send("🌑 進入夜晚。")

@bot.tree.command(name="wolf_kill", description="狼人殺人 (僅限狼人頻道)")
async def wolf_kill(interaction: discord.Interaction, target: discord.Member):
    if current_game.wolf_channel and interaction.channel_id != current_game.wolf_channel.id:
        return await interaction.response.send_message("❌ 只能在狼人頻道使用", ephemeral=True)
    if current_game.phase != GamePhase.WEREWOLF_NIGHT:
        return await interaction.response.send_message("❌ 現在不是夜晚", ephemeral=True)
    
    current_game.night_actions["wolf_kill"] = target
    await interaction.response.send_message(f"🐺 狼人鎖定目標：**{target.display_name}**")
    
    if current_game.god_channel:
        await current_game.god_channel.send(f"🔪 狼人想殺：{target.display_name}")

    # 修正：自動私訊女巫
    witch = None
    for p, r in current_game.roles.items():
        if r == "女巫" and p in current_game.alive_players:
            witch = p
            break
    
    if witch:
        try:
            await witch.send(f"🧪 **女巫請注意**！今晚狼人想殺：**{target.display_name}**\n你可以使用 `/witch_action action:使用解藥` 來救他。")
        except:
            if current_game.god_channel: await current_game.god_channel.send("⚠️ 無法私訊女巫 (可能關閉私訊)")

@bot.tree.command(name="seer_check", description="預言家查驗 (僅限預言家)")
async def seer_check(interaction: discord.Interaction, target: discord.Member):
    if current_game.roles.get(interaction.user) != "預言家":
        return await interaction.response.send_message("❌ 你不是預言家", ephemeral=True)
    if current_game.phase != GamePhase.WEREWOLF_NIGHT:
        return await interaction.response.send_message("❌ 天亮了不能查", ephemeral=True)

    role = current_game.roles.get(target)
    result = "🐺 狼人" if role == "狼人" else "😇 好人"
    
    await interaction.response.send_message(f"🔮 查驗結果：{target.display_name} 是 **{result}**", ephemeral=True)
    if current_game.god_channel:
        await current_game.god_channel.send(f"🔮 預言家查了 {target.display_name} -> {result}")

@bot.tree.command(name="witch_action", description="女巫行動 (僅限女巫)")
@app_commands.choices(action=[
    app_commands.Choice(name="使用解藥", value="save"),
    app_commands.Choice(name="使用毒藥", value="poison")
])
async def witch_action(interaction: discord.Interaction, action: app_commands.Choice[str], target: discord.Member = None):
    if current_game.roles.get(interaction.user) != "女巫":
        return await interaction.response.send_message("❌ 你不是女巫", ephemeral=True)
    if current_game.phase != GamePhase.WEREWOLF_NIGHT:
        return await interaction.response.send_message("❌ 天亮了不能用", ephemeral=True)

    kill_target = current_game.night_actions.get("wolf_kill")

    if action.value == "save":
        if not current_game.witch_inventory["antidote"]:
            return await interaction.response.send_message("❌ 解藥用光了", ephemeral=True)
        if not kill_target:
            return await interaction.response.send_message("❌ 狼人還沒殺人，無法救", ephemeral=True)
        
        current_game.night_actions["witch_save"] = True
        current_game.witch_inventory["antidote"] = False
        await interaction.response.send_message(f"🧪 你救了 {kill_target.display_name}", ephemeral=True)
        if current_game.god_channel: await current_game.god_channel.send(f"🧪 女巫救了 {kill_target.display_name}")

    elif action.value == "poison":
        if not current_game.witch_inventory["poison"]:
            return await interaction.response.send_message("❌ 毒藥用光了", ephemeral=True)
        if not target:
            return await interaction.response.send_message("⚠️ 請選擇毒殺對象", ephemeral=True)
        
        current_game.night_actions["witch_poison"] = target
        current_game.witch_inventory["poison"] = False
        await interaction.response.send_message(f"🧪 你毒死了 {target.display_name}", ephemeral=True)
        if current_game.god_channel: await current_game.god_channel.send(f"🧪 女巫毒了 {target.display_name}")

async def check_werewolf_win():
    wolves = [p for p in current_game.alive_players if current_game.roles.get(p) == "狼人"]
    villagers = [p for p in current_game.alive_players if current_game.roles.get(p) == "村民"]
    gods = [p for p in current_game.alive_players if current_game.roles.get(p) in ["預言家", "女巫", "獵人"]]
    
    if not wolves:
        await current_game.game_channel.send("🎉 **狼人全滅！好人陣營獲勝！**")
        current_game.phase = GamePhase.GAME_OVER
    elif not villagers or not gods: 
        await current_game.game_channel.send("🎉 **屠邊成功！狼人陣營獲勝！**")
        current_game.phase = GamePhase.GAME_OVER

# --- 共用指令：發言與投票 ---

@bot.tree.command(name="speak", description="輸入發言")
async def speak(interaction: discord.Interaction, content: str):
    if not current_game.game_channel or interaction.channel_id != current_game.game_channel.id: return
    if current_game.game_type == 'werewolf':
        return await interaction.response.send_message("🐺 狼人殺請直接在頻道打字聊天即可。", ephemeral=True)
    
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

@bot.tree.command(name="call_vote", description="發起投票 (限時5分鐘)")
async def call_vote(interaction: discord.Interaction):
    if not current_game.game_channel or interaction.channel_id != current_game.game_channel.id: return
    if current_game.phase == GamePhase.VOTING: return await interaction.response.send_message("⚠️ 投票進行中", ephemeral=True)
    
    if current_game.game_type == 'werewolf':
        if current_game.phase != GamePhase.WEREWOLF_DAY:
            return await interaction.response.send_message("❌ 只有白天可以投票", ephemeral=True)
    elif current_game.game_type == 'spy':
        if not current_game.voting_unlocked: return await interaction.response.send_message("❌ 第一輪未結束", ephemeral=True)

    current_game.phase = GamePhase.VOTING
    current_game.votes = {}
    await interaction.response.send_message(f"🗳️ {interaction.user.display_name} 發起投票！")
    current_game.voting_task = bot.loop.create_task(voting_timer())
    await current_game.game_channel.send("📢 **投票開始！限時 5 分鐘！**\n請使用 `/vote <玩家>` 投出你想處決的人！")

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

async def process_voting_results_final():
    await current_game.game_channel.send("🛑 **投票截止！統計中...**")
    await asyncio.sleep(2)

    if not current_game.votes:
        await current_game.game_channel.send("⚠️ 無人投票，本局無人淘汰。")
        if current_game.game_type == 'spy': await check_win_condition(from_voting=True)
        elif current_game.game_type == 'werewolf': 
            current_game.phase = GamePhase.WEREWOLF_DAY 
            await current_game.game_channel.send("請主持人輸入 `/next_phase` 進入夜晚。")
        return

    vote_counts = Counter(current_game.votes.values())
    most_voted_player, count = vote_counts.most_common(1)[0]
    
    if list(vote_counts.values()).count(count) > 1:
        await current_game.game_channel.send(f"⚖️ **平票！** (最高票數 {count})，無人被淘汰。")
        if current_game.game_type == 'spy': await check_win_condition(from_voting=True)
        elif current_game.game_type == 'werewolf': 
            current_game.phase = GamePhase.WEREWOLF_DAY
            await current_game.game_channel.send("請主持人輸入 `/next_phase` 進入夜晚。")
        return

    await current_game.game_channel.send(f"💀 **{most_voted_player.mention}** 以 {count} 票被處決了！")
    
    current_game.round_losers.append(most_voted_player)
    if most_voted_player in current_game.alive_players:
        current_game.alive_players.remove(most_voted_player)

    if current_game.game_type == 'spy':
        real_wb = current_game.whiteboard_player
        real_spy = current_game.spy_player
        
        if most_voted_player == real_wb:
            await current_game.game_channel.send(f"🚨 **他是白板！**\n但還沒結束... **你有 30 秒的時間在聊天室輸入平民詞！**")
            def check_guess(m): return m.author == real_wb and m.channel == current_game.game_channel
            try:
                msg = await bot.wait_for('message', check=check_guess, timeout=30.0)
                if msg.content.strip() == current_game.civilian_word:
                    await current_game.game_channel.send(f"🎉 **白板猜對了！** 平民詞是 `{current_game.civilian_word}`！\n🏆 **白板逆轉獲勝！**")
                    current_game.phase = GamePhase.GAME_OVER
                    return 
                else:
                    spy_alive = current_game.spy_player in current_game.alive_players
                    if spy_alive: await current_game.game_channel.send(f"❌ **猜錯了！**\n💀 白板正式出局。")
                    else: await current_game.game_channel.send(f"❌ **猜錯了！** (正確是 `{current_game.civilian_word}`)\n💀 白板正式出局。")
            except asyncio.TimeoutError:
                await current_game.game_channel.send("⏰ **時間到！** 白板放棄掙扎。\n💀 白板正式出局。")
        elif most_voted_player == real_spy: await current_game.game_channel.send(f"🔫 **漂亮！** 你們抓到了一隻 **臥底**！")
        else: await current_game.game_channel.send(f"😭 **抓錯人了！** 他是無辜的 **平民**...")
        await check_win_condition(from_voting=True)

    elif current_game.game_type == 'werewolf':
        role = current_game.roles.get(most_voted_player)
        await current_game.game_channel.send(f"他的身分是：**{role}**") 
        await check_werewolf_win()
        if current_game.phase != GamePhase.GAME_OVER:
            current_game.phase = GamePhase.WEREWOLF_DAY
            await current_game.game_channel.send("請主持人輸入 `/next_phase` 進入夜晚。")

async def check_win_condition(from_voting=False):
    real_spy = current_game.spy_player
    real_wb = current_game.whiteboard_player
    spy_dead = real_spy not in current_game.alive_players
    wb_dead = real_wb not in current_game.alive_players
    if spy_dead and wb_dead:
        await current_game.game_channel.send(f"🎉 **臥底和白板都死了！**\n平民詞：`{current_game.civilian_word}`\n臥底詞：`{current_game.spy_word}`\n🏆 **平民陣營獲勝！**")
        current_game.phase = GamePhase.GAME_OVER
        return
    bad_guys_count = 0
    if not spy_dead: bad_guys_count += 1
    if not wb_dead: bad_guys_count += 1
    civilians_count = len(current_game.alive_players) - bad_guys_count
    if bad_guys_count >= civilians_count or civilians_count == 0:
        await current_game.game_channel.send("💀 **平民人數不足！壞人控場！**")
        if not wb_dead: await current_game.game_channel.send("🏆 **白板存活到最後，白板獲勝！**")
        else: await current_game.game_channel.send("🏆 **臥底獲勝！**")
        await current_game.game_channel.send(f"平民詞：`{current_game.civilian_word}`\n臥底詞：`{current_game.spy_word}`")
        current_game.phase = GamePhase.GAME_OVER
        return
    if from_voting:
        current_game.phase = GamePhase.SPEAKING
        current_game.turn_index = 0 
        await current_game.game_channel.send("🔄 **遊戲繼續！** 壞人尚未全滅。")
        if current_game.alive_players:
            await current_game.game_channel.send(f"現在輪到 {current_game.alive_players[0].mention} 發言。")

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
        await current_game.game_channel.send(f"🚫 **猜錯！** {interaction.user.mention} 自殺出局。")
        current_game.round_losers.append(interaction.user)
        current_game.alive_players.remove(interaction.user)
        if interaction.user in current_game.votes: del current_game.votes[interaction.user]
        await check_win_condition(from_voting=False)
        if current_game.phase != GamePhase.GAME_OVER:
            if current_game.turn_index >= len(current_game.alive_players): current_game.turn_index = 0
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
    min_p = 2
    if current_game.game_type == 'spy': min_p = 4
    if current_game.game_type == 'werewolf': min_p = 6
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

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
