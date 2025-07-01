import discord
from discord.ext import commands, tasks
import socket, struct, time, json

# ==== LOAD CONFIG ====
with open("config.json", "r") as f:
    cfg = json.load(f)

TOKEN = cfg["TOKEN"]
CHANNEL_ID = int(cfg["CHANNEL_ID"])
SERVER_IP = cfg["SERVER_IP"]
SERVER_PORT = int(cfg["SERVER_PORT"])

LOGO_URL = "https://cdn.discordapp.com/attachments/1388392100394958879/1388468081084469318/IMG-20250626-WA0001.jpg"
COLOR_GREEN = discord.Color.from_str("#1abc9c")
COLOR_RED = discord.Color.red()

# ==== SAMP QUERY ====
def decode_samp_string(data):
    charset = ''.join([chr(i) for i in range(128)]) + (
        '€�‚ƒ„…†‡�‰�‹�����‘’“”•–—�™�›���� ΅Ά£¤¥¦§¨©�«¬­®―°±²³΄µ¶·ΈΉΊ»Ό½ΎΏΐΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡ�ΣΤΥΦΧΨΩΪΫάέήίΰαβγδεζηθικλμνξοπρςστυφχψωϊϋόύώ�'
    )
    decoded = ''
    for b in data:
        index = b * 2
        if index + 1 < len(charset.encode('utf-16-le')):
            decoded += (charset.encode('utf-16-le')[index:index+2]).decode('utf-16-le')
    return decoded

def query_samp_info(ip, port):
    def send(opcode):
        packet = b'SAMP' + bytes(map(int, ip.split('.'))) + struct.pack('<H', port) + opcode.encode('ascii')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        try:
            start = time.time()
            s.sendto(packet, (ip, port))
            data, _ = s.recvfrom(4096)
            ping = int((time.time() - start) * 1000)
            return data[11:], ping
        except:
            return None, None
        finally:
            s.close()

    info_data, ping = send("i")
    if not info_data: return None

    try:
        offset = 0
        info = {}
        info["ping"] = ping
        info["passworded"] = info_data[offset]; offset += 1
        info["players"] = struct.unpack('<H', info_data[offset:offset+2])[0]; offset += 2
        info["maxplayers"] = struct.unpack('<H', info_data[offset:offset+2])[0]; offset += 2

        for key in ["hostname", "gamemode", "mapname"]:
            strlen = struct.unpack('<I', info_data[offset:offset+4])[0]; offset += 4
            info[key] = decode_samp_string(info_data[offset:offset+strlen]); offset += strlen

    except: return None

    rules_data, _ = send("r")
    rules = {}
    try:
        count = struct.unpack('<H', rules_data[:2])[0]; offset = 2
        for _ in range(count):
            klen = rules_data[offset]; offset += 1
            key = decode_samp_string(rules_data[offset:offset+klen]); offset += klen
            vlen = rules_data[offset]; offset += 1
            val = decode_samp_string(rules_data[offset:offset+vlen]); offset += vlen
            rules[key] = val
    except: rules = {}

    return {"info": info, "rules": rules}

# ==== DISCORD BOT ====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
message_id = None

@bot.event
async def on_ready():
    print(f"✅ Bot is active as {bot.user}")
    monitor_server.start()

@tasks.loop(seconds=10)
async def monitor_server():
    global message_id
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Channel not found.")
        return

    data = query_samp_info(SERVER_IP, SERVER_PORT)
    now = time.strftime("%B %d, %Y • %H:%M:%S")

    if not data:
        embed = discord.Embed(
        title="Som City Roleplay V3",
        color=discord.Color.red()
   )
        embed.add_field(name="STATUS", value=f"```🔴 Offline```", inline=False)
        embed.add_field(name="PLAYERS", value=f"```0 / 200```", inline=False)
        embed.set_footer(text=f"Last Checked • {now}")
        embed.set_image(url="https://cdn.discordapp.com/attachments/1388392100394958879/1388468081084469318/IMG-20250626-WA0001.jpg")
        embed.set_footer(text=f"Last checked: {now}")
    else:
        info = data['info']
        rules = data['rules']
        embed = discord.Embed(
            title=f"🌍 {info['hostname']}",
            description="Welcome to **Som City Roleplay** server!",
            color=COLOR_GREEN
        )
        embed.set_thumbnail(url=LOGO_URL)
        embed.add_field(name="STATUS", value=f"```🟢 Online```")
        embed.add_field(name="PLAYERS", value=f"```{info['players']} / {info['maxplayers']}```")
        embed.add_field(name="F8 CONNECT", value=f"```connect {SERVER_IP}:{SERVER_PORT}```")
        embed.add_field(name="LANGUAGE", value=f"```{info['mapname']}```")
        embed.add_field(name="WEBSITE", value=f"```{rules.get('weburl', 'Unknown')}```")
        embed.add_field(name="PING SERVER", value=f"```{info['ping']} ms```")
        embed.set_image(url=LOGO_URL)
        embed.set_footer(text=f"Last checked: {now}")

    try:
        if message_id is None:
            msg = await channel.send(embed=embed)
            message_id = msg.id
        else:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
    except Exception as e:
        print(f"❌ Failed to send/update embed: {e}")

bot.run(TOKEN)
