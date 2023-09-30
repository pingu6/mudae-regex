# cogs / prefix.py
from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Guild
from discord.ext import commands

if TYPE_CHECKING:
    from main import Bot


class Prefix(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        await self.bot.db.prefixes.create_many(
            data=[{'bot_id': self.bot.user.id, 'guild_id': guild.id, 'prefix': self.bot.default_prefix}],
        )
        self.bot.prefixes.pop(guild.id, None)
        await self.bot.db.bots.update(
            where={
                'id': self.bot.user.id,
            },
            data={
                'guild_count': {
                    'increment': 1,
                }
            },
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await self.bot.db.prefixes.delete_many(
            where={
                'bot_id': self.bot.user.id,
                'guild_id': guild.id,
            },
        )
        self.bot.prefixes[guild.id] = self.bot.default_prefix
        await self.bot.db.bots.update(
            where={
                'id': self.bot.user.id,
            },
            data={
                'guild_count': {
                    'decrement': 1,
                }
            },
        )

    @commands.hybrid_command(name='prefix')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context[Bot], prefix: str):
        """change bot prefix"""
        if not ctx.guild:
            return
        await self.bot.db.prefixes.update_many(
            where={
                'bot_id': self.bot.user.id,
                'guild_id': ctx.guild.id,
            },
            data={
                'prefix': prefix,
            },
        )
        self.bot.prefixes[ctx.guild.id] = prefix
        await ctx.send(f'prefix changed to `{prefix}`')


async def setup(bot: Bot):
    await bot.add_cog(Prefix(bot))
