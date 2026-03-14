import discord
from discord.ext import commands
from .style import card, CFG

HELP_SECTIONS = {
    "Utility Commands": [
        "`=whois <user>` — Shows information about a user. (`=wi` shortcut)",
        "`=si` — Displays server information and stats. (`=serverinfo` shortcut)",
        "`=calc <expression>` — Perform calculations (Example: `=calc 10%8`).",
        "`=convert <amount> <currency1> <currency2>` — Convert currency (Example: `=convert 10 usd eur`).",
        "`=rm <time> [message]` — Set a reminder (Example: `=rm 10m Take a break`).",
        "`=bal <address>` — Check Litecoin balance for an address.",
        "`=tx <txID>` — View Litecoin transaction details.",
        "`=snipe` — View the last deleted message in the channel.",
        "`=editsnipe` — View the last edited message in the channel.",
        "`=invites` — Show your invite stats and info.",
        "`=ping` — Check bot latency and response time.",
        "`=userinfo <user>` — Expanded profile with moderation history.",
    ],
    "Mod Commands": [
        "`=pm` — Sends the payment methods embed.",
        "`=ltc <amount in eur>` — Generate a Litecoin payment embed.",
        "`=early [user]` — Grant early supporter role to a user.",
        "`=inv <user>` — Grant merchant role to a user.",
        "`=purge <amount> [user]` — Delete messages, optionally filtering by user.",
        "`=ban <user> [reason]` — Ban a user from the server.",
        "`=unban <user_id|name#tag>` — Unban a user from the server.",
        "`=echo <message>` — Make the bot repeat your message.",
        "`=notify [target] <message>` — Send a DM notification to a user.",
        "`=warn <user> <reason>` — Issue a warning to a user.",
        "`=dewarn <user> <index>` — Remove a specific warning from a user.",
        "`=warns [user]` — View all warnings for a user.",
        "`=clearwarns <user>` — Remove all warnings from a user.",
        "`=mute <user> <duration> [reason]` — Timeout a member (Example: `=mute @user 10m Spamming`).",
        "`=unmute <user>` — Remove timeout from a member.",
        "`=cleanwarns <user>` — Clear all warnings for a user.",
    ],
    "Ticket Commands": [
        "`=panel` — Permissions: `1451578463617290240`.",
        "`=application` — Permissions: `1451578463617290240`.",
        "`=appopen` — Permissions: `1451578463617290240`.",
        "`=appclose` — Permissions: `1451578463617290240`.",
        "`=critical` — Permissions: `@゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=givetranscript` — Permissions: `@゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=clean` — Permissions: `@゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=ticketdone` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=pending` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=close` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=reopen` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=add` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=remove` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=rename` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
        "`=transcript` — Permissions: `1451578463617290240`, `@゛ OWNERS ⸝⸝.ᐟ⋆ + @゛ OWNERS ⸝⸝.ᐟ⋆`.",
    ],
    "Admin Commands": [
        "`=role <user> <role>` — Assign or remove a role from a member.",
        "`=cnuke` — Clone and delete the current channel.",
        "`=notfa` — Toggle channel between admin-only and normal access.",
        "`=private` — Toggle channel between staff-only and normal access.",
        "`=full` — Lock channel to members only.",
        "`=ban <user> [reason]` — Ban a user from the server.",
        "`=unban <user_id|name#tag>` — Unban a user from the server.",
        "`=banlist` — View banned users with quick unban buttons.",
        "`=kick <user> [reason]` — Kick a user from the server.",
        "`=nick <@user|username|id> <nickname>` — Change or reset a user's nickname.",
        "`=roleaccess` — Post the supporter role access panel.",
    ],
    "Tag System": [
        "`=tagc <name> <content>` — Create a new tag.",
        "`=tag <name>` — Use a saved tag.",
        "`=taglist` — List all available tags.",
        "`=tagdel <name>` — Delete a tag (admin only).",
    ],
}


def _help_card(section: str) -> str:
    if section == "Help Menu":
        return "Choose a category from the select menu below."
    header = f"**{section}:**\n"
    lines = "\n".join(f"> {entry}" for entry in HELP_SECTIONS[section])
    return f"{header}\n{lines}"


class HelpView(discord.ui.DesignerView):
    def __init__(self, section: str = "Help Menu"):
        super().__init__(timeout=None)
        self.section = section
        thumbs = CFG.get("theme", {}).get("thumbs", {})
        self.thumbnail_url = "https://media.discordapp.net/attachments/1482517562196496515/1482518798715060407/7f2ed419-ebf6-4466-a5d6-17e008a61e13.png?ex=69b73eb9&is=69b5ed39&hm=087f335e1b493fa391cf245609f2bc0dc6124889e5092d47cae909be98743944&=&format=webp&quality=lossless&width=560&height=560"

        # Build embed for the current section
        accent = CFG.get("theme", {}).get("accent_int", 0x87CEEB)
        desc = _help_card(section)
        if section == "Help Menu":
            desc = f"**Help Menu**\n\n{desc}"
        self.embed = discord.Embed(description=desc, color=discord.Color(accent))
        self.embed.set_thumbnail(url=self.thumbnail_url)

        # Select menu options
        options = [
            discord.SelectOption(label=name, value=name, default=(name == section))
            for name in HELP_SECTIONS
        ]

        # Create the Select menu
        select = discord.ui.Select(
            placeholder="Choose a category...",
            options=options,
            custom_id="silverslots.help.menu",
        )

        async def cb(inter: discord.Interaction):
            chosen = select.values[0]
            await inter.response.defer()
            try:
                new_view = HelpView(chosen)
                await inter.message.edit(embed=new_view.embed, view=new_view)
            except discord.HTTPException:
                await inter.followup.send(
                    "This help menu expired — run `=help` again.",
                    ephemeral=True,
                )

        select.callback = cb  # type: ignore

        # ✅ Add the Select via an ActionRow
        row = discord.ui.ActionRow(select)
        self.add_item(row)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        view = HelpView("Help Menu")
        await ctx.send(embed=view.embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(Help(bot))
