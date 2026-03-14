import discord
from discord.ext import commands
from .style import card, CFG, maybe_delete_invocation, send_log, FlexibleMember, has_role, send_permission_denied

def channel_jump_url(ch: discord.TextChannel) -> str:
    return f"https://discord.com/channels/{ch.guild.id}/{ch.id}"

def goto_channel_button(ch: discord.TextChannel) -> discord.ui.Button:
    return discord.ui.Button(
        label="Go to Channel",
        style=discord.ButtonStyle.link,
        url=channel_jump_url(ch),
    )

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._protected_role_id = str(CFG.get("roles", {}).get("MOD_ROLE_ID") or "1446630188078207036")

    def _is_protected(self, member: discord.Member | None) -> bool:
        return has_role(member, self._protected_role_id)

    async def _deny_if_peer_protected(self, ctx: commands.Context, target: discord.Member, action: str) -> bool:
        """Block peer moderation between members sharing the protected role."""
        if self._is_protected(ctx.author) and self._is_protected(target):
            await ctx.send(view=card("Action Blocked", f"You cannot {action} someone with the same staff role.").to_view())
            return True
        return False

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

    @commands.command(name="role")
    async def role(self, ctx: commands.Context, role: discord.Role, target: FlexibleMember | None = None):
        """Toggle a role for a member. Usage: =role @Role @user (or username/ID/mention)."""
        await maybe_delete_invocation(ctx)
        member = target or ctx.author
        if not ctx.guild:
            await ctx.send(view=card("Role", "This command only works in servers.").to_view()); return
        if role.guild.id != ctx.guild.id:
            await ctx.send(view=card("Role", "That role belongs to another server.").to_view()); return
        if await self._deny_if_peer_protected(ctx, member, "toggle roles for"):
            return

        if role in member.roles:
            await member.remove_roles(role, reason=f"By {ctx.author}")
            payload = card("Role Removed", f"Removed {role.mention} from {member.mention}")
            await ctx.send(view=payload.to_view())
            log = card(
                "Log • Role Removed",
                f"**Member:** {member.mention} (`{member.id}`)\n"
                f"**Role:** {role.mention}\n"
                f"**Moderator:** {ctx.author.mention}",
            )
            await send_log(self.bot, ctx.guild, log.with_color(discord.Color.dark_gold()))
        else:
            await member.add_roles(role, reason=f"By {ctx.author}")
            payload = card("Role Added", f"Gave {role.mention} to {member.mention}")
            await ctx.send(view=payload.to_view())
            log = card(
                "Log • Role Added",
                f"**Member:** {member.mention} (`{member.id}`)\n"
                f"**Role:** {role.mention}\n"
                f"**Moderator:** {ctx.author.mention}",
            )
            await send_log(self.bot, ctx.guild, log.with_color(discord.Color.dark_gold()))

    @commands.command(name="early")
    async def early(self, ctx: commands.Context, user: FlexibleMember | None = None):
        """Give Early Supporter role to a user."""
        await maybe_delete_invocation(ctx)
        user = user or ctx.author
        role = self._get_role(ctx.guild, "EARLY_SUPPORTER_ID")
        if not role:
            await ctx.send(view=card("Early Supporter", "Role not found — check `EARLY_SUPPORTER_ID` in config.json.").to_view()); return
        if role in user.roles:
            await ctx.send(view=card("Early Supporter", f"{user.mention} already has {role.mention}").to_view()); return
        await user.add_roles(role, reason=f"Early by {ctx.author}")
        await ctx.send(view=card("Early Supporter", f"Gave {role.mention} to {user.mention}").to_view())

        log = card(
            "Log • Early Supporter",
            f"**Member:** {user.mention} (`{user.id}`)\n"
            f"**Role:** {role.mention}\n"
            f"**Granted by:** {ctx.author.mention}",
        )
        await send_log(self.bot, ctx.guild, log.with_color(discord.Color.gold()))

    @commands.command(name="inv")
    async def inv(self, ctx: commands.Context, user: FlexibleMember | None = None):
        """Give Merchant role to a user."""
        await maybe_delete_invocation(ctx)
        user = user or ctx.author
        role = self._get_role(ctx.guild, "MERCHANT_ID")
        if not role:
            await ctx.send(view=card("Merchant", "Role not found — check `MERCHANT_ID` in config.json.").to_view()); return
        if role in user.roles:
            await ctx.send(view=card("Merchant", f"{user.mention} already has {role.mention}").to_view()); return
        await user.add_roles(role, reason=f"Merchant by {ctx.author}")
        await ctx.send(view=card("Merchant", f"Gave {role.mention} to {user.mention}").to_view())

        log = card(
            "Log • Merchant Role",
            f"**Member:** {user.mention} (`{user.id}`)\n"
            f"**Role:** {role.mention}\n"
            f"**Granted by:** {ctx.author.mention}",
        )
        await send_log(self.bot, ctx.guild, log.with_color(discord.Color.gold()))

    @commands.command(name="notify")
    async def notify(self, ctx: commands.Context, target: FlexibleMember, *, message: str | None = None):
        msg = message or "Please check the channel as soon as possible."
        await maybe_delete_invocation(ctx)
        delivered = False
        try:
            payload = card(
                "Reminder Notification",
                f"You are reminded to check {ctx.channel.mention}\n\n**Message**\n{msg}",
            )
            dm_view = payload.to_view(goto_channel_button(ctx.channel))
            await target.send(view=dm_view)
            delivered = True
        except Exception:
            fb_id = CFG.get("logging", {}).get("dm_fallback_channel_id")
            try:
                fb = int(fb_id) if fb_id else None
            except (TypeError, ValueError):
                fb = None
            if fb and ctx.guild and (ch := ctx.guild.get_channel(fb)):
                fallback_view = card(
                    "Notify (fallback)",
                    f"{target.mention}\n\n{msg}",
                ).to_view(goto_channel_button(ctx.channel))
                await ch.send(view=fallback_view)
                delivered = True
            else:
                await ctx.send("Failed to notify — user has DMs closed and no fallback channel is configured.")
                log = card(
                    "Log • Notify Failed",
                    f"**Target:** {target.mention} (`{target.id}`)\n"
                    f"**Moderator:** {ctx.author.mention}\n"
                    f"**Message:** {msg}\n"
                    "Delivery failed.",
                )
                await send_log(self.bot, ctx.guild, log.with_color(discord.Color.red()))
                return

        await ctx.send(f"{target.mention} has been notified.")

        log = card(
            "Log • Notify",
            f"**Target:** {target.mention} (`{target.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Message:** {msg}\n"
            f"**Delivered:** {'Yes' if delivered else 'No'}",
        )
        await send_log(self.bot, ctx.guild, log.with_color(discord.Color.blue()))

    @commands.command(name="cnuke")
    async def cnuke(self, ctx: commands.Context):
        await maybe_delete_invocation(ctx)
        old: discord.TextChannel = ctx.channel
        overwrites = old.overwrites; category = old.category; position = old.position
        topic = old.topic; slowmode = old.slowmode_delay; nsfw = old.is_nsfw()
        new = await old.clone(name=old.name, reason=f"Nuked by {ctx.author}")
        if category:
            await new.edit(category=category, position=position, topic=topic, slowmode_delay=slowmode, nsfw=nsfw, overwrites=overwrites)
        else:
            await new.edit(position=position, topic=topic, slowmode_delay=slowmode, nsfw=nsfw, overwrites=overwrites)
        await old.delete(reason=f"Nuked by {ctx.author}")
        payload = card("Channel Nuked", f"Nuked by {ctx.author.mention}")
        await new.send(view=payload.to_view(goto_channel_button(new)))

        log = card(
            "Log • Channel Nuked",
            f"{old.mention} nuked and recreated as {new.mention} by {ctx.author.mention}.",
        ).with_color(discord.Color.dark_red())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="notfa", aliases=["restrict"])
    async def restrict(self, ctx: commands.Context):
        """Set channel to admin-only view."""
        await maybe_delete_invocation(ctx)

        try:
            overwrites = dict(ctx.channel.overwrites)
            default_role = ctx.guild.default_role
            admin_role = self._get_role(ctx.guild, "ADMIN_ROLE_ID")
            admin_tag = admin_role.mention if admin_role else "admins"

            current = overwrites.get(default_role)
            locked = current and current.read_messages is False

            if locked:
                overwrites[default_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if admin_role and admin_role in overwrites:
                    overwrites.pop(admin_role)
                await ctx.channel.edit(overwrites=overwrites)
                message = card("Channel Restored", f"{ctx.channel.mention} reverted to normal access.")
                log = card(
                    "Log • Restrict",
                    f"{ctx.channel.mention} unlocked by {ctx.author.mention}.",
                ).with_color(discord.Color.green())
            else:
                overwrites[default_role] = discord.PermissionOverwrite(read_messages=False, send_messages=False)
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                await ctx.channel.edit(overwrites=overwrites)
                message = card("Admin Only", f"{ctx.channel.mention} is now only visible to {admin_tag}.")
                log = card(
                    "Log • Restrict",
                    f"{ctx.channel.mention} locked to admins by {ctx.author.mention}.",
                ).with_color(discord.Color.dark_red())

            await ctx.send(view=message.to_view())
            await send_log(self.bot, ctx.guild, log)
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to modify this channel.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to restrict channel: {str(e)}").to_view())

    @commands.command(name="private")
    async def private(self, ctx: commands.Context):
        """Set channel to mod-only access."""
        await maybe_delete_invocation(ctx)
        
        try:
            overwrites = dict(ctx.channel.overwrites)
            default_role = ctx.guild.default_role
            mod_role = self._get_role(ctx.guild, "MOD_ROLE_ID")
            admin_role = self._get_role(ctx.guild, "ADMIN_ROLE_ID")
            mod_tag = mod_role.mention if mod_role else "staff"

            current = overwrites.get(default_role)
            locked = current and current.read_messages is False

            if locked and (mod_role and overwrites.get(mod_role) and overwrites.get(mod_role).read_messages):
                overwrites[default_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if mod_role and mod_role in overwrites:
                    overwrites.pop(mod_role)
                if admin_role and admin_role in overwrites:
                    overwrites.pop(admin_role)
                await ctx.channel.edit(overwrites=overwrites)
                await ctx.send(view=card("Channel Restored", f"{ctx.channel.mention} is now regular access.").to_view())

                log = card(
                    "Log • Private",
                    f"{ctx.channel.mention} restored by {ctx.author.mention}.",
                ).with_color(discord.Color.green())
                await send_log(self.bot, ctx.guild, log)
                return

            overwrites[default_role] = discord.PermissionOverwrite(read_messages=False, send_messages=False)
            
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
            await ctx.channel.edit(overwrites=overwrites)
            await ctx.send(view=card("Channel Private", f"{ctx.channel.mention} is now only visible to {mod_tag}.").to_view())

            log = card(
                "Log • Private",
                f"{ctx.channel.mention} locked to staff by {ctx.author.mention}.",
            ).with_color(discord.Color.blue())
            await send_log(self.bot, ctx.guild, log)
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to modify this channel.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to make channel private: {str(e)}").to_view())

    @commands.command(name="full")
    async def full(self, ctx: commands.Context):
        """Set channel to members-only access."""
        await maybe_delete_invocation(ctx)
        
        try:
            # Set channel to members-only access
            overwrites = ctx.channel.overwrites
            overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(read_messages=False, send_messages=False)
            
            # Member role and staff can access
            member_role = self._get_role(ctx.guild, "MEMBER_ROLE_ID")
            mod_role = self._get_role(ctx.guild, "MOD_ROLE_ID")
            admin_role = self._get_role(ctx.guild, "ADMIN_ROLE_ID")
            
            if member_role:
                overwrites[member_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
            await ctx.channel.edit(overwrites=overwrites)
            await ctx.send(view=card("Channel Full", f"{ctx.channel.mention} is now members-only access.").to_view())

            log = card(
                "Log • Full",
                f"{ctx.channel.mention} set to members-only by {ctx.author.mention}.",
            ).with_color(discord.Color.orange())
            await send_log(self.bot, ctx.guild, log)
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to modify this channel.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to make channel full: {str(e)}").to_view())

    @commands.command(name="nick")
    async def nick(self, ctx: commands.Context, member: FlexibleMember, *, nickname: str | None = None):
        """Change a member's nickname. Leave nickname blank to reset."""
        await maybe_delete_invocation(ctx)
        if await self._deny_if_peer_protected(ctx, member, "change the nickname of"):
            return
        before_nick = member.nick
        try:
            await member.edit(nick=nickname, reason=f"Nickname change by {ctx.author}")
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I can't edit that member's nickname.").to_view())
            return
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to change nickname: {e}").to_view())
            return

        if nickname:
            await ctx.send(view=card("Nickname Updated", f"Changed {member.mention}'s nickname to **{nickname}**.").to_view())
        else:
            await ctx.send(view=card("Nickname Reset", f"Reset {member.mention}'s nickname.").to_view())

        log = card(
            "Log • Nickname",
            f"{ctx.author.mention} updated {member.mention}'s nickname.\n"
            f"**Member:** {member.mention} (`{member.id}`)\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Old Nickname:** {before_nick or member.name}\n"
            f"**Nickname:** {nickname or 'Reset to default'}",
        ).with_color(discord.Color.blurple())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="ban")
    async def ban(self, ctx: commands.Context, user: FlexibleMember, *, reason: str = "No reason provided"):
        """Ban a user from the server."""
        await maybe_delete_invocation(ctx)
        if await self._deny_if_peer_protected(ctx, user, "ban"):
            return
        if not ctx.author.guild_permissions.ban_members and not ctx.author.guild_permissions.administrator:
            await send_permission_denied(ctx)
            return
        
        try:
            await user.ban(reason=f"Banned by {ctx.author}: {reason}")
            await ctx.send(view=card("User Banned", f"**{user.mention}** has been banned.\n**Reason:** {reason}").to_view())

            log = card(
                "Log • Ban",
                f"{ctx.author.mention} banned {user.mention}.\n"
                f"**User:** {user.mention} (`{user.id}`)\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Reason:** {reason}",
            ).with_color(discord.Color.dark_red())
            await send_log(self.bot, ctx.guild, log)
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to ban this user.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to ban user: {str(e)}").to_view())

    @commands.command(name="unban")
    async def unban(self, ctx: commands.Context, *, user: str):
        """Unban a user from the server."""
        await maybe_delete_invocation(ctx)
        if not ctx.author.guild_permissions.ban_members and not ctx.author.guild_permissions.administrator:
            await send_permission_denied(ctx)
            return
        if not ctx.guild:
            await ctx.send(view=card("", "This command only works in servers.").to_view())
            return

        target_entry = None
        bans = []
        try:
            bans = await ctx.guild.bans()
        except Exception:
            pass

        lookup = user.strip()
        for entry in bans:
            if str(entry.user.id) == lookup:
                target_entry = entry
                break
            tag = f"{entry.user.name}#{entry.user.discriminator}"
            if lookup.lower() == tag.lower():
                target_entry = entry
                break

        if not target_entry:
            try:
                obj = discord.Object(id=int(lookup))
                await ctx.guild.unban(obj, reason=f"Unbanned by {ctx.author}")
                target = lookup
            except Exception:
                await ctx.send(view=card("", f"Could not find a ban for `{lookup}`.").to_view())
                return
        else:
            target = f"{target_entry.user} (`{target_entry.user.id}`)"
            await ctx.guild.unban(target_entry.user, reason=f"Unbanned by {ctx.author}")

        await ctx.send(view=card("", f"Unbanned **{target}**.").to_view())

        log = card(
            "Log • Unban",
            f"Staff: {ctx.author.mention}\n"
            f"User: {target}\n"
            f"Reason: Unban",
        ).with_color(discord.Color.green())
        await send_log(self.bot, ctx.guild, log)

    @commands.command(name="banlist")
    async def banlist(self, ctx: commands.Context):
        """List banned users with quick unban buttons."""
        await maybe_delete_invocation(ctx)
        if not ctx.guild:
            await ctx.send(view=card("", "This command only works in servers.").to_view())
            return
        if not ctx.author.guild_permissions.ban_members and not ctx.author.guild_permissions.administrator:
            await send_permission_denied(ctx)
            return

        try:
            bans = await ctx.guild.bans()
        except Exception:
            await ctx.send(view=card("", "Could not fetch the ban list.").to_view())
            return

        if not bans:
            await ctx.send(view=card("", "No banned users.").to_view())
            return

        button_specs: list[tuple[discord.ui.Button, discord.User | discord.Member]] = []
        lines: list[str] = []
        shown = bans[:5]
        for entry in shown:
            user = entry.user
            lines.append(f"• {user} (`{user.id}`)")
            btn = discord.ui.Button(
                label=f"Unban {user.name}",
                style=discord.ButtonStyle.danger,
                custom_id=f"banlist.unban.{user.id}",
            )
            button_specs.append((btn, user))

        more_note = ""
        if len(bans) > len(shown):
            more_note = f"\n…and {len(bans) - len(shown)} more not shown."
        desc = "**Banned Users**\n" + "\n".join(lines) + more_note
        view = card("", desc).to_view(*(btn for btn, _ in button_specs))

        for btn, target in button_specs:
            async def cb(interaction: discord.Interaction, target=target, button=btn):
                if not interaction.guild:
                    return
                if not interaction.user.guild_permissions.ban_members and not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message(
                        "**<:no:1446871285438349354> Hello There! You do not have the required permissions to use this**",
                        ephemeral=True,
                    )
                    return
                try:
                    await interaction.guild.unban(target, reason=f"Quick unban by {interaction.user}")
                except Exception as exc:
                    await interaction.response.send_message(f"Failed to unban {target}: {exc}", ephemeral=True)
                    return

                button.disabled = True
                button.style = discord.ButtonStyle.secondary
                await interaction.response.edit_message(view=view)
                await interaction.followup.send(f"Unbanned **{target}**.", ephemeral=True)

                log = card(
                    "Log • Unban",
                    f"Staff: {interaction.user.mention}\n"
                    f"User: {target} (`{target.id}`)\n"
                    f"Reason: Quick unban from banlist",
                ).with_color(discord.Color.green())
                await send_log(self.bot, interaction.guild, log)

            btn.callback = cb  # type: ignore

        await ctx.send(view=view)

    @commands.command(name="kick")
    async def kick(self, ctx: commands.Context, user: FlexibleMember, *, reason: str = "No reason provided"):
        """Kick a user from the server."""
        await maybe_delete_invocation(ctx)
        if await self._deny_if_peer_protected(ctx, user, "kick"):
            return
        
        try:
            await user.kick(reason=f"Kicked by {ctx.author}: {reason}")
            await ctx.send(view=card("User Kicked", f"**{user.mention}** has been kicked.\n**Reason:** {reason}").to_view())

            log = card(
                "Log • Kick",
                f"{ctx.author.mention} kicked {user.mention}.\n"
                f"**User:** {user.mention} (`{user.id}`)\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Reason:** {reason}",
            ).with_color(discord.Color.orange())
            await send_log(self.bot, ctx.guild, log)
        except discord.Forbidden:
            await ctx.send(view=card("Permission Error", "I don't have permission to kick this user.").to_view())
        except Exception as e:
            await ctx.send(view=card("Error", f"Failed to kick user: {str(e)}").to_view())

    @commands.command(name="embed")
    async def embed(self, ctx: commands.Context, action: str, *, content: str = ""):
        """Create or edit embeds."""
        await maybe_delete_invocation(ctx)
        
        if action.lower() == "create":
            # Simple card creation using components
            await ctx.send(view=card("New Embed", content, color=discord.Color(0xFF8A00)).to_view())
        
        elif action.lower() == "edit":
            # This would require a message link to edit
            if not content:
                await ctx.send(view=card("Embed Edit", "Please provide a message link to edit.\nUsage: `=embed edit <message_link>`").to_view())
                return
            await ctx.send(view=card("Embed Edit", "Embed editing requires a message link. This feature is not fully implemented yet.").to_view())
            
        else:
            await ctx.send(view=card("Embed Command", "Usage:\n• `=embed create <content>` — Create a new embed\n• `=embed edit <message_link>` — Edit an existing embed").to_view())

def setup(bot):
    bot.add_cog(Admin(bot))
