# cogs / char_value.py
from __future__ import annotations

import asyncio
import inspect
import math
import re
from io import BytesIO
from typing import TYPE_CHECKING, Optional, Self

import discord
import fast_colorthief
from aiohttp import FormData
from colormap import rgb2hex
from discord import app_commands, ui
from discord.ext import commands, menus
from discord.ext.commands import Greedy
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from main import Bot

font = ImageFont.truetype(
    "Assets/fonts/JetBrainsMono/JetBrainsMono-ExtraBold.ttf",
    size=16,
    layout_engine=ImageFont.Layout.BASIC,
)


def get_images_url(text: str) -> list[str]:
    return re.findall(r"https?://.*?\.(?:jpg|gif|png|webp)", text)


def char_info_regex(char_info: dict[str, int], description: str) -> dict[str, int]:
    claim = re.compile(r"Claim rank: #(.*)$", flags=re.MULTILINE | re.IGNORECASE)
    like = re.compile(r"Like rank: #(.*)$", flags=re.MULTILINE | re.IGNORECASE)
    key = re.compile(r"key:.*\((.*)\)", flags=re.MULTILINE)
    if claim.search(description):
        char_info["claim_rank"] = int(claim.findall(description)[0])
    if like.search(description):
        char_info["like_rank"] = int(like.findall(description)[0])
    if key.search(description):
        char_info["keys"] = int(key.findall(description)[0])
    return char_info


