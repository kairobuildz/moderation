import io
import aiohttp
import qrcode
import discord
from discord.ext import commands
from decimal import Decimal, ROUND_DOWN
from qrcode.constants import ERROR_CORRECT_Q
from urllib.parse import urlencode

from .style import CardLayout, card, CFG, maybe_delete_invocation
from storage.cache import ltc_eur, ltc_rates, last_ltc_price
from storage.ratelimit import allow

# ✅ Baby-blue theme & updated LTC logo
BABY_BLUE = (135, 206, 235)  # Accent color for embeds
QR_FOREGROUND = "black"  # Solid black for maximum contrast
QR_BOX_SIZE = int(CFG.get("features", {}).get("qr_box_size", 5))
QR_BORDER = int(CFG.get("features", {}).get("qr_border", 4))
QR_ADDRESS_ONLY = CFG.get("features", {}).get("qr_address_only", True)
LTC_LOGO = "https://media.discordapp.net/attachments/1429831741895475253/1429836818278383636/7d3b2caf-removebg-preview.png?ex=68f796ce&is=68f6454e&hm=ae1bc1a62bb2645d2d11ddfbf1dde47606237f26d8243922444125d1a0c4235f&=&format=webp&quality=lossless&width=800&height=800"
THUMB_URL = CFG.get("theme", {}).get("thumbs", {}).get("help", "https://imgur.com/a/3LD6C7U#CcCmoCl")

_LTC_QUANT = Decimal("0.00000001")


def _format_ltc_amount(amount: Decimal | float | str) -> str:
    """Return an LTC amount string with exactly 8 decimal places."""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return format(amount.quantize(_LTC_QUANT, rounding=ROUND_DOWN), "f")


def _first_key(d: dict):
    return next(iter(d.keys())) if d else None


class UpstreamError(RuntimeError):
    def __init__(self, status: int, msg: str = ""):
        self.status = status
        super().__init__(msg or f"HTTP {status}")


async def _http_json(url: str, params: dict | None = None):
    """Perform GET request and return parsed JSON or raise UpstreamError."""
    headers = {"User-Agent": CFG["payments"]["ltc"].get("user_agent", "SilverSlots/1.0")}
    token = CFG["payments"]["ltc"].get("blockcypher_token", "")
    if token:
        params = dict(params or {})
        params["token"] = token

    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.get(url, params=params, timeout=25) as r:
            text = await r.text()

            try:
                data = await r.json()
            except Exception:
                raise UpstreamError(r.status, f"Non-JSON response: {text[:120]}")

            if r.status != 200:
                msg = data.get("error", f"HTTP {r.status}")
                raise UpstreamError(r.status, msg)

            if "error" in data:
                raise UpstreamError(r.status, data["error"])

            return data


async def _blockcypher_address(addy: str):
    """Fetch LTC address balance details from BlockCypher."""
    base = CFG["payments"]["ltc"]["blockcypher_base"].rstrip("/")
    data = await _http_json(f"{base}/ltc/main/addrs/{addy}/balance")
    if "balance" not in data and "final_balance" not in data:
        raise RuntimeError("No balance data for this address.")
    return {
        "confirmed": data.get("balance", 0) / 1e8,
        "unconfirmed": data.get("unconfirmed_balance", 0) / 1e8,
        "final": data.get("final_balance", 0) / 1e8,
        "received": data.get("total_received", 0) / 1e8,
        "txs": data.get("n_tx", 0),
    }


async def _blockcypher_tx(txid: str):
    """Fetch LTC transaction details from BlockCypher."""
    base = CFG["payments"]["ltc"]["blockcypher_base"].rstrip("/")
    data = await _http_json(f"{base}/ltc/main/txs/{txid}")
    raw_outputs = data.get("outputs")
    if not raw_outputs:
        raise RuntimeError("No data for this transaction.")
    conf = data.get("confirmations", 0)
    items, total = [], 0.0
    for idx, o in enumerate(raw_outputs):
        addr = o.get("addresses", ["N/A"])[0] if o.get("addresses") else "N/A"
        val = o.get("value", 0) / 1e8
        total += val
        if idx < 5:
            items.append((addr, val))
    return total, conf, items, len(raw_outputs)


