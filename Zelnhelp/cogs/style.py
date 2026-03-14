import json
import os
import re
import discord
from discord.ext import commands
from discord.ui import Container, Separator, TextDisplay, View

# === Load Config ===
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

def _color_from_hex(raw: str) -> discord.Color:
    value = (raw or "").strip().lower().replace("0x", "").replace("#", "")
    try:
        return discord.Color(int(value, 16))
    except (ValueError, TypeError):
        return discord.Color(0x87CEEB)


ACCENT = _color_from_hex(CFG["theme"].get("accent_hex", "#87CEEB"))


class CardLayout:
    """Represent a reusable card payload that can render as components or embeds."""

    __slots__ = ("title", "description", "color", "thumbnail", "footer", "timestamp", "as_log")

    def __init__(
        self,
        title: str,
        description: str = "",
        *,
        thumbnail: str | None = None,
        color: discord.Color | None = None,
        footer: str | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.color = color or ACCENT
        self.thumbnail = thumbnail
        self.footer = footer
        self.timestamp = discord.utils.utcnow()
        self.as_log = False

    def __setattr__(self, name, value):
        # Allow legacy assignments like `card(...).color = 0x123456`
        if name == "color":
            if isinstance(value, int):
                value = discord.Color(value)
            elif isinstance(value, str):
                value = _color_from_hex(value)
        super().__setattr__(name, value)

    def with_color(self, color: discord.Color) -> "CardLayout":
        self.color = color
        return self

    def for_log(self) -> "CardLayout":
        """Mark this card as a log so embeds keep their titles."""
        self.as_log = True
        return self

    def _body(self) -> str:
        heading = f"**{self.title}**" if self.title else ""
        if self.as_log:
            return self.description or heading
        if heading and self.description:
            return f"{heading}\n\n{self.description}"
        return heading or self.description

    def to_container(self) -> Container:
        blocks: list[discord.ui.Item] = []

        if self.title and self.as_log:
            blocks.append(TextDisplay(f"### {self.title}"))

        body = self._body()
        if body:
            if blocks:
                blocks.append(Separator())
            blocks.append(TextDisplay(body))

        if self.footer and self.as_log:
            blocks.append(Separator())
            blocks.append(TextDisplay(f"*{self.footer}*"))

        return Container(*blocks, color=self.color)

    def to_view(self, *extra_items: discord.ui.Item, timeout: float | None = None) -> View:
        view_cls = getattr(discord.ui, "DesignerView", View)
        view: View = view_cls(timeout=timeout)
        view.add_item(self.to_container())

        action_row_cls = getattr(discord.ui, "ActionRow", None)
        pending_row = None

        def flush_row():
            nonlocal pending_row
            if pending_row and getattr(pending_row, "children", None):
                view.add_item(pending_row)
            pending_row = None

        for item in extra_items:
            if not item:
                continue

            if isinstance(item, Container):
                if action_row_cls:
                    flush_row()
                view.add_item(item)
                continue

            if action_row_cls and isinstance(item, action_row_cls):
                flush_row()
                view.add_item(item)
                continue

            if action_row_cls:
                if pending_row is None:
                    pending_row = action_row_cls()
                pending_row.add_item(item)
                if len(getattr(pending_row, "children", [])) >= 5:
                    flush_row()
            else:
                view.add_item(item)

        if action_row_cls:
            flush_row()
        return view

    def to_embed(self) -> discord.Embed:
        body = self._body()
        embed = discord.Embed(
            title=self.title if self.as_log else None,
            description=body,
            color=self.color,
        )
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        if self.footer and self.as_log:
            embed.set_footer(text=self.footer)
        embed.timestamp = self.timestamp
        return embed

# === Asset Paths ===
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

SUCCESS_EMOJI = "<:yes:1446871297111097549>"
DENIED_EMOJI = "<:no:1446871285438349354>"
CTA_TICKET = "<:tix:1452022685566505071>"
CTA_BOT = "<:trusted:1446871291817754685>"
CTA_WEB = "<:linkb:1446871276210618418>"


def _lines_to_text(lines: list[str] | str) -> str:
    if isinstance(lines, str):
        return lines
    return "\n".join(line for line in lines if line)


async def send_success(target, lines: list[str] | str, *, auto_delete: bool = False):
    desc = f"**{SUCCESS_EMOJI} Success**\n{_lines_to_text(lines)}"
    view = card("", desc, color=discord.Color.green()).to_view()
    await target.send(view=view, delete_after=15 if auto_delete else None)


async def send_denied(target, reason: str, *, auto_delete: bool = False):
    desc = f"**{DENIED_EMOJI} {reason}**"
    view = card("", desc, color=discord.Color.red()).to_view()
    await target.send(view=view, delete_after=15 if auto_delete else None)


async def send_permission_denied(target, *, auto_delete: bool = True):
    await send_denied(
        target,
        "Hello There! You do not have the required permissions to use this",
        auto_delete=auto_delete,
    )


# === Embed Helper ===
def card(
    title: str,
    desc: str = "",
    *,
    thumbnail: str | None = None,
    color: discord.Color | None = None
) -> CardLayout:
    """Creates a styled card payload for reuse."""
    return CardLayout(title, desc, thumbnail=thumbnail, color=color)


# === Divider Images ===
def blue_divider_file():
    """Returns a blue divider bar image (if exists)."""
    path = os.path.join(ASSETS_DIR, "bar_blue.png")
    if not os.path.exists(path):
        # fallback to orange if blue not found
        path = os.path.join(ASSETS_DIR, "bar_orange.png")
    f = discord.File(path, filename=os.path.basename(path))
    return f, f"attachment://{os.path.basename(path)}"


# Backward compatibility — old code may still import orange_divider_file
def orange_divider_file():
    """Alias for backward compatibility."""
    return blue_divider_file()


# === Invocation Cleanup ===
async def maybe_delete_invocation(ctx: commands.Context):
    """Deletes the invoking message if enabled in config."""
    if CFG.get("features", {}).get("delete_invocation", True):
        try:
            await ctx.message.delete()
        except Exception:
            pass


# === Logging Helper ===
async def send_log(bot: commands.Bot, guild: discord.Guild | None, payload):
    """Send a styled card (or legacy embed) to the configured modlog channel."""
    if not guild:
        return
    modlog_id = CFG.get("logging", {}).get("modlog_channel_id")
    if not modlog_id:
        return
    try:
        channel_id = int(modlog_id)
    except (TypeError, ValueError):
        return

    channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
    if not channel:
        return

    try:
        if isinstance(payload, CardLayout):
            payload.for_log()
            await channel.send(view=payload.to_view())
        else:
            await channel.send(embed=payload)
    except Exception:
        pass


def has_role(member: discord.Member | None, role_id: str | int | None) -> bool:
    """Safely check if a member has a specific role ID."""
    if not member or not role_id:
        return False
    try:
        rid = int(role_id)
    except (TypeError, ValueError):
        return False
    return any(r.id == rid for r in getattr(member, "roles", []) or [])


class FlexibleMember(commands.Converter):
    """Resolve a member by mention, ID, username, or display name."""

    async def convert(self, ctx: commands.Context, argument):
        if isinstance(argument, discord.Member):
            return argument

        lookup = str(argument).strip()
        mention_match = re.match(r"<@!?(\d+)>", lookup)
        if mention_match:
            lookup = mention_match.group(1)

        if lookup.isdigit() and ctx.guild:
            member = ctx.guild.get_member(int(lookup))
            if member:
                return member

        if ctx.guild:
            lower = lookup.lower()
            for member in ctx.guild.members:
                if lower == member.name.lower() or lower == member.display_name.lower():
                    return member
            for member in ctx.guild.members:
                if member.name.lower().startswith(lower) or member.display_name.lower().startswith(lower):
                    return member

        raise commands.BadArgument("Member not found.")


# === Cog Setup Placeholder ===
def setup(bot):
    """Compatibility shim for extension loader."""
    return
