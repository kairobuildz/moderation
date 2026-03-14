import json
import os
import discord
from discord.ext import commands
from discord.ui import DesignerView, Button, ActionRow, Separator

from .style import CardLayout, card, CFG, maybe_delete_invocation, send_log

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def _supporter_role_id() -> int | None:
    val = (
        CFG.get("supporter_role_id")
        or CFG.get("roles", {}).get("SUPPORTER_ROLE_ID")
        or "1482519383363420340"
    )
    if not val:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _verification_log_id() -> int | None:
    val = CFG.get("verification_log_channel_id") or "1445436207126417438"
    if not val:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _is_staff(member: discord.Member | None) -> bool:
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True

    roles_cfg = CFG.get("roles", {})
    mod_id = roles_cfg.get("MOD_ROLE_ID")
    admin_id = roles_cfg.get("ADMIN_ROLE_ID")
    verifier_id = "1446630188078207036"

    for candidate in (admin_id, mod_id, verifier_id):
        if not candidate:
            continue
        try:
            rid = int(candidate)
        except (TypeError, ValueError):
            continue
        if any(r.id == rid for r in member.roles):
            return True
    return False


def _is_admin(member: discord.Member | None) -> bool:
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    admin_id = CFG.get("roles", {}).get("ADMIN_ROLE_ID") or "1446629173400440852"
    try:
        rid = int(admin_id)
    except (TypeError, ValueError):
        return False
    return any(r.id == rid for r in member.roles)


def _write_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(CFG, f, indent=2)


def _brand_name() -> str:
    return CFG.get("brand", "Kairo's Studios")


