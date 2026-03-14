import re, discord, time, asyncio, datetime
from discord.ext import commands
from .style import card, FlexibleMember, maybe_delete_invocation, CFG, send_log

# Allow digits, whitespace, + - * / ( ) . %
SAFE = re.compile(r"^[0-9\s+\-*/().%]+$")

_last_deleted: dict[int, tuple[int, str, int]] = {}
_last_edited: dict[int, tuple[int, str, str, int]] = {}

class Utility(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.content:
            return
        _last_deleted[message.channel.id] = (message.author.id, message.content, int(time.time()))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return
        _last_edited[before.channel.id] = (
            before.author.id,
            before.content or "",
            after.content or "",
            int(time.time()),
        )

    # ✅ FIXED: no maybe_delete_invocation here
    @commands.command(name="snipe")
    async def snipe(self, ctx: commands.Context):
        """Shows the last deleted message in the channel."""
        item = _last_deleted.get(ctx.channel.id)
        if not item:
            await ctx.send(view=card("Snipe", "_Nothing to snipe._").to_view())
            return

        author_id, content, ts = item
        payload = card(
            "Last Deleted Message",
            f"**Author:** <@{author_id}>\n**When:** <t:{ts}:R>\n\n{content}",
        ).with_color(discord.Color.blurple())
        await ctx.send(view=payload.to_view())

    # ✅ FIXED: no maybe_delete_invocation here either
    @commands.command(name="editsnipe")
    async def editsnipe(self, ctx: commands.Context):
        """Shows the last edited message in the channel."""
        item = _last_edited.get(ctx.channel.id)
        if not item:
            await ctx.send(view=card("Edit Snipe", "_Nothing to snipe._").to_view())
            return

        author_id, before, after, ts = item
        payload = card(
            "Last Edited Message",
            f"**Author:** <@{author_id}>\n**When:** <t:{ts}:R>\n\n**Before:**\n{before}\n\n**After:**\n{after}",
        ).with_color(discord.Color.blurple())
        await ctx.send(view=payload.to_view())

    @commands.command(name="whois", aliases=["wi"])
    async def whois(self, ctx: commands.Context, user: FlexibleMember | None = None):
        await maybe_delete_invocation(ctx)
        user = user or ctx.author
        joined = f"<t:{int(user.joined_at.timestamp())}:F>" if user.joined_at else "N/A"
        created = f"<t:{int(user.created_at.timestamp())}:F>"
        roles_sorted = sorted(
            [r for r in user.roles if r != ctx.guild.default_role],
            key=lambda r: r.position,
            reverse=True,
        )
        role_lines = "\n".join(r.mention for r in roles_sorted) or "_No roles_"
        avatar_link = user.display_avatar.with_static_format("png").url
        payload = card(
            f"User Info — {user}",
            f"**ID:** `{user.id}`\n**Joined:** {joined}\n**Created:** {created}\n**Roles:**\n{role_lines}\n\n[View Avatar]({avatar_link})",
        )
        await ctx.send(view=payload.to_view())

    @commands.command(name="userinfo")
    async def userinfo(self, ctx: commands.Context, user: FlexibleMember | None = None):
        """Expanded whois with moderation history."""
        await maybe_delete_invocation(ctx)
        user = user or ctx.author
        joined = f"<t:{int(user.joined_at.timestamp())}:F>" if user.joined_at else "N/A"
        created = f"<t:{int(user.created_at.timestamp())}:F>"
        roles_sorted = sorted(
            [r for r in user.roles if r != ctx.guild.default_role],
            key=lambda r: r.position,
            reverse=True,
        )
        role_lines = "\n".join(r.mention for r in roles_sorted) or "_No roles_"

        warnings = getattr(self.bot, f"warnings_{user.id}", [])
        warn_count = len(warnings)
        last_warn = warnings[-1] if warnings else None

        def _fmt_warn_ts(raw):
            if isinstance(raw, int):
                return f"<t:{raw}:R>"
            if isinstance(raw, str):
                try:
                    ts = int(datetime.datetime.fromisoformat(raw).timestamp())
                    return f"<t:{ts}:R>"
                except Exception:
                    return "Unknown"
            return "Unknown"

        warn_line = "Warnings: None"
        if warn_count:
            ts_text = _fmt_warn_ts(last_warn.get("timestamp"))
            warn_line = f"Warnings: {warn_count} (last: {last_warn.get('reason', 'N/A')} • {ts_text})"

        avatar_link = user.display_avatar.with_static_format("png").url
        desc = (
            f"**User Info — {user}**\n"
            f"ID: `{user.id}`\n"
            f"Joined: {joined}\n"
            f"Created: {created}\n"
            f"Roles:\n{role_lines}\n\n"
            f"{warn_line}\n"
            f"[View Avatar]({avatar_link})"
        )
        await ctx.send(view=card("", desc).to_view())

    @commands.command(name="si", aliases=["serverinfo"])
    async def si(self, ctx: commands.Context):
        await maybe_delete_invocation(ctx)
        g = ctx.guild
        humans = len([m for m in g.members if not m.bot]) if g else 0
        bots = len([m for m in g.members if m.bot]) if g else 0
        active = len([m for m in g.members if m.status != discord.Status.offline]) if g else 0
        text_channels = len([c for c in g.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len([c for c in g.channels if isinstance(c, discord.VoiceChannel)])
        categories = len([c for c in g.channels if isinstance(c, discord.CategoryChannel)])
        created_ts = int(g.created_at.timestamp()) if g else 0
        accent = CFG.get("theme", {}).get("accent_int", 0x87CEEB)
        roles_sorted = [
            r for r in sorted(g.roles, key=lambda r: r.position, reverse=True)
            if r != g.default_role
        ]
        role_preview = "\n".join(r.mention for r in roles_sorted[:8]) or "_No roles_"
        if len(roles_sorted) > 8:
            role_preview += f"\n…plus {len(roles_sorted) - 8} more"

        embed = discord.Embed(
            description=(
                f"**{g.name} — Server Info**\n"
                f"Owner: {g.owner.mention if g.owner else 'N/A'}\n"
                f"Created: <t:{created_ts}:F> (<t:{created_ts}:R>)\n"
                f"ID: `{g.id}`"
            ),
            color=discord.Color(accent),
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        if g.banner:
            embed.set_image(url=g.banner.url)

        embed.add_field(
            name="Members",
            value=f"Total: **{g.member_count}**\nHumans: **{humans}** • Bots: **{bots}**\nActive Now: **{active}**",
            inline=False,
        )
        embed.add_field(
            name="Channels",
            value=f"Text: **{text_channels}** • Voice: **{voice_channels}**\nCategories: **{categories}**",
            inline=True,
        )
        embed.add_field(
            name="Boosts",
            value=f"Level **{g.premium_tier}**\nBoosts: **{g.premium_subscription_count or 0}**",
            inline=True,
        )
        embed.add_field(
            name="Security",
            value=f"Verification: **{g.verification_level.name.title()}**\n2FA for Mods: **{'On' if g.mfa_level else 'Off'}**",
            inline=True,
        )
        embed.add_field(
            name="Roles (highest first)",
            value=role_preview,
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(name="calc")
    async def calc(self, ctx: commands.Context, *, expr: str):
        await maybe_delete_invocation(ctx)
        if not SAFE.fullmatch(expr):
            await ctx.send(view=card("Calc", "Invalid expression.").to_view())
            return
        try:
            res = eval(expr, {"__builtins__": {}}, {})
        except Exception:
            await ctx.send(view=card("Calc", "Error evaluating expression.").to_view())
            return
        await ctx.send(view=card("Calc", f"`{expr}` = **{res}**").to_view())

    @commands.command(name="convert")
    async def convert(self, ctx: commands.Context, amount: float, c1: str, c2: str):
        await maybe_delete_invocation(ctx)
        conversions = {
            "usd": {"eur": 0.85, "gbp": 0.73, "jpy": 110.0},
            "eur": {"usd": 1.18, "gbp": 0.86, "jpy": 129.0},
            "gbp": {"usd": 1.37, "eur": 1.16, "jpy": 150.0},
        }

        c1_lower, c2_lower = c1.lower(), c2.lower()

        if c1_lower in conversions and c2_lower in conversions[c1_lower]:
            rate = conversions[c1_lower][c2_lower]
            result = amount * rate
            await ctx.send(
                view=card(
                    "Currency Conversion",
                    f"**{amount} {c1.upper()}** = **{result:.2f} {c2.upper()}**\n\n*Note: This is a simplified conversion.*",
                ).to_view()
            )
        else:
            await ctx.send(
                view=card(
                    "Currency Conversion",
                    f"Conversion from {c1.upper()} to {c2.upper()} not supported.\n\nSupported: USD, EUR, GBP, JPY",
                ).to_view()
            )

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        await maybe_delete_invocation(ctx)
        await ctx.send(view=card("Pong!", f"Latency: `{round(self.bot.latency*1000)}ms`").to_view())

    @commands.command(name="rm")
    async def rm(self, ctx: commands.Context, time_str: str, *, message: str = "Check the channel as soon as possible"):
        await maybe_delete_invocation(ctx)
        import re
        time_pattern = re.compile(r"^(\d+)([smhd])$")
        match = time_pattern.match(time_str.lower())

        if not match:
            await ctx.send(
                view=card(
                    "Invalid Time Format",
                    "Please use format: `10m`, `1h`, `2d`\n\nExamples:\n• `=rm 10m Check the channel`\n• `=rm 1h Important meeting`\n• `=rm 2d Weekly report`",
                ).to_view()
            )
            return

        amount, unit = int(match.group(1)), match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        seconds = amount * multipliers[unit]
        await ctx.send(
            view=card(
                "Reminder Set",
                f"**Reminder set for:** {amount}{unit}\n**Message:** {message}\n\nI'll remind you <t:{int(discord.utils.utcnow().timestamp()) + seconds}:R>",
            ).to_view()
        )

        await asyncio.sleep(seconds)
        try:
            reminder_payload = card("⏰ Reminder!", message)
            await ctx.author.send(view=reminder_payload.to_view())
        except:
            await ctx.send(f"{ctx.author.mention} ⏰ **Reminder:** {message}")

    @commands.command(name="invites")
    async def invites(self, ctx: commands.Context):
        await maybe_delete_invocation(ctx)
        try:
            invites = await ctx.guild.invites()
            user_invites = [inv for inv in invites if inv.inviter and inv.inviter.id == ctx.author.id]

            if not user_invites:
                await ctx.send(view=card("Invites", "You haven't created any invites yet.").to_view())
                return

            total_uses = sum(inv.uses for inv in user_invites)
            invite_list = [f"**{inv.code}** — {inv.uses} uses" for inv in user_invites[:5]]
            desc = f"**Total Invites:** {len(user_invites)}\n**Total Uses:** {total_uses}\n\n**Top Invites:**\n" + "\n".join(invite_list)

            if len(user_invites) > 5:
                desc += f"\n\n*Showing top 5 of {len(user_invites)} invites*"

            await ctx.send(view=card("Your Invites", desc).to_view())
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to view invites.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to fetch invite information: {str(e)}").to_view())

    def _get_original_name(self, channel: discord.TextChannel) -> str | None:
        topic = channel.topic or ""
        m = re.search(r"\[orig=([^\]]+)\]", topic)
        return m.group(1) if m else None

    async def _stamp_original_name(self, channel: discord.TextChannel):
        if self._get_original_name(channel):
            return
        try:
            topic = channel.topic or ""
            suffix = f" [orig={channel.name}]"
            await channel.edit(topic=f"{topic}{suffix}".strip())
        except Exception:
            pass

    @commands.command(name="rename", aliases=["rn"])
    async def rename(self, ctx: commands.Context, *, new_name: str | None = None):
        """Rename the current channel, or restore its original name if none is provided."""
        await maybe_delete_invocation(ctx)
        if not ctx.channel.permissions_for(ctx.author).manage_channels:
            await ctx.send(view=card("Permission Error", "You need Manage Channels to rename this.").to_view())
            return
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send(view=card("Rename", "This command only works in text channels.").to_view())
            return

        await self._stamp_original_name(ctx.channel)
        original = self._get_original_name(ctx.channel) or ctx.channel.name
        target_name = (new_name or original).strip()
        if not target_name:
            await ctx.send(view=card("Rename", "Provide a new name or leave blank to restore the original.").to_view())
            return
        if len(target_name) > 100:
            await ctx.send(view=card("Rename", "Channel names must be 100 characters or fewer.").to_view())
            return

        try:
            await ctx.channel.edit(name=target_name, reason=f"Renamed by {ctx.author}")
            await ctx.send(view=card("Renamed", f"Channel renamed to **{target_name}**.").to_view())
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I can't rename this channel.").to_view())
            return
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to rename: {e}").to_view())
            return

        log = card(
            "Log • Rename",
            f"{ctx.author.mention} renamed {ctx.channel.mention} to **{target_name}**.\n"
            f"Original: **{original}**",
        ).with_color(discord.Color.blurple())
        await send_log(self.bot, ctx.guild, log)

def setup(bot):
    bot.add_cog(Utility(bot))