# hhttps://codepen.io/ifailatgithub/pen/mdrJdgb (outdated)
# https://codepen.io/xr_/pen/oNaOxxB (updated fork)
def get_value(claim_rank: int, like_rank: int, claimed_chars: int, keys: int) -> discord.Embed:
    def keys_multiplier():
        if keys < 1:
            return 1
        elif 1 <= keys < 3:
            return 1 + 0.1 * (keys - 1)
        elif 3 <= keys < 6:
            return 1.1 + 0.1 * (keys - 3)
        elif 6 <= keys < 10:
            return 1.3 + 0.1 * (keys - 6)
        else:
            return 1.6 + 0.05 * (keys - 10)

    def keys_bonus_value() -> int:
        if 10 >= keys > 20:
            return 15 * (keys // 5 - 1)
        elif 20 >= keys > 35:
            return 30 + 10 * (keys // 5 - 3)
        elif 35 >= keys > 60:
            return 60 + 5 * (keys // 5 - 6)
        elif 60 >= keys > 300:
            return 100 + 5 * (keys // 10 - 8)
        elif keys >= 300:
            return 210
        else:
            return 0

    avg_rank = (claim_rank + like_rank) / 2
    claim_multiplier = 1 + claimed_chars / 5500
    base_value = math.floor((25000 * (avg_rank + 70) ** -0.75 + 20 + keys_bonus_value()) * claim_multiplier + 0.5)
    kakera_value = math.floor(base_value * keys_multiplier() + 0.5)
    embed = discord.Embed(color=discord.Color.brand_red())
    description = f"Base Value: {base_value}\nKey Multiplier: {keys_multiplier():.2f}\nKakera Value: {kakera_value}"
    embed.description = f"""
    Claim Rank: {claim_rank}
    Like Rank: {like_rank}
    No. of Claimed Characters: {claimed_chars}
    No. of Keys: {keys} <:chaoskey:1070283460373139557>
    ```\n{description}\n```
    """
    embed.set_footer(text="Value calculations interpolated by Okami and LilJamJam")
    return embed


def processing(image: BytesIO):
    palette = [rgb2hex(r, g, b) for r, g, b in fast_colorthief.get_palette(image, color_count=25, quality=1)]

    n = len(palette)
    cols = 4
    rows = ((n - 1) // cols) + 1
    cell_height = 30
    cell_width = 170
    img_height = cell_height * rows
    img_width = cell_width * cols

    i = Image.new("RGBA", (img_width, img_height))
    a = ImageDraw.Draw(i)

    for index, color in enumerate(palette):
        y0 = cell_height * (index // cols)
        y1 = y0 + cell_height
        x0 = cell_width * (index % cols)
        x1 = x0 + (cell_width / 4)

        a.rectangle((x0, y0, x1, y1), fill=color, outline="black")
        a.text((x1 + 1, y0 + 10), color, fill="white", font=font)
    palette_png = BytesIO()
    i.save(palette_png, "png")
    return palette, palette_png


class ImgChestFlags(commands.FlagConverter):
    title: str | None = None
    anonymous: bool = False
    nsfw: bool = False


class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.add_command(
            app_commands.ContextMenu(
                name="Kakera Value Calculator",
                callback=self.KakeraValueCalculatorCallback,
            )
        )

    async def KakeraValueCalculatorCallback(self, interaction: discord.Interaction, message: discord.Message):
        if message.embeds and message.embeds[0].description:
            char_info = {"claim_rank": 1, "like_rank": 1, "claimed_chars": 0, "keys": 0}
            embed = get_value(**char_info_regex(char_info, message.embeds[0].description))
            view = CharInfoView(char_info)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()

    @commands.command()
    async def value(
        self,
        ctx: commands.Context[Bot],
        claim_rank: int = 1,
        like_rank: int = 1,
        claimed_chars: int = 0,
        keys: int = 0,
    ):
        """Calculate Kakera Value"""
        char_info = {
            "claim_rank": claim_rank,
            "like_rank": like_rank,
            "claimed_chars": claimed_chars,
            "keys": keys,
        }
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            embed = get_value(**char_info_regex(char_info, reply.resolved.embeds[0].description))
        else:
            embed = get_value(**char_info)

        view = CharInfoView(char_info)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(aliases=["upload"])
    @commands.cooldown(60, 60)
    async def imgchest(self, ctx: commands.Context[Bot], attachments: Greedy[discord.Attachment]):
        """Upload images to <https://imgchest.com>

        __Notes__
        - Allowed file types: png, jpeg, jpg, gif, webp
        - Maximum file size: 30MB
        """
        checked_attachments = [
            attachment
            for attachment in attachments
            if attachment.size <= 3e7 and attachment.url.lower().endswith(("png", "jpeg", "jpg", "gif", "webp"))
        ]
        if not checked_attachments:
            raise commands.MissingRequiredArgument(
                commands.parameters.Parameter(name="attachments", kind=inspect.Parameter.POSITIONAL_ONLY)
            )
        elif sum(attachment.size for attachment in checked_attachments) > 99e6:
            return await ctx.send("Total attachments size must be less than 99MB")

        data = FormData()
        data.add_field("anonymous", "1")
        data.add_field("nsfw", "true")
        for attachment in checked_attachments:
            data.add_field(
                "images[]",
                await attachment.read(),
                filename=attachment.filename,
                content_type=attachment.content_type,
            )

        async with ctx.bot.session.post(
            url="https://api.imgchest.com/v1/post",
            headers={"Authorization": f"Bearer {ctx.bot.config['imgchest_key']}"},
            data=data,
        ) as response:
            if response.status != 200:
                return await ctx.send(await response.text())

            json = await response.json()

        links = "\n".join([image["link"] for image in json["data"]["images"]])
        await ctx.send(
            f"https://imgchest.com/p/{json['data']['id']}\n\n{links}",
            suppress_embeds=True,
        )

    @commands.command()
    async def limit(self, ctx: commands.Context[Bot], limit: int, *, args: str):
        """limit the number of given characters"""
        if args:
            characters = [i.strip() for i in args.split("$")]
            await ctx.send(f"```\n{' $'.join(characters[:limit])}\n```")

    @commands.hybrid_command(name="page")
    async def page(self, ctx: commands.Context[Bot], from_page: int, to_page: int):
        """Generate a list of pages"""
        msg = " ".join([str(i) for i in range(from_page, to_page + 1)])
        if len(msg) > 1995:
            await ctx.send(f"message to long({len(msg)} character )")
        else:
            await ctx.send(f"page {msg}")

    @commands.command()
    async def ec(
        self,
        ctx: commands.Context[Bot],
        attachments: Greedy[discord.Attachment],
        *,
        args: Optional[str],
    ):
        """get most 25 dominant colors in an image using median cut algorithm"""

        urls = get_images_url(args) if args else None
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if reply and isinstance(reply.resolved, discord.Message):
            urls = get_images_url(reply.resolved.content)
            if reply.resolved.attachments:
                urls = [attachment.url for attachment in reply.resolved.attachments]
            elif reply.resolved.embeds and reply.resolved.embeds[0].image:
                urls = [reply.resolved.embeds[0].image.url]
            elif reply.resolved.embeds and reply.resolved.embeds[0].description:
                urls = get_images_url(reply.resolved.embeds[0].description)

        elif attachments:
            urls = [attachment.url for attachment in attachments]

        if not urls:
            return await ctx.send("no image found")

        async def get(url: str):
            async with ctx.bot.session.get(url) as response:
                if response.status == 200 and response.url.name != "removed.png":
                    return (url, BytesIO(await response.read()))

        entries: list[tuple[str, BytesIO]] = await asyncio.gather(*[get(url) for url in urls if url])
        if not entries:
            return await ctx.send("invalid url")
        formatter = MySource(entries, 1)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)


class CharInfoModal(ui.Modal, title="Update Values"):
    claim_rank: ui.TextInput[Self] = ui.TextInput(label="Claim Rank")
    like_rank: ui.TextInput[Self] = ui.TextInput(label="Like Rank")
    claimed_chars: ui.TextInput[Self] = ui.TextInput(label="Number of Claimed Characters")
    keys: ui.TextInput[Self] = ui.TextInput(label="Number of Keys")

    def __init__(self, char_info: dict[str, int]) -> None:
        super().__init__()
        self.claim_rank.default = str(char_info["claim_rank"])
        self.like_rank.default = str(char_info["like_rank"])
        self.claimed_chars.default = str(char_info["claimed_chars"])
        self.keys.default = str(char_info["keys"])

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        self.stop()


class CharInfoView(ui.View):
    def __init__(self, char_info: dict[str, int]):
        self.char_info = char_info
        self.message: discord.InteractionMessage | discord.Message
        super().__init__()

    @ui.button(label="Update Values", style=discord.ButtonStyle.secondary)
    async def update_values(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        modal = CharInfoModal(self.char_info)
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()
        if timed_out:
            await interaction.followup.send("Took too long", ephemeral=True)
            return
        elif self.is_finished():
            await modal.interaction.response.send_message("Took too long", ephemeral=True)
            return
        self.char_info["claim_rank"] = int(modal.claim_rank.value)
        self.char_info["like_rank"] = int(modal.like_rank.value)
        self.char_info["claimed_chars"] = int(modal.claimed_chars.value)
        self.char_info["keys"] = int(modal.keys.value)
        await interaction.edit_original_response(embed=get_value(**self.char_info))

    @ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def Quit(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            pass


# https://gist.github.com/InterStella0/454cc51e05e60e63b81ea2e8490ef140
class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source: menus.ListPageSource):
        super().__init__(timeout=180)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.palette_png: BytesIO
        self.message: discord.Message

    async def start(
        self,
        ctx: commands.Context[Bot],
        *,
        channel: discord.abc.Messageable | None = None,
        wait: bool = False,
    ):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message: discord.Message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page: int) -> dict[str, str | discord.Embed | discord.ui.View | None]:
        """This method calls ListPageSource.format_page class"""
        value: dict[str, str | discord.Embed | discord.ui.View | None] = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    @ui.button(style=discord.ButtonStyle.secondary, label="Colors", row=2)
    async def colors(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        self.palette_png.seek(0)
        await interaction.response.send_message(
            file=discord.File(fp=self.palette_png, filename="Colors.png"),
            ephemeral=True,
        )

    @ui.button(emoji="<:RemLeft:1052054214634913882>", style=discord.ButtonStyle.secondary, row=2)
    async def before_page(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        await interaction.response.defer()
        if self.current_page == 0:
            self.current_page = self._source.get_max_pages()
        await self.show_checked_page(self.current_page - 1)

    @ui.button(emoji="<:RamRight:1052054203901673482>", style=discord.ButtonStyle.secondary, row=2)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        await interaction.response.defer()
        if self.current_page == self._source.get_max_pages() - 1:
            self.current_page = -1
        await self.show_checked_page(self.current_page + 1)

    @ui.button(style=discord.ButtonStyle.red, label="Quit", row=2)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button[Self]):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class MySource(menus.ListPageSource):
    def __init__(self, entries: list[tuple[str, BytesIO]], per_page: int):
        super().__init__(entries, per_page=per_page)
        self.Dropdown = None

    async def format_page(self, menu: MyMenuPages, page: tuple[str, BytesIO]):
        url, image_bytes = page
        colors, palette_png = await asyncio.to_thread(processing, image_bytes)
        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_image(url=url)
        options = [discord.SelectOption(label=color) for color in colors]
        if self.Dropdown:
            menu.remove_item(self.Dropdown)

        self.Dropdown = Dropdown(options, embed)
        menu.add_item(self.Dropdown)
        menu.palette_png = palette_png
        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f"Page {menu.current_page + 1} / {maximum}"
            embed.set_footer(text=footer)

        return embed


class Dropdown(discord.ui.Select[MyMenuPages]):
    def __init__(self, options: list[discord.SelectOption], embed: discord.Embed):
        self.embed = embed
        super().__init__(
            placeholder="Choose a color...",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.embed.color = discord.Color.from_str(self.values[0])
        for option in self.options:
            if option.value == self.values[0]:
                option.default = True
            else:
                option.default = False

        await interaction.response.edit_message(embed=self.embed, view=self.view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