class VerificationView(DesignerView):
    def __init__(self, cog: "RoleAccess", target_user_id: int | None = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.target_user_id = target_user_id

        # Create buttons manually and add via ActionRow
        yes_button = Button(label="Yes", style=discord.ButtonStyle.success, custom_id="roleaccess.verify_yes")
        no_button = Button(label="No", style=discord.ButtonStyle.danger, custom_id="roleaccess.verify_no")

        yes_button.callback = self.yes_button
        no_button.callback = self.no_button

        self.add_item(ActionRow(yes_button, no_button))

    def _resolve_target(self, interaction: discord.Interaction) -> int | None:
        if self.target_user_id:
            return self.target_user_id
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
        if embed and embed.description:
            for part in embed.description.splitlines():
                if "`" in part:
                    segment = part.split("`")
                    for token in segment:
                        token = token.strip()
                        if token.isdigit():
                            try:
                                return int(token)
                            except ValueError:
                                continue
        return None

    async def yes_button(self, interaction: discord.Interaction):
        target_id = self._resolve_target(interaction)
        if not _is_staff(interaction.user):
            await interaction.response.send_message("You are not allowed to verify this request.", ephemeral=True)
            return
        if not interaction.guild or not target_id:
            await interaction.response.send_message("Guild or member not found.", ephemeral=True)
            return

        member = interaction.guild.get_member(target_id)
        if not member:
            await interaction.response.send_message("User is no longer in the server.", ephemeral=True)
            await interaction.message.edit(view=None)
            return

        role = self.cog.get_supporter_role(interaction.guild)
        if not role:
            await interaction.response.send_message("Supporter role is not configured.", ephemeral=True)
            return

        if role in member.roles:
            await interaction.response.send_message(f"{member.mention} already has the role.", ephemeral=True)
            await interaction.message.edit(view=None)
            return

        await member.add_roles(role, reason="Supporter role approved")
        try:
            brand = _brand_name()
            await member.send(
                f"Hey {member.mention}! Thanks for supporting {brand}. "
                "We've awarded you the **Supporter** role."
            )
        except Exception:
            pass

        await interaction.message.edit(view=None)
        await interaction.response.send_message(f"✅ Verified! {member.mention} received {role.mention}.", ephemeral=True)

        log = card(
            "Log • Supporter Verified",
            f"**User:** {member.mention} (`{member.id}`)\n"
            f"**Staff:** {interaction.user.mention}\n"
            f"**Role:** {role.mention}",
        ).with_color(discord.Color.blue())
        await send_log(self.cog.bot, interaction.guild, log)

    async def no_button(self, interaction: discord.Interaction):
        target_id = self._resolve_target(interaction)
        if not _is_staff(interaction.user):
            await interaction.response.send_message("You are not allowed to decline this request.", ephemeral=True)
            return
        if not interaction.guild or not target_id:
            await interaction.response.send_message("Guild or member not found.", ephemeral=True)
            return

        member = interaction.guild.get_member(target_id)
        panel_link = CFG.get("panel_message_link", "the supporter panel")

        if member:
            try:
                await member.send(
                    "Hey! We checked your supporter request but couldn't confirm `.gg/vanityhere` "
                    f"in your status or bio. Please review {panel_link} and try again once you meet the requirements."
                )
            except Exception:
                pass

        await interaction.message.edit(view=None)
        await interaction.response.send_message("<:no:1446871285438349354> Request denied.", ephemeral=True)

        log = card(
            "Log • Supporter Denied",
            f"**User:** {member.mention if member else target_id}\n"
            f"**Staff:** {interaction.user.mention}\n"
            "Request denied.",
        ).with_color(discord.Color.red())
        await send_log(self.cog.bot, interaction.guild, log)


class ClaimRoleView(DesignerView):
    def __init__(
        self,
        cog: "RoleAccess",
        payload: CardLayout | None = None,
        early_supporter: CardLayout | None = None,
    ):
        super().__init__(timeout=None)
        self.cog = cog
        if payload:
            self.add_item(payload.to_container())

        if payload and early_supporter:
            self.add_item(Separator())

        if early_supporter:
            self.add_item(early_supporter.to_container())

        # Claim button
        claim_button = Button(label="Claim Supporter", style=discord.ButtonStyle.primary, custom_id="roleaccess.claim")
        claim_button.callback = self.claim_role
        open_ticket = Button(
            label="Open a Ticket",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/1446626338726482122/1446627706220318731",
        )
        self.add_item(ActionRow(claim_button, open_ticket))

    async def claim_role(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This button only works in a server.", ephemeral=True)
            return

        log_channel = self.cog.get_verification_channel(interaction.guild)
        if not log_channel:
            await interaction.response.send_message("Verification channel is not configured.", ephemeral=True)
            return

        embed = discord.Embed(
            description=(
                "**Supporter Role Request**\n"
                f"**User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"**Username:** {interaction.user}\n\n"
                "Please ensure their status or bio contains `.gg/vanity`."
            ),
            color=discord.Color.blue(),
        )

        view = VerificationView(self.cog, interaction.user.id)
        await log_channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            "Your request has been submitted! Please wait for verification.",
            ephemeral=True,
        )


class RoleAccess(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_supporter_role(self, guild: discord.Guild | None) -> discord.Role | None:
        if not guild:
            return None
        role_id = _supporter_role_id()
        return guild.get_role(role_id) if role_id else None

    def get_verification_channel(self, guild: discord.Guild | None) -> discord.TextChannel | None:
        if not guild:
            return None
        channel_id = _verification_log_id()
        if not channel_id:
            return None
        return guild.get_channel(channel_id) or self.bot.get_channel(channel_id)

    @commands.command(name="roleaccess", aliases=["roleacces"])
    async def roleacces(self, ctx: commands.Context):
        if not _is_admin(ctx.author):
            await ctx.send("Only admins can post the supporter panel.")
            return
        await maybe_delete_invocation(ctx)

        supporter_role_id = _supporter_role_id() or CFG.get("roles", {}).get("SUPPORTER_ROLE_ID") or ""
        supporter_card = CardLayout(
            "Role Access — Supporters",
            (
                f"**Supporter Role:** <@&{1482519383363420340}>\n"
                "Add `.gg/vanity` to your status or bio, then press **Claim Supporter**.\n"
                "Our team quickly verifies it — the badge stays forever and helps Kairo''s Studios grow.\n"
                "Questions? Ping any staff member and we'll sort it out."
            ),
            footer=None,
        ).with_color(discord.Color.blue())

        early_card = CardLayout(
            "How to Claim Early Supporter",
            (
                f"**Role:** <@&1482518292672544885>\n\n"
                "Kairo's's Slots is growing every day, and we’re excited to open up a way for our community members to support the project directly. "
                "If you enjoy what we’re building and want to help us improve even more, you can now donate a minimum of €1 (or more) to show your support!\n\n"
                "All donors will receive the Early Supporter role — a special badge of appreciation that shows you were among the very first to support Kairo''s Studios journey. "
                "This role may come with special perks in the future, and it’s a permanent mark of your contribution to the server.\n\n"
                "<:dolar:1446871271584567446> **How to donate:** Click **Open a Ticket** below and our team will help you complete the process and confirm your Early Supporter role."
            ),
            footer=None,
        ).with_color(discord.Color.blue())

        view = ClaimRoleView(self, supporter_card, early_card)
        message = await ctx.send(view=view)

        CFG["panel_message_link"] = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{message.id}"
        _write_config()

        log = card(
            "Log • Supporter Panel Posted",
            f"{ctx.author.mention} posted a supporter panel in {ctx.channel.mention}.",
        ).with_color(discord.Color.blue())
        await send_log(self.bot, ctx.guild, log)


def setup(bot: commands.Bot):
    cog = RoleAccess(bot)
    bot.add_cog(cog)
    bot.add_view(ClaimRoleView(cog))
    bot.add_view(VerificationView(cog))
