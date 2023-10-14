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
        self.bot.prefixes[guild.id] = self.bot.default_prefix
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    prefixes (guild_id, prefix)
                VALUES
                    (?, ?)
                ON CONFLICT (guild_id) DO UPDATE
                SET
                    prefix = excluded.prefix
                """,
                (guild.id, self.bot.default_prefix),
            )
            await conn.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        self.bot.prefixes[guild.id] = self.bot.default_prefix
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM prefixes WHERE guild_id = guild_id",
                (guild.id,),
            )
            await conn.commit()

    @commands.hybrid_command(name='prefix')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context[Bot], prefix: str):
        """change bot prefix"""
        if not ctx.guild:
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    prefixes (guild_id, prefix)
                VALUES
                    (?, ?)
                ON CONFLICT (guild_id) DO UPDATE
                SET
                    prefix = excluded.prefix
                """,
                (ctx.guild.id, prefix),
            )
            await conn.commit()
        self.bot.prefixes[ctx.guild.id] = prefix
        await ctx.send(f'prefix changed to `{prefix}`')


async def setup(bot: Bot):
    await bot.add_cog(Prefix(bot))
