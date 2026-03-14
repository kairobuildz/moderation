import re, datetime, discord, os, json
from discord.ext import commands
from .style import card, CFG, FlexibleMember, maybe_delete_invocation, send_log, has_role

BLOCKLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "storage", "blocked_words.json")
DEFAULT_BLOCKED = [
    "boosts", "paypal", "bank", "docs", "documents", "stake", "server", "sex",
    "porn", "gamble", "nitro", "nb", "nitro boost", "nigger", "nga", "nega",
    "gay", "vpn", "fuck", "bitch", "deco", "server boosts", "tokens",
]

DUR_RX = re.compile(r"^(\d+)([smhd])$")
def parse_duration(s: str) -> int | None:
    m = DUR_RX.match(s.lower().strip())
    if not m: return None
    n, u = int(m.group(1)), m.group(2)
    mult = {'s':1,'m':60,'h':3600,'d':86400}[u]
    return n*mult


def describe_duration(raw: str) -> str:
    """Turn 10m/2h/etc into a friendly phrase."""
    m = DUR_RX.match(raw.lower().strip())
    if not m:
        return raw
    value, unit = int(m.group(1)), m.group(2)
    names = {'s': 'second', 'm': 'minute', 'h': 'hour', 'd': 'day'}
    base = names.get(unit, "second")
    if value != 1:
        base += "s"
    return f"{value} {base}"

