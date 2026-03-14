import asyncio
import sys
import os
import json
import traceback
import logging
import inspect
import discord
from discord.ext import commands

# ───────────────────────────────────────────────
# 🧠 Windows event loop fix
# ───────────────────────────────────────────────
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ───────────────────────────────────────────────
# 📁 Working directory and config
# ───────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open("config.json", "r", encoding="utf-8"))

# ───────────────────────────────────────────────
# 🧾 Logging setup
# ───────────────────────────────────────────────
try:
    discord.utils.setup_logging()
except AttributeError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
logging.getLogger("discord.gateway").setLevel(logging.ERROR)

# ───────────────────────────────────────────────
# 💡 Intents
# ───────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ───────────────────────────────────────────────
# 🤖 Bot setup
# ───────────────────────────────────────────────
bot = commands.Bot(
    command_prefix=CFG.get("prefix", "="),
    intents=intents,
    help_command=None
)
bot.CFG = CFG

# ───────────────────────────────────────────────
# 🧩 Cogs
# ───────────────────────────────────────────────
EXTS = [
    "cogs.errors",
    "cogs.style",
    "cogs.payments",
    "cogs.moderation",
    "cogs.admin",
    "cogs.utility",
    "cogs.help",
    "cogs.tags",
    "cogs.roleaccess",
    "cogs.welcome",
]

# ───────────────────────────────────────────────
# 🧱 Role helpers
# ───────────────────────────────────────────────
def _has_role(member: discord.Member, role_id):
    if not role_id:
        return False
    try:
        rid = int(role_id)
    except Exception:
        return False
    return any(r.id == rid for r in getattr(member, "roles", []) or [])

def is_admin(member: discord.Member) -> bool:
    if getattr(member, "guild_permissions", None) and member.guild_permissions.administrator:
        return True
    return _has_role(member, bot.CFG["roles"].get("ADMIN_ROLE_ID"))

def is_mod(member: discord.Member) -> bool:
    return is_admin(member) or _has_role(member, bot.CFG["roles"].get("MOD_ROLE_ID"))

# ───────────────────────────────────────────────
# 🚪 Global command gate
# ───────────────────────────────────────────────
@bot.check
async def global_gate(ctx):
    if ctx.guild is None:
        return ctx.command and ctx.command.name in ["help", "ping"]

    name = ctx.command.name if ctx.command else ""
    if name in ["help", "ping", "si", "convert"]:
        return True

    # Moderator commands
    if name in [
        "ltc", "mute", "unmute", "notify", "snipe", "editsnipe", "pm",
        "early", "inv", "purge", "echo", "warn", "dewarn", "warns",
        "clearwarns", "tagc", "tag", "taglist", "add", "remove", "rename",
        "rm", "invites", "bal", "tx",
    ]:
        return is_mod(ctx.author)

    # Everything else = Admin only
    return is_admin(ctx.author)

# ───────────────────────────────────────────────
# ⚙️ Load all cogs
# ───────────────────────────────────────────────
async def load_all():
    for e in EXTS:
        try:
            result = bot.load_extension(e)
            if inspect.isawaitable(result):
                await result
            print(f"[OK] Loaded {e}")
        except Exception as ex:
            print(f"[FAIL] {e}: {ex}")
            traceback.print_exc()

# ───────────────────────────────────────────────
# 🧹 Periodic cleanup loop
# ───────────────────────────────────────────────
async def nuke_loop():
    await bot.wait_until_ready()
    channel_id = bot.CFG.get("chat_channel_id")
    if not channel_id:
        return
    try:
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        logging.getLogger(__name__).warning("Invalid chat_channel_id in config.json")
        return

    interval = int(bot.CFG.get("chat_cleanup_seconds", 6 * 60 * 60))
    while not bot.is_closed():
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                total_deleted = 0
                while True:
                    deleted = await channel.purge(limit=100, bulk=True)
                    total_deleted += len(deleted)
                    if not deleted:
                        break
                    await asyncio.sleep(1)
                embed_color = bot.CFG.get("theme", {}).get("accent_int", 0x87CEEB)
                embed = discord.Embed(
                    description=f"**Chat Successfully Deleted**\nDeleted Messages: `{total_deleted}`",
                    color=discord.Color(embed_color),
                )
                await channel.send(embed=embed)
            except Exception as exc:
                logging.getLogger(__name__).warning("Failed to purge chat channel: %s", exc)
        await asyncio.sleep(interval)

# ───────────────────────────────────────────────
# ⚡ On Connect (load cogs here for Pycord)
# ───────────────────────────────────────────────
@bot.event
async def on_connect():
    await load_all()
    print("✅ All cogs successfully loaded!")

# ───────────────────────────────────────────────
# 🟢 On Ready
# ───────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    status_text = bot.CFG.get("status_text") or f"{bot.CFG.get('brand')} — type {bot.CFG.get('prefix')}help"
    await bot.change_presence(activity=discord.Game(name=status_text))

    if not getattr(bot, "_nuke_task", None):
        bot._nuke_task = asyncio.create_task(nuke_loop())

# ───────────────────────────────────────────────
# 🚀 Main entry point
# ───────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(CFG["token"])