class LTCView(discord.ui.DesignerView):
    def __init__(self, payload: CardLayout, address: str, amount_ltc: str):
        super().__init__(timeout=None)
        self.address = address
        self.amount_ltc = amount_ltc

        # === Create Buttons ===
        qr_button = discord.ui.Button(
            label="Generate QR Code",
            style=discord.ButtonStyle.primary,
            custom_id="vexus.qr",
        )
        qr_button.callback = self._on_generate_qr

        copy_address_button = discord.ui.Button(
            label="Copy Address",
            style=discord.ButtonStyle.secondary,
            custom_id="vexus.copy_addr",
        )
        copy_address_button.callback = self._on_copy_address

        copy_amount_button = discord.ui.Button(
            label="Copy Amount",
            style=discord.ButtonStyle.secondary,
            custom_id="vexus.copy_amt",
        )
        copy_amount_button.callback = self._on_copy_amount

        # === Use ActionRow for Pycord v2 compatibility ===
        row = discord.ui.ActionRow(qr_button, copy_address_button, copy_amount_button)

        container = payload.to_container()
        container.add_item(discord.ui.Separator())
        self.add_item(container)
        self.add_item(row)

    async def _on_generate_qr(self, interaction: discord.Interaction):
        if QR_ADDRESS_ONLY:
            qr_payload = self.address
        else:
            params = urlencode({"amount": self.amount_ltc}) if self.amount_ltc else ""
            qr_payload = f"litecoin:{self.address}"
            if params:
                qr_payload = f"{qr_payload}?{params}"

        qr = qrcode.QRCode(
            version=None,
            box_size=QR_BOX_SIZE,
            border=QR_BORDER,
            error_correction=ERROR_CORRECT_Q,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color=QR_FOREGROUND, back_color="white").convert("RGB")

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)

        message = interaction.message
        file = discord.File(buf, filename="ltc_qr_styled.png")

        if message and message.embeds:
            embed = message.embeds[0]
            embed.set_image(url="attachment://ltc_qr_styled.png")
            await message.edit(embed=embed, attachments=[file])
            await interaction.response.send_message("✅ QR Code generated and added!", ephemeral=True)
        else:
            embed = discord.Embed(description="**LTC Payment QR Code**", color=0x87CEEB)
            embed.set_image(url="attachment://ltc_qr_styled.png")
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

    async def _on_copy_address(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            await interaction.followup.send(self.address, ephemeral=True)
        else:
            await interaction.response.send_message(self.address, ephemeral=True)

    async def _on_copy_amount(self, interaction: discord.Interaction):
        content = self.amount_ltc
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)


