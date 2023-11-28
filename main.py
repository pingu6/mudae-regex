# main.py
import datetime
import logging

import aiofiles
import aiohttp
import asqlite
import discord
import starlight  # type: ignore
import toml
from asqlite import Pool
from discord.ext import commands

from cogs import EXTENSIONS

config = toml.load("config.toml")
default_prefix = config["PREFIX"]
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=get_prefix,
            intents=discord.Intents.all(),
            case_insensitive=True,
            strip_after_prefix=True,
            activity=discord.Game(name=f"{default_prefix}help"),
            help_command=starlight.MenuHelpCommand(
                accent_color=discord.Color.blue(),
                command_attrs={"hidden": True},
                pagination_buttons={
                    "start_button": None,
                    "end_button": None,
                    "previous_button": discord.ui.Button(emoji="<:RemLeft:1052054214634913882>", row=0),
                    "next_button": discord.ui.Button(emoji="<:RamRight:1052054203901673482>", row=0),
                    "stop_button": discord.ui.Button(label="Quit", row=2, style=discord.ButtonStyle.red),
                },  # type: ignore
            ),
        )
        self.pool: Pool
        self.session: aiohttp.ClientSession
        self.config = config
        self.prefixes: dict[int, str] = {}
        self.default_prefix: str = default_prefix
        self.launch_time = datetime.datetime.now(datetime.timezone.utc)

    async def setup_hook(self) -> None:
        print(f"Logged on as {self.user} (ID: {self.user.id})")  # type: ignore
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        await self.load_extension("jishaku")
        print("Loaded cogs")
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector())

        self.pool = await asqlite.create_pool("database.db")
        async with self.pool.acquire() as conn, aiofiles.open("schema.sql") as fp:
            await conn.executescript(await fp.read())
            await conn.commit()

    async def close(self) -> None:
        await self.pool.close()
        await self.session.close()
        await super().close()


# https://mystb.in/PoundJpgQuarter
async def get_prefix(bot: Bot, message: discord.Message) -> list[str]:
    if not message.guild or not bot.user:  # check if dm
        return commands.when_mentioned_or(default_prefix)(bot, message)  # return default prefix
    try:
        return commands.when_mentioned_or(bot.prefixes[message.guild.id])(bot, message)

    except KeyError:
        async with bot.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT prefix FROM prefixes WHERE guild_id = ?",
                (message.guild.id,),
            )
            prefix = await cursor.fetchone()
            await conn.commit()

        if prefix:  # if it's in the database,
            bot.prefixes.update({message.guild.id: prefix["prefix"]})  # cache it
            return commands.when_mentioned_or(bot.prefixes.get(message.guild.id, default_prefix))(bot, message)

        else:  # if not in the database,
            # insert into the database
            async with bot.pool.acquire() as conn:
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
                    (message.guild.id, default_prefix),
                )
                await conn.commit()
            bot.prefixes.update({message.guild.id: default_prefix})  # after inserting, cache it
            return commands.when_mentioned_or(bot.prefixes.get(message.guild.id, default_prefix))(bot, message)


if __name__ == "__main__":
    Bot().run(config["TOKEN"], log_handler=handler)