def load_blocklist() -> set[str]:
    if os.path.exists(BLOCKLIST_FILE):
        try:
            with open(BLOCKLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(w.lower() for w in data if isinstance(w, str))
        except Exception:
            pass
    return set(DEFAULT_BLOCKED)

def save_blocklist(words: set[str]) -> None:
    os.makedirs(os.path.dirname(BLOCKLIST_FILE), exist_ok=True)
    with open(BLOCKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(words), f, indent=2, ensure_ascii=False)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_warn_lookup: dict[int, int] = {}
        self._protected_role_id = str(CFG.get("roles", {}).get("MOD_ROLE_ID") or "1446630188078207036")
        self.blocked_words: set[str] = load_blocklist()

    def _is_protected(self, member: discord.Member | None) -> bool:
        return has_role(member, self._protected_role_id)

    async def _deny_if_peer_protected(self, ctx: commands.Context, target: discord.Member, action: str) -> bool:
        """Block peer moderation between members sharing the protected role."""
        if self._is_protected(ctx.author) and self._is_protected(target):
            await ctx.send(view=card("Action Blocked", f"You cannot {action} someone with the same staff role.").to_view())
            return True
        return False

    def _is_filter_immune(self, member: discord.Member | None) -> bool:
        if not member:
            return False
        if getattr(member, "bot", False):
            return True
        if getattr(member, "guild_permissions", None) and member.guild_permissions.administrator:
            return True
        return self._is_protected(member)

    def _dm_enabled(self) -> bool:
        return CFG.get("features", {}).get("dm_on_warn", True)

    async def _send_warn_dm(self, user: discord.Member, title: str, description: str):
        if not self._dm_enabled():
            return
        try:
            payload = card("", f"**{title}**\n{description}")
            await user.send(embed=payload.to_embed())
        except Exception:
            pass

    def _get_role(self, guild: discord.Guild | None, key: str) -> discord.Role | None:
        if not guild:
            return None
        rid = CFG.get("roles", {}).get(key)
        if not rid:
            return None
        try:
            return guild.get_role(int(rid))
        except (TypeError, ValueError):
            return None

    @commands.command(name="mute")
    async def mute(self, ctx: commands.Context, user: FlexibleMember, duration: str, *, reason: str = "No reason provided"):
        await maybe_delete_invocation(ctx)
        secs = parse_duration(duration)
        if not secs:
            await ctx.send(view=card("", "Duration must be like `10m`, `1h`, `2d`.").to_view())
            return
        if await self._deny_if_peer_protected(ctx, user, "mute"):
            return
        until = discord.utils.utcnow() + datetime.timedelta(seconds=secs)
        try:
            await user.timeout(until, reason=reason)
        except AttributeError:
            await user.edit(timed_out_until=until, reason=reason)
        mute_role = self._get_role(ctx.guild, "MUTE_ROLE_ID")
        if mute_role and mute_role not in user.roles:
            try:
                await user.add_roles(mute_role, reason=f"Muted by {ctx.author}: {reason}")
            except Exception:
                pass

        nice_duration = describe_duration(duration)
        try:
            dm_payload = card(
                "",
                f"You have been muted in **{ctx.guild.name if ctx.guild else 'this server'}**.\n"
                f"Duration: **{nice_duration}**\n"
                f"Reason: {reason}",
            )
            await user.send(embed=dm_payload.to_embed())
        except Exception:
            pass

        payload = card("", f"{user.mention}\nDuration: **{nice_duration}**\nReason: {reason}")
        await ctx.send(view=payload.to_view())

        log = card(
            "Log • Mute",
            f"Staff: {ctx.author.mention}\n"
            f"User: {user.mention} (`{user.id}`)\n"
            f"Reason: {reason}\n"
            f"Duration: {duration} ({nice_duration})\n"
            "Units: s/S=Seconds • m/M=Minutes • h/H=Hours • d/D=Days",
        ).with_color(discord.Color.red())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="unmute")
    async def unmute(self, ctx: commands.Context, user: FlexibleMember):
        await maybe_delete_invocation(ctx)
        try:
            await user.timeout(None, reason="Unmute")
        except Exception:
            await user.edit(timed_out_until=None, reason="Unmute")
        mute_role = self._get_role(ctx.guild, "MUTE_ROLE_ID")
        if mute_role and mute_role in user.roles:
            try:
                await user.remove_roles(mute_role, reason=f"Unmuted by {ctx.author}")
            except Exception:
                pass

        try:
            dm_payload = card(
                "",
                f"You have been unmuted in **{ctx.guild.name if ctx.guild else 'this server'}**.",
            )
            await user.send(embed=dm_payload.to_embed())
        except Exception:
            pass

        payload = card("", f"{user.mention} has been unmuted.")
        await ctx.send(view=payload.to_view())

        log = card(
            "Log • Unmute",
            f"Staff: {ctx.author.mention}\n"
            f"User: {user.mention} (`{user.id}`)",
        ).with_color(discord.Color.green())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="warn")
    async def warn(self, ctx: commands.Context, user: FlexibleMember, *, reason: str = "No reason provided"):
        """Issue a warning to a user."""
        await maybe_delete_invocation(ctx)
        if await self._deny_if_peer_protected(ctx, user, "warn"):
            return
        
        # Store warning in a simple way (you can implement proper database storage later)
        warning_key = f"warnings_{user.id}"
        if not hasattr(self.bot, warning_key):
            setattr(self.bot, warning_key, [])
        
        warnings = getattr(self.bot, warning_key)
        warnings.append({
            "reason": reason,
            "moderator": ctx.author.id,
            "timestamp": int(discord.utils.utcnow().timestamp())
        })

        await ctx.send(view=card("Warning Issued", f"**{user.mention}** has been warned.\n**Reason:** {reason}\n**Total Warnings:** {len(warnings)}").to_view())

        await self._send_warn_dm(
            user,
            "You received a warning",
            f"**Server:** {ctx.guild.name if ctx.guild else 'Unknown'}\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}\n**Total warnings:** {len(warnings)}",
        )

        log = card(
            "Log • Warn",
            f"{ctx.author.mention} warned {user.mention}.\n"
            f"**User:** {user.mention} (`{user.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Total Warnings:** {len(warnings)}",
        ).with_color(discord.Color.yellow())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="warns")
    async def warns(self, ctx: commands.Context, user: FlexibleMember = None):
        """View all warnings for a user."""
        await maybe_delete_invocation(ctx)
        user = user or ctx.author
        
        warning_key = f"warnings_{user.id}"
        if not hasattr(self.bot, warning_key):
            await ctx.send(view=card("No Warnings", f"{user.mention} has no warnings.").to_view())
            return

        warnings = getattr(self.bot, warning_key)
        if not warnings:
            await ctx.send(view=card("No Warnings", f"{user.mention} has no warnings.").to_view())
            return
        
        warning_list = []
        for i, warning in enumerate(warnings, 1):
            mod = ctx.guild.get_member(warning["moderator"])
            mod_name = mod.mention if mod else f"<@{warning['moderator']}>"
            timestamp = warning.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = int(datetime.datetime.fromisoformat(timestamp).timestamp())
                except Exception:
                    timestamp = None
            ts_text = f"<t:{timestamp}:R>" if isinstance(timestamp, int) else "Unknown time"
            warning_list.append(f"**{i}.** {warning['reason']}\n> By {mod_name} • {ts_text}")

        desc = f"**Warnings for {user.display_name}**\n\n" + "\n\n".join(warning_list)
        await ctx.send(view=card("", desc, color=discord.Color(0xFF8A00)).to_view())
        self._last_warn_lookup[ctx.author.id] = user.id

    @commands.command(name="dewarn")
    async def dewarn(self, ctx: commands.Context, *args: str):
        """Remove a specific warning. Usage: =dewarn <index> [user]"""
        await maybe_delete_invocation(ctx)

        if not args:
            await ctx.send(view=card("Warn Removal", "Provide the warning number to remove.\nUsage: `=dewarn <index> [member]`").to_view())
            return

        member: discord.Member | None = None
        index: int | None = None
        converter = FlexibleMember()
        for arg in args:
            if index is None and arg.isdigit():
                index = int(arg)
                continue
            if member is None:
                try:
                    member = await converter.convert(ctx, arg)  # type: ignore[arg-type]
                except commands.BadArgument:
                    if index is None:
                        try:
                            index = int(arg)
                        except ValueError:
                            await ctx.send(view=card("Warn Removal", f"Couldn't understand `{arg}`. Use a user mention or a number.").to_view())
                            return

        if index is None:
            await ctx.send(view=card("Warn Removal", "Please provide which warning number to remove.").to_view())
            return

        if member is None:
            last_target = self._last_warn_lookup.get(ctx.author.id)
            if last_target and ctx.guild:
                member = ctx.guild.get_member(last_target)
        member = member or ctx.author
        if await self._deny_if_peer_protected(ctx, member, "modify warnings for"):
            return

        warning_key = f"warnings_{member.id}"
        warnings = getattr(self.bot, warning_key, None)
        if not warnings:
            await ctx.send(view=card("No Warnings", f"{member.mention} has no warnings.").to_view())
            return

        if index < 1 or index > len(warnings):
            await ctx.send(view=card("Invalid Index", f"Please provide a number between 1 and {len(warnings)}.").to_view())
            return

        removed_warning = warnings.pop(index - 1)
        await ctx.send(view=card("Warning Removed", f"Removed warning #{index} from {member.mention}.\n**Reason was:** {removed_warning['reason']}").to_view())

        await self._send_warn_dm(
            member,
            "A warning was removed",
            f"**Server:** {ctx.guild.name if ctx.guild else 'Unknown'}\n**Removed by:** {ctx.author.mention}\n**Original reason:** {removed_warning['reason']}",
        )

        log = card(
            "Log • Warning Removed",
            f"**User:** {member.mention} (`{member.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Removed Reason:** {removed_warning['reason']}",
        ).with_color(discord.Color.orange())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="clearwarns", aliases=["cleanwarns"])
    async def clearwarns(self, ctx: commands.Context, user: FlexibleMember):
        """Remove all warnings from a user."""
        await maybe_delete_invocation(ctx)
        if await self._deny_if_peer_protected(ctx, user, "clear warnings for"):
            return
        
        warning_key = f"warnings_{user.id}"
        if not hasattr(self.bot, warning_key):
            await ctx.send(view=card("No Warnings", f"{user.mention} has no warnings.").to_view())
            return

        warnings = getattr(self.bot, warning_key)
        if not warnings:
            await ctx.send(view=card("No Warnings", f"{user.mention} has no warnings.").to_view())
            return

        count = len(warnings)
        setattr(self.bot, warning_key, [])

        await ctx.send(view=card("Warnings Cleared", f"Cleared {count} warnings from {user.mention}.").to_view())

        await self._send_warn_dm(
            user,
            "Warnings cleared",
            f"**Server:** {ctx.guild.name if ctx.guild else 'Unknown'}\n**Moderator:** {ctx.author.mention}\n**Removed warnings:** {count}",
        )

        log = card(
            "Log • Warnings Cleared",
            f"**User:** {user.mention} (`{user.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Cleared Count:** {count}",
        ).with_color(discord.Color.orange())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="purge")
    async def purge(self, ctx: commands.Context, amount: int, user: FlexibleMember = None):
        """Delete messages."""
        await maybe_delete_invocation(ctx)
        
        if amount < 1 or amount > 100:
            await ctx.send(view=card("Invalid Amount", "Please provide a number between 1 and 100.").to_view())
            return
        
        try:
            if user:
                # Delete messages from specific user
                deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author == user)
            else:
                # Delete all messages
                deleted = await ctx.channel.purge(limit=amount)
            
            await ctx.send(view=card("Messages Purged", f"Deleted {len(deleted)} message(s).").to_view(), delete_after=5)

            log = card(
                "Log • Purge",
                f"**Channel:** {ctx.channel.mention}\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Deleted:** {len(deleted)} message(s)\n"
                f"**Filter:** {'Only ' + user.mention if user else 'Entire channel'}",
            ).with_color(discord.Color.dark_teal())
            await send_log(self.bot, ctx.guild, log)
            
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to delete messages.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to delete messages: {str(e)}").to_view())

    @commands.command(name="echo")
    async def echo(self, ctx: commands.Context, *, message: str):
        """Echo a message."""
        await maybe_delete_invocation(ctx)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(message)

    @commands.command(name="add")
    async def add_blocked_word(self, ctx: commands.Context, *, word: str | None = None):
        """Add a word to the blocked list."""
        await maybe_delete_invocation(ctx)
        if not word:
            await ctx.send(view=card("Blocked Words", "Provide a word to add. Usage: `=add <word>`").to_view())
            return
        if not self._is_protected(ctx.author) and not ctx.author.guild_permissions.administrator:
            await ctx.send(view=card("Permission Denied", "You need staff permissions to modify blocked words.").to_view())
            return
        normalized = word.strip().lower()
        if not normalized:
            await ctx.send(view=card("Blocked Words", "Provide a valid word to add.").to_view())
            return
        if normalized in self.blocked_words:
            await ctx.send(view=card("Blocked Words", f"`{normalized}` is already blocked.").to_view())
            return
        self.blocked_words.add(normalized)
        save_blocklist(self.blocked_words)
        await ctx.send(view=card("Blocked Words", f"Added `{normalized}` to the blocklist.").to_view())

        log = card(
            "Log • Blocklist Updated",
            f"{ctx.author.mention} added `{normalized}` to the blocked words.",
        ).with_color(discord.Color.blurple())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="remove")
    async def remove_blocked_word(self, ctx: commands.Context, *, word: str | None = None):
        """Remove a word from the blocked list."""
        await maybe_delete_invocation(ctx)
        if not word:
            await ctx.send(view=card("Blocked Words", "Provide a word to remove. Usage: `=remove <word>`").to_view())
            return
        if not self._is_protected(ctx.author) and not ctx.author.guild_permissions.administrator:
            await ctx.send(view=card("Permission Denied", "You need staff permissions to modify blocked words.").to_view())
            return
        normalized = word.strip().lower()
        if normalized not in self.blocked_words:
            await ctx.send(view=card("Blocked Words", f"`{normalized}` is not in the blocklist.").to_view())
            return
        self.blocked_words.remove(normalized)
        save_blocklist(self.blocked_words)
        await ctx.send(view=card("Blocked Words", f"Removed `{normalized}` from the blocklist.").to_view())

        log = card(
            "Log • Blocklist Updated",
            f"{ctx.author.mention} removed `{normalized}` from the blocked words.",
        ).with_color(discord.Color.blurple())
        await send_log(self.bot, ctx.guild, log)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if self._is_filter_immune(message.author):
            return
        content = (message.content or "").lower()
        if not content:
            return

        tripped = None
        for word in self.blocked_words:
            if word and word in content:
                tripped = word
                break
        if not tripped:
            return

        try:
            await message.delete()
            feedback = await message.channel.send(view=card("Blocked", "Your message was removed for containing a blocked word.").to_view())
            await feedback.delete(delay=5)
        except Exception:
            pass

        log = card(
            "Log • Blocked Word",
            f"**User:** {message.author.mention} (`{message.author.id}`)\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Word:** `{tripped}`\n"
            f"**Content:** {message.content[:180]}",
        ).with_color(discord.Color.dark_red())
        await send_log(self.bot, message.guild, log)

def setup(bot):
    bot.add_cog(Moderation(bot))
