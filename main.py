# main.py
import datetime
import logging

import aiohttp
import discord
import starlight
import toml
from discord.ext import commands, tasks
from prisma import Prisma

from cogs import EXTENSIONS

config = toml.load("config.toml")
default_prefix = config["PREFIX"]
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            intents=discord.Intents.all(),
            case_insensitive=True,
            strip_after_prefix=True,
            activity=discord.Game(name=f"{default_prefix}help, {default_prefix}invite"),
            help_command=starlight.MenuHelpCommand(
                per_page=10,
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
        self.db = Prisma()
        self.config = config
        self.session: aiohttp.ClientSession
        self.prefixes: dict[int, str] = {}
        self.default_prefix: str = default_prefix
        self.launch_time = datetime.datetime.now(datetime.timezone.utc)

    async def setup_hook(self):  # overwriting a handler
        print(f"\033[31mLogged in as {self.user}\033[39m")
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        await self.load_extension("jishaku")
        print("Loaded cogs")
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector())
        await self.db.connect()
        # self.insert_bot_info.start()

    @tasks.loop(count=1)
    async def insert_bot_info(self):
        await self.wait_until_ready()
        if not self.user:
            return
        await self.db.bots.upsert(
            where={"id": self.user.id},
            data={
                "create": {
                    "id": self.user.id,
                    "name": self.user.name,
                    "prefix": self.default_prefix,
                    "guild_count": len(self.guilds),
                },
                "update": {
                    "guild_count": len(self.guilds),
                    "name": self.user.name,
                    "prefix": self.default_prefix,
                },
            },
        )


# https://mystb.in/PoundJpgQuarter
async def get_prefix(bot: Bot, message: discord.Message):
    if not message.guild or not bot.user:  # check if dm
        return commands.when_mentioned_or(default_prefix)(bot, message)  # return default prefix
    try:
        return commands.when_mentioned_or(bot.prefixes.get(message.guild.id, default_prefix))(bot, message)

    except KeyError:
        # if it's not, pull from the database
        prefix = await bot.db.prefixes.find_many(
            where={"bot_id": bot.user.id, "guild_id": message.guild.id},
        )
        if prefix:  # if it's in the database,
            bot.prefixes.update({message.guild.id: prefix[0].prefix})  # cache it
            return commands.when_mentioned_or(bot.prefixes.get(message.guild.id, default_prefix))(bot, message)

        else:  # if not in the database,
            # insert into the database
            await bot.db.prefixes.create(
                data={
                    "bot_id": bot.user.id,
                    "prefix": default_prefix,
                    "guild_id": message.guild.id,
                },
            )
            bot.prefixes.update({message.guild.id: default_prefix})  # after inserting, cache it
            return commands.when_mentioned_or(bot.prefixes.get(message.guild.id, default_prefix))(bot, message)


if __name__ == "__main__":
    Bot().run(config["TOKEN"], log_handler=handler)
