from __future__ import annotations

import datetime
import itertools
import platform
from dataclasses import dataclass
from typing import TYPE_CHECKING
import asyncio
from io import BytesIO
import discord
import psutil
import pygit2
from discord import utils
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from main import Bot


@dataclass
class BotData:
    name: str
    image: bytes
    guild_count: int


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process = psutil.Process()

    # https://gist.github.com/Gorialis/e89482310d74a90a946b44cf34009e88
    @staticmethod
    def processing(bots: list[BotData]) -> BytesIO:
        with Image.new('RGBA', (250, len(bots) * 48)) as blank:
            draw = ImageDraw.Draw(blank)
            font = ImageFont.truetype('Assets/fonts/JetBrainsMono/JetBrainsMono-Regular.ttf', size=12)
            for index, bot in enumerate(bots):
                with Image.open(BytesIO(bot.image)) as image:
                    blank.paste(image.resize((48, 48)), (0, index * 48))
                    draw.text((52, 24 + index * 48), f"{bot.name} . guild count: {bot.guild_count}", font=font)
                    if index + 1 < len(bots):
                        draw.line((0, 47 + index * 48, 250, 47 + index * 48), fill="#000000", width=1)

            final_buffer = BytesIO()
            blank.save(final_buffer, "png")
            final_buffer.seek(0)

            return final_buffer

    # This code is licensed MPL v2 from https://github.com/Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/stats.py#L260-L304

    def format_commit(self, commit: pygit2.Commit) -> str:
        short, _, _ = commit.message.partition('\n')
        short_sha2 = commit.hex[:6]
        commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)

        # [`hash`](url) message (offset)
        offset = utils.format_dt(commit_time, style='R')
        return f'[`{short_sha2}`](https://github.com/tuna-chan404/mudae-regex/commit/{commit.hex}) {short} ({offset})'

    def get_last_commits(self, count: int = 3):
        repo = pygit2.Repository('.git')
        commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count))
        return '\n'.join(self.format_commit(c) for c in commits)

    @commands.hybrid_command(name='about')
    async def about(self, ctx: commands.Context[Bot]):
        """Tells you information about the bot itself."""
        revision = self.get_last_commits()
        embed = discord.Embed(description='Latest Changes:\n' + revision)
        embed.color = discord.Color.brand_red()
        embed.set_author(name=str(ctx.author.name), icon_url=ctx.author.display_avatar.url)

        # statistics
        total_members = 0
        total_unique = len(self.bot.users)

        text = 0
        voice = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count or 0
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1
        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')
        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name='Guilds', value=guilds)
        embed.add_field(
            name='python',
            value=f"""
        <:python:1054963692694937711> [**python**](https://www.python.org) `{platform.python_version()}`
        <:DiscordPy:1054964966681219084> [**discord.py**](https://github.com/Rapptz/discord.py) `{discord.__version__}`""",
        )
        resolved_relative = utils.format_dt(ctx.bot.launch_time, 'R')
        embed.add_field(name='Uptime', value=resolved_relative)
        embed.timestamp = utils.utcnow()
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label='Support Server', url='https://discord.gg/XjWcDVvuPt'))
        view.add_item(
            discord.ui.Button(
                emoji='<:github:1085015921829101748>',
                label='Source Code',
                url='https://github.com/pingu6/mudae-regex',
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='uptime')
    async def uptime(self, ctx: commands.Context[Bot]):
        resolved_full = utils.format_dt(ctx.bot.launch_time, 'F')
        resolved_relative = utils.format_dt(ctx.bot.launch_time, 'R')
        await ctx.send(f'I started at {resolved_full}, and have been up since: {resolved_relative}')

    @commands.hybrid_command(name='invite')
    async def invite(self, ctx: commands.Context[Bot]):
        "Generate invite link for all Mudae Regex instances"
        async with ctx.typing():
            rows = await ctx.bot.db.bots.find_many(
                order={
                    'guild_count': 'desc',
                }
            )
            bots = [
                BotData(
                    row.name,
                    await ctx.bot.get_user(row.id).display_avatar.read(),
                    row.guild_count,
                )
                for row in rows
            ]
            final_buffer = await asyncio.to_thread(self.processing, bots)
            image = discord.File(filename="image.png", fp=final_buffer)
            embed = discord.Embed(color=discord.Color.brand_red())
            embed.set_image(url=f"attachment://{image.filename}")

            permission_names = (
                'send_messages',
                'send_messages_in_threads',
                'read_messages',
                'read_message_history',
                'embed_links',
                'add_reactions',
                'attach_files',
                'external_emojis',
                'view_channel',
            )
            permissions = discord.Permissions(**dict.fromkeys(permission_names, True))
            view = discord.ui.View()
            for row in rows:
                view.add_item(discord.ui.Button(label=row.name, url=utils.oauth_url(row.id, permissions=permissions)))
            await ctx.send(embed=embed, view=view, file=image)


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))