class Payments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pm")
    async def pm(self, ctx: commands.Context):
        await maybe_delete_invocation(ctx)
        addresses = CFG["payments"].get("addresses", {})
        lines = []
        for coin in CFG["payments"]["coins"]:
            key = coin.upper()
            addr = addresses.get(key)
            if addr:
                lines.append(f"> **{key}**\n`{addr}`")
            else:
                lines.append(f"> **{key}**")
        desc = "\n\n".join(lines) or "No payment methods configured."
        base_view = card("Payment Methods", desc, thumbnail=LTC_LOGO)

        # Buttons to copy addresses
        ltc_btn = discord.ui.Button(label="Copy LTC", style=discord.ButtonStyle.primary, custom_id="pm.copy_ltc")
        btc_btn = discord.ui.Button(label="Copy BTC", style=discord.ButtonStyle.secondary, custom_id="pm.copy_btc")
        eth_btn = discord.ui.Button(label="Copy ETH", style=discord.ButtonStyle.secondary, custom_id="pm.copy_eth")

        async def send_addr(inter: discord.Interaction, coin: str):
            addr = addresses.get(coin)
            if not addr:
                await inter.response.send_message(f"No {coin} address configured.", ephemeral=True)
                return
            if inter.response.is_done():
                await inter.followup.send(addr, ephemeral=True)
            else:
                await inter.response.send_message(addr, ephemeral=True)

        ltc_btn.callback = lambda inter: send_addr(inter, "LTC")
        btc_btn.callback = lambda inter: send_addr(inter, "BTC")
        eth_btn.callback = lambda inter: send_addr(inter, "ETH")

        view = base_view.to_view(ltc_btn, btc_btn, eth_btn)
        await ctx.send(view=view)

    @commands.command(name="ltc")
    async def ltc(self, ctx: commands.Context, eur: float):
        await maybe_delete_invocation(ctx)
        ok, rem = allow(f"ltc:{ctx.channel.id}", int(CFG["cooldowns"].get("ltc_per_channel_seconds", 5)))
        if not ok:
            await ctx.send(view=card("Slow down", f"Try again in `{rem:.1f}s`").to_view())
            return

        rate = await ltc_eur()
        prev = last_ltc_price() or rate
        delta = rate - prev
        pct = (delta / prev * 100.0) if prev else 0.0
        trend = "up" if delta > 0 else ("down" if delta < 0 else "unchanged")
        trend_note = f"\n\n**Price check:** LTC/EUR is **{trend} {abs(pct):.2f}%** since last request."
        ltc_amt_decimal = (Decimal(str(eur)) / Decimal(str(rate))).quantize(_LTC_QUANT, rounding=ROUND_DOWN)
        ltc_amt_str = _format_ltc_amount(ltc_amt_decimal)
        addr = CFG["payments"]["ltc"]["address"]

        desc = (
            f"**Scan the QR Code** or pay to the address with the exact amount:{trend_note}\n"
            f"```{addr}```\n```€{eur:.2f} / {ltc_amt_str} LTC```\n"
            f"Once you have sent the payment, let our Staff know."
        )
        payload = card("LTC Payment", desc, thumbnail=LTC_LOGO)
        await ctx.send(view=LTCView(payload, addr, ltc_amt_str))

    @commands.command(name="bal")
    async def bal(self, ctx: commands.Context, addy: str):
        await maybe_delete_invocation(ctx)
        try:
            rates = await ltc_rates()
            balance = await _blockcypher_address(addy)
            accent = CFG.get("theme", {}).get("accent_int", 0x87CEEB)

            def build_embed(currency: str) -> discord.Embed:
                rate = rates.get(currency, 0.0)
                symbol = "$" if currency.lower() == "usd" else "€"
                currency = currency.lower()
                value_label = "USD Value" if symbol == "$" else "EUR Value"
                embed = discord.Embed(color=discord.Color(accent))
                embed.set_thumbnail(url=THUMB_URL)
                embed.description = (
                    "**Litecoin Address Balance**\n"
                    f"**Confirmed Balance:**\n"
                    f"` {balance['confirmed']:.8f} LTC`\n\n"
                    f"**{value_label}:**\n"
                    f"` {symbol}{balance['confirmed'] * rate:.2f}`\n\n"
                    f"**Unconfirmed Balance:**\n"
                    f"` {balance['unconfirmed']:.8f} LTC`\n\n"
                    f"**{value_label}:**\n"
                    f"` {symbol}{balance['unconfirmed'] * rate:.2f}`\n\n"
                    f"**Total Received:**\n"
                    f"` {balance['received']:.8f} LTC`\n\n"
                    f"**{value_label}:**\n"
                    f"` {symbol}{balance['received'] * rate:.2f}`"
                )
                return embed

            class BalanceView(discord.ui.View):
                def __init__(self, address: str):
                    super().__init__(timeout=None)
                    self.address = address
                    self.currency = "usd" if "usd" in rates else "eur"

                    self.usd_button = discord.ui.Button(
                        label="USD View",
                        style=discord.ButtonStyle.primary,
                        custom_id="balance.usd",
                        disabled="usd" not in rates,
                    )
                    self.eur_button = discord.ui.Button(
                        label="EUR View",
                        style=discord.ButtonStyle.secondary,
                        custom_id="balance.eur",
                        disabled="eur" not in rates,
                    )
                    url_button = discord.ui.Button(
                        label="View Transaction",
                        style=discord.ButtonStyle.link,
                        url=f"https://blockchair.com/litecoin/address/{address}",
                    )

                    if self.currency == "eur":
                        self.usd_button.style = discord.ButtonStyle.secondary
                        self.eur_button.style = discord.ButtonStyle.primary

                    async def show_usd(interaction: discord.Interaction):
                        self.currency = "usd"
                        self._update_styles()
                        await interaction.response.edit_message(embed=build_embed("usd"), view=self)

                    async def show_eur(interaction: discord.Interaction):
                        self.currency = "eur"
                        self._update_styles()
                        await interaction.response.edit_message(embed=build_embed("eur"), view=self)

                    self.usd_button.callback = show_usd
                    self.eur_button.callback = show_eur

                    self.add_item(self.usd_button)
                    self.add_item(self.eur_button)
                    self.add_item(url_button)

                def _update_styles(self):
                    if self.currency == "usd":
                        self.usd_button.style = discord.ButtonStyle.primary
                        self.eur_button.style = discord.ButtonStyle.secondary
                    else:
                        self.usd_button.style = discord.ButtonStyle.secondary
                        self.eur_button.style = discord.ButtonStyle.primary

            view = BalanceView(addy)
            start_currency = view.currency
            await ctx.send(embed=build_embed(start_currency), view=view)
        except UpstreamError as ue:
            await ctx.send(view=card("Error checking balance", f"Upstream error: {ue}").to_view())
        except Exception as e:
            await ctx.send(view=card("Error checking balance", f"{e}").to_view())

    @commands.command(name="tx")
    async def tx(self, ctx: commands.Context, txid: str):
        await maybe_delete_invocation(ctx)
        try:
            rates = await ltc_rates()
            usd_rate = rates.get("usd") or next(iter(rates.values()), 0.0)
            eur_rate = rates.get("eur") or next(iter(rates.values()), 0.0)
            total, conf, outputs, output_count = await _blockcypher_tx(txid)
            total_usd = total * usd_rate

            lines = [
                f"**Transaction ID**",
                f"`{txid}`",
                "",
                f"**Confirmations**",
                f"`{conf}/6`",
                "",
                f"**Total Output [{output_count}]**",
                f"`{total:.8f} LTC | ${total_usd:.2f}`",
                "",
                "**Outputs**",
            ]

            for addr, val in outputs:
                usd_val = val * usd_rate
                lines.append(
                    f"- > [**{addr}**](https://blockchair.com/litecoin/address/{addr})\n"
                    f"  -  {val:.8f} LTC | ${usd_val:.2f}"
                )
            if output_count > len(outputs):
                lines.append(f"*+ {output_count - len(outputs)} more outputs not shown.*")

            lines.append(f"\n*Quoted at ${usd_rate:.2f} / €{eur_rate:.2f} per LTC*")

            desc = "\n".join(lines)

            embed = discord.Embed(
                description=f"**Litecoin Transaction Details**\n{desc}",
                color=discord.Color(CFG.get("theme", {}).get("accent_int", 0x87CEEB)),
            )
            embed.set_thumbnail(url=THUMB_URL)

            link_button = discord.ui.Button(
                label="View on Blockchair",
                style=discord.ButtonStyle.link,
                url=f"https://blockchair.com/litecoin/transaction/{txid}",
            )
            view = discord.ui.View()
            view.add_item(link_button)

            m = await ctx.send(embed=embed, view=view)
            try:
                await m.delete(delay=60)
            except Exception:
                pass
        except UpstreamError as ue:
            await ctx.send(view=card("Error checking transaction", f"Upstream error: {ue}").to_view())
        except Exception as e:
            await ctx.send(view=card("Error checking transaction", f"{e}").to_view())


def setup(bot):
    bot.add_cog(Payments(bot))
