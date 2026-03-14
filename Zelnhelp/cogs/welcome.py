from datetime import datetime, timezone
import discord
from discord.ext import commands

from .style import card, CFG, send_log


def _channel_by_id(bot: commands.Bot, guild: discord.Guild | None, key: str) -> discord.TextChannel | None:
    if not guild:
        return None
    channel_id = CFG.get(key)
    if not channel_id:
        return None
    try:
        cid = int(channel_id)
    except (TypeError, ValueError):
        return None
    return guild.get_channel(cid) or bot.get_channel(cid)


def _human_timedelta(start: datetime, end: datetime) -> str:
    diff = end - start
    days = diff.days
    if days >= 365:
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    if days >= 30:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''} ago"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return "Just now"


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invite_cache: dict[int, dict[str, int]] = {}
        self.inviter_lookup: dict[int, int | None] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
            except Exception:
                self.invite_cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        brand = CFG.get("brand", "Zelune's Slots")
        channel = _channel_by_id(self.bot, member.guild, "welcome_channel_id")
        if not channel:
            return

        account_age = _human_timedelta(member.created_at, datetime.now(timezone.utc))

        inviter_text = "Unknown"
        total_invites_text = "Unknown"
        try:
            previous = self.invite_cache.get(member.guild.id, {})
            invites = await member.guild.invites()
            used_invite = None
            for inv in invites:
                if inv.uses > previous.get(inv.code, 0):
                    used_invite = inv
                    break
            self.invite_cache[member.guild.id] = {inv.code: inv.uses for inv in invites}

            if used_invite and used_invite.inviter:
                inviter_text = used_invite.inviter.mention
                total_invites_text = f"{used_invite.inviter.mention} — **{used_invite.uses}** invites"
                self.inviter_lookup[member.id] = used_invite.inviter.id
            else:
                self.inviter_lookup[member.id] = None
        except Exception:
            pass

        embed = discord.Embed(color=discord.Color(0x87CEEB))
        embed.description = f"**Welcome to {brand}**\n{member.mention} just joined — make them feel welcome!"
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Invited By", value=inviter_text, inline=True)
        embed.add_field(name="Total Invites", value=total_invites_text, inline=True)
        embed.add_field(name="Account Age", value=account_age, inline=True)
        embed.add_field(
            name="Member Number",
            value=f"#{member.guild.member_count}",
            inline=True,
        )
        embed.add_field(
            name="Getting Started",
            value="Say hi in chat and add `.gg/zlnsmp` to grab your supporter badge!",
            inline=False,
        )

        await channel.send(f"{member.mention}", embed=embed)

        log = card(
            "Log • Member Joined",
            f"{member.mention} joined. Account created {account_age}.",
        ).with_color(discord.Color(0x87CEEB))
        await send_log(self.bot, member.guild, log)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        brand = CFG.get("brand", "Zelune's Slots")
        channel = _channel_by_id(self.bot, member.guild, "leave_channel_id")
        if not channel:
            return

        joined_at = member.joined_at or datetime.now(timezone.utc)
        time_in_server = _human_timedelta(joined_at, datetime.now(timezone.utc))
        inviter_id = self.inviter_lookup.pop(member.id, None)
        inviter_text = f"<@{inviter_id}>" if inviter_id else "Unknown"

        embed = discord.Embed(color=discord.Color(0x87CEEB))
        embed.add_field(
            name="\u200b",
            value=(
                f"**Goodbye from {brand}**\n"
                f"• **User:** {member.mention} (`{member.id}`)\n"
                f"• **Original Invited By:** {inviter_text}\n"
                f"• **Time in Server:** {time_in_server}\n"
                f"• **Member Count:** {brand} now has **{member.guild.member_count}** members"
            ),
            inline=False,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

        log = card(
            "Log • Member Left",
            f"{member.mention} left after {time_in_server}.",
        ).with_color(discord.Color(0x87CEEB))
        await send_log(self.bot, member.guild, log)


def setup(bot: commands.Bot):
    bot.add_cog(Welcome(bot))
