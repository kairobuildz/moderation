import json
import os
import discord
from discord.ext import commands
from .style import card, CFG, maybe_delete_invocation

TAGS_FILE = os.path.join(os.path.dirname(__file__), "..", "storage", "tags.json")

def load_tags():
    """Load tags from storage file"""
    if os.path.exists(TAGS_FILE):
        try:
            with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tags(tags):
    """Save tags to storage file"""
    os.makedirs(os.path.dirname(TAGS_FILE), exist_ok=True)
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, indent=2, ensure_ascii=False)

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tags = load_tags()

    async def cog_load(self):
        # Auto-register saved tags when the cog loads so they persist across servers/restarts.
        await self.register_tag_commands()

    @commands.command(name="tagc")
    async def tagc(self, ctx: commands.Context, *, content: str):
        """Create a new tag"""
        await maybe_delete_invocation(ctx)
        
        # Check if user has permission (mod or admin)
        if not CFG.get("roles", {}).get("MOD_ROLE_ID") or not CFG.get("roles", {}).get("ADMIN_ROLE_ID"):
            await ctx.send(view=card("Error", "Tag system not configured properly.").to_view())
            return
            
        mod_role = ctx.guild.get_role(int(CFG["roles"]["MOD_ROLE_ID"]))
        admin_role = ctx.guild.get_role(int(CFG["roles"]["ADMIN_ROLE_ID"]))
        
        if not (mod_role in ctx.author.roles or admin_role in ctx.author.roles or ctx.author.guild_permissions.administrator):
            await ctx.send(view=card("Permission Denied", "You need mod permissions to create tags.").to_view())
            return
        
        # Create tag name from content (first word)
        tag_name = content.split()[0].lower()
        tag_content = content[len(tag_name):].strip()
        
        if not tag_content:
            await ctx.send(view=card("Error", "Please provide content for the tag.").to_view())
            return
            
        # Save the tag
        self.tags[tag_name] = {
            "content": tag_content,
            "created_by": ctx.author.id,
            "created_at": discord.utils.utcnow().isoformat()
        }
        save_tags(self.tags)
        
        # Register the new tag as a command
        await self.register_tag_commands()
        
        # Send confirmation
        await ctx.send(view=card("Tag Created", f"Tag `{tag_name}` created successfully!\n\n**Content:** {tag_content}\n\nYou can now use `={tag_name}` to call this tag!").to_view())

    @commands.command(name="tag")
    async def tag(self, ctx: commands.Context, tag_name: str):
        """Use a tag"""
        await maybe_delete_invocation(ctx)
        
        tag_name = tag_name.lower()
        if tag_name not in self.tags:
            await ctx.send(view=card("Tag Not Found", f"Tag `{tag_name}` does not exist.\nUse `=taglist` to see all available tags.").to_view())
            return
            
        tag_data = self.tags[tag_name]
        await ctx.send(tag_data["content"])

    def get_tag_command(self, tag_name: str):
        """Get a tag command function for dynamic command registration"""
        async def tag_cmd(ctx: commands.Context):
            await maybe_delete_invocation(ctx)
            if tag_name in self.tags:
                await ctx.send(self.tags[tag_name]["content"])
            else:
                await ctx.send(view=card("Tag Not Found", f"Tag `{tag_name}` does not exist.").to_view())
        return tag_cmd

    async def register_tag_commands(self):
        """Register all tags as commands"""
        for tag_name in self.tags:
            # Remove existing command if it exists
            if tag_name in self.bot.all_commands:
                self.bot.remove_command(tag_name)
            
            # Create and register new command
            tag_cmd = self.get_tag_command(tag_name)
            tag_cmd.__name__ = tag_name
            tag_cmd.__qualname__ = f"Tags.{tag_name}"
            tag_cmd.help = f"Tag: {self.tags[tag_name]['content'][:50]}..."
            
            self.bot.add_command(commands.Command(tag_cmd, name=tag_name))

    @commands.command(name="taglist")
    async def taglist(self, ctx: commands.Context):
        """List all available tags"""
        await maybe_delete_invocation(ctx)
        
        if not self.tags:
            await ctx.send(view=card("No Tags", "No tags have been created yet.").to_view())
            return
            
        # Create embed with tag list
        brand = CFG.get("brand", "Zelune's Slots")
        embed = discord.Embed(color=0xFF8A00)
        embed.timestamp = discord.utils.utcnow()
        
        # Group tags by category or just list them
        tag_list = []
        for tag_name, tag_data in self.tags.items():
            content_preview = tag_data["content"][:50] + "..." if len(tag_data["content"]) > 50 else tag_data["content"]
            tag_list.append(f"**`{tag_name}`**\n> {content_preview}")
        
        # Split into chunks if too many tags
        if len(tag_list) <= 10:
            embed.description = "\n\n".join(tag_list)
        else:
            # Create multiple embeds for many tags
            chunks = [tag_list[i:i+10] for i in range(0, len(tag_list), 10)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    embed.description = "**Available Tags**\n\n" + "\n\n".join(chunk)
                    await ctx.send(embed=embed)
                else:
                    page_embed = discord.Embed(color=0xFF8A00)
                    page_embed.description = f"**Available Tags (Page {i+1})**\n\n" + "\n\n".join(chunk)
                    page_embed.timestamp = discord.utils.utcnow()
                    await ctx.send(embed=page_embed)
            return
            
        embed.description = "**Available Tags**\n\n" + "\n\n".join(tag_list)
        await ctx.send(embed=embed)

    @commands.command(name="tagdel")
    async def tagdel(self, ctx: commands.Context, tag_name: str):
        """Delete a tag (admin only)"""
        await maybe_delete_invocation(ctx)
        
        # Check admin permissions
        admin_role = ctx.guild.get_role(int(CFG["roles"]["ADMIN_ROLE_ID"]))
        if not (admin_role in ctx.author.roles or ctx.author.guild_permissions.administrator):
            await ctx.send(view=card("Permission Denied", "You need admin permissions to delete tags.").to_view())
            return
            
        tag_name = tag_name.lower()
        if tag_name not in self.tags:
            await ctx.send(view=card("Tag Not Found", f"Tag `{tag_name}` does not exist.").to_view())
            return
            
        # Delete the tag
        deleted_content = self.tags[tag_name]["content"]
        del self.tags[tag_name]
        save_tags(self.tags)
        
        await ctx.send(view=card("Tag Deleted", f"Tag `{tag_name}` has been deleted.\n\n**Content was:** {deleted_content}").to_view())

def setup(bot):
    bot.add_cog(Tags(bot))
