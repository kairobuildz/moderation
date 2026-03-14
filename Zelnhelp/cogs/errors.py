import traceback, json, os
import discord
from discord.ext import commands
from .style import card, send_permission_denied
CFG = json.load(open(os.path.join(os.path.dirname(__file__),"..","config.json"),"r",encoding="utf-8"))
class ErrorHandler(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound): return
        if isinstance(error, commands.CheckFailure):
            await send_permission_denied(ctx)
            return
        await ctx.send(view=card("Error", f"```\n{error}\n```").to_view())
        ch_id = int(CFG["logging"].get("error_channel_id",0)) or None
        if ch_id and ctx.guild:
            ch = ctx.guild.get_channel(ch_id)
            if ch and ch.permissions_for(ctx.guild.me).send_messages:
                tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))[-1500:]
                await ch.send(view=card("Error Trace", f"```py\n{tb}\n```").to_view())
def setup(bot):
    bot.add_cog(ErrorHandler(bot))
