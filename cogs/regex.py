from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Callable, Self, Sized

import discord
import toml
from discord import app_commands
from discord.ext import commands
from more_itertools import constrained_batches

if TYPE_CHECKING:
    from main import Bot

tracks: dict[int, list[str]] = {}
# a list of chracters that have '-' in there name, for exmple:
# 'Sky Striker Ace - Roze'
#                 ^
EXCLUSION: list[str] = toml.load("config.toml")["exclusion_list"]


# +2 for ' $'
def get_len(item: Sized) -> int:
    return len(item) + 2


def encode_exclusions(text: str) -> str:
    for i in EXCLUSION:
        text = text.replace(i, i.replace("-", "&45;"))
    return text


def decode_exclusions(text: str) -> str:
    for i in EXCLUSION:
        text = text.replace(i.replace("-", "&45;"), i)
    return text


regex_pattern = re.compile(
    r"^#\d+ - | [=\-·\|💞🚫] .*|[\u200b❌⭐🔐✅]| \d+ ka|\(Soulkeys: \d+\)| \(#[\da-f]{6}\)|Top 1\d value: \d+|"
    r"AVG: \d+|<?:kakera:(\d+)?>?|Total value: \d+|\d+ \$wa, \d+ \$ha, \d+ \$wg, \d+ \$hg|^.+ - \d+\/\d+",
    flags=re.M,
)


def regex(content: str) -> list[str]:
    content = re.sub(r"\*.*\*\n\n", "", content, flags=re.M | re.DOTALL)
    encoded = encode_exclusions(content.replace("*", ""))
    post_regex = regex_pattern.sub("", encoded)
    decoded = decode_exclusions(post_regex)
    return [i.strip() for i in decoded.splitlines() if i != ""]


def remove_sl_regex(content: str) -> list[str]:
    soulmate_list: list[str] = [line for line in content.splitlines() if re.search(r"\(Soulkeys: (\*\*)?\d{2,}", line)]
    return regex("\n".join(soulmate_list))


def pin_regex(content: str) -> list[str]:
    return re.findall(r"(?<=:)pin\d+(?=:)|(?<=<:unkn:\d{18}> · )pin\d+", content, flags=re.M)


def dl_regex(content: str) -> list[str]:
    dl = re.sub(
        r"\d+ disabled \([\d$whag ,]+\)|.+\(\$toggleirl\)|.+\(\$togglewestern\)| ⚠ ",
        "",
        content.replace("*", ""),
        flags=re.M,
    )
    dl = re.findall(r".+(?= \()", dl, re.M)
    return list(filter(None, dl))


clean_notes_pattern = re.compile(
    r"^#\d+ - | ? 💞 => .+?(?= \|)| 🚫 \$.*| \· \(\$.*|[\u200b]| \d+ ka|\(Soulkeys: \d+\)| \(#[\da-f]{6}\)|Top 15"
    r" value: \d+|"
    r"AVG: \d+||Total value: \d+|\d+ \$wa, \d+ \$ha, \d+ \$wg, \d+ \$hg|^.+ - \d+\/\d+",
    flags=re.M,
)


def note_regex(content: str) -> list[str]:
    notes: dict[str, list[str]] = {}
    lines = re.findall(r"(.*) \| (.*)", clean_notes_pattern.sub("", content.replace("*", "")), re.M)
    for name, note in lines:
        notes.setdefault(note, []).append(name)

    notes_list: list[str] = []
    for note, name in notes.items():
        names: list[tuple[str]] = list(constrained_batches(name, 1900, get_len=get_len))
        notes_list.extend(f"```$n {' $'.join(i)} ${note}```" for i in names)
    return notes_list


def image_regex(content: str) -> list[str]:
    ai: dict[str, list[str]] = {}
    for line in content.replace("*", "").splitlines():
        name, image = re.findall(r".+[^*\r\n]+(?= - https)|(?<= - )https:.+", line, re.M)
        ai.setdefault(name, []).append(image)

    ail: list[str] = []
    for name, images in ai.items():
        images_batches: list[tuple[str]] = list(constrained_batches(images, 1920, get_len=get_len))
        ail.extend(f"```$ai {name} ${' $'.join(batch)}```" for batch in images_batches)
    return ail


clean_ec_pattern = re.compile(
    r"^#\d+ - |\s+?[=\-·\|💞🚫].+?(?= \(#)|[\u200b❌⭐🔐✅]| \d+ ka|\(Soulkeys: \d+\)|Top 15 value: \d+|"
    r"AVG: \d+|<?:kakera:(\d+)?>?|Total value: \d+|\d+ \$wa, \d+ \$ha, \d+ \$wg, \d+ \$hg|^.+ - \d+\/\d+",
    flags=re.M,
)


def ec_regex(content: str) -> list[str]:
    lines = re.findall(r"(.*) \(\#(.*)\)", clean_ec_pattern.sub("", content.replace("*", "")), re.M)
    ec: dict[str, list[str]] = {}
    for character, embed_color in lines:
        ec.setdefault(embed_color, []).append(character)

    ec_list: list[str] = []
    for embed_color, character in ec.items():
        characters: list[tuple[str]] = list(constrained_batches(character, 2000, get_len=get_len))
        ec_list.extend(f"```$ec {' $'.join(i)} $ #{embed_color}```" for i in characters)
    return ec_list


class Regex(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(app_commands.ContextMenu(name="regex", callback=self.context_menu_callback))

    async def context_menu_callback(self, interaction: discord.Interaction, message: discord.Message) -> None:
        if message.id in tracks:
            await interaction.response.send_message("that message has already been replied to", ephemeral=True)
            return
        if message.embeds and message.embeds[0].description:
            tracks.update({message.id: [message.embeds[0].description]})
            view = RowButtons(message.id, regex_type=regex)
            await interaction.response.send_message(view=view)
            view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        embeds = after.embeds
        if before.id in tracks and embeds and embeds[0].description and embeds[0].description not in tracks[before.id]:
            tracks[before.id].append(embeds[0].description)

    @commands.group(invoke_without_command=True)
    async def regex(self, ctx: commands.Context[Bot], *, characters: str | None) -> None:
        """
        Generate a `$` separated list of characters for use with other mudae commands.
        Can be used by replying to a mudae embed or directly passing in a list of characters.

        When replying to an embed:
        Syntax: `regex`

        Else:
        Syntax: `regex <character list>`
        * One character per line (ideally copied from mudae)
        """

        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            if msg_id in tracks:
                await ctx.reply("that message has already been replied to")
                return
            tracks.update({msg_id: [reply.resolved.embeds[0].description]})
            view = RowButtons(msg_id, regex_type=regex)
            view.message = await ctx.send(view=view)
        else:
            if not characters:
                raise commands.MissingRequiredArgument(
                    commands.parameters.Parameter(name="characters", kind=inspect.Parameter.POSITIONAL_ONLY)
                )
            characters = " $".join(regex(characters))
            count = len(characters.split("$"))
            await ctx.send(f"Total number of characters: {count}\n```\n{characters}\n```")

    @regex.command()
    async def pin(self, ctx: commands.Context[Bot], *, pins: str | None) -> None:
        """Generate a list of pins separated by `$`"""
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if reply and isinstance(reply.resolved, discord.Message) and not reply.resolved.embeds:
            content = reply.resolved.content
            await ctx.send(f"```{' $'.join(pin_regex(content))}```")
        elif (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=pin_regex)
            view.message = await ctx.send(view=view)
        else:
            if not pins:
                raise commands.BadArgument("Syntax: `regex pin <pins>`")
            await ctx.send(" $".join(pin_regex(pins)))

    @regex.command()
    async def note(self, ctx: commands.Context[Bot], *, notes: str | None) -> None:
        """
        Generate a list of $n commands that can be used to duplicate or backup notes
        """
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=note_regex)
            view.message = await ctx.send(view=view)
        else:
            if not notes:
                raise commands.BadArgument("Syntax: `regex note <notes>`")
            notes = "".join(note_regex(content=notes))
            await ctx.send(notes)

    @regex.command()
    async def ec(self, ctx: commands.Context[Bot], *, content: str | None) -> None:
        """
        Generate a list of $n commands that can be used to duplicate or backup notes
        """
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=ec_regex)
            view.message = await ctx.send(view=view)
        else:
            if not content:
                raise commands.BadArgument("Syntax: `regex ec <ec>`")
            content = "".join(ec_regex(content))
            await ctx.send(content)

    @regex.command()
    async def wrsl(self, ctx: commands.Context[Bot], *, characters: str | None) -> None:
        """
        Generate a list of $n commands that can be used to duplicate or backup notes
        """
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=remove_sl_regex)
            view.message = await ctx.send(view=view)
        else:
            if not characters:
                raise commands.BadArgument("Syntax: `regex sl <characters>`")
            characters = " $".join(remove_sl_regex(characters))
            if not characters:
                await ctx.send("```````")
                return
            count = len(characters.split("$"))
            await ctx.send(f"Total number of characters: {count}\n```\n{characters}\n```")

    @regex.command()
    async def ail(self, ctx: commands.Context[Bot], *, ail: str | None) -> None:
        """
        Generate a list of $ai commands that can be used to copy or backup custom images
        """
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=image_regex)
            view.message = await ctx.send(view=view)
        else:
            if not ail:
                raise commands.BadArgument("Syntax: `regex ail <list>`")
            ail = "".join(image_regex(content=ail))
            await ctx.send(ail)

    @regex.command()
    async def dl(self, ctx: commands.Context[Bot], *, bundles: str | None) -> None:
        """
        Generate a list of bundles/series separated by `$`
        """
        reply: discord.MessageReference | discord.DeletedReferencedMessage | None = ctx.message.reference
        if (
            reply
            and isinstance(reply.resolved, discord.Message)
            and reply.resolved.embeds
            and reply.resolved.embeds[0].description
        ):
            msg_id = reply.resolved.id
            description = reply.resolved.embeds[0].description
            if msg_id not in tracks:
                tracks.update({msg_id: [description]})
            view = RowButtons(msg_id, regex_type=dl_regex)
            view.message = await ctx.send(view=view)
        else:
            if not bundles:
                raise commands.MissingRequiredArgument(
                    commands.parameters.Parameter(name="bundles", kind=inspect.Parameter.POSITIONAL_ONLY)
                )
            dls = dl_regex(bundles)
            dl = " $".join(list(filter(None, dls)))
            await ctx.send(f"Total number bundles: {len(dls)}\n```{dl}```")


class CharacterLimitModal(discord.ui.Modal, title="Set Character Limit"):
    page: discord.ui.TextInput[Self] = discord.ui.TextInput(
        label="Maximum Number of Characters",
        placeholder="Enter a number between 1 and 8100, 0 for no limit",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        self.stop()


class RowButtons(discord.ui.View):
    def __init__(self, msg_id: int, regex_type: Callable[[str], list[str]]) -> None:
        self.max_character_count = None
        self.message: discord.InteractionMessage | discord.Message
        self.msg_id = msg_id
        self.msgs: list[str] = tracks[msg_id]
        self.regex_type = regex_type
        self.current_page = -1
        super().__init__(timeout=360)

    async def on_timeout(self) -> None:
        tracks.pop(self.msg_id)
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.message.edit(view=self)
        except discord.errors.NotFound:
            pass

    def characters_pages(self) -> list[tuple[str]]:
        regex_output = self.regex_type("\n".join(self.msgs))
        characters = regex_output[: self.max_character_count] if self.max_character_count else regex_output
        characters_pages: list[tuple[str]] = list(constrained_batches(characters, 1960, get_len=get_len))
        return characters_pages

    def format_embed(self, characters_pages: list[tuple[str]]) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.brand_red())
        description = characters_pages[self.current_page]
        embed.description = f"Total number of characters: {len(description)}\n```\n{' $'.join(description)}\n```"

        if self.regex_type == pin_regex:
            embed.description.replace("characters", "Pins")

        elif self.regex_type in [note_regex, image_regex, ec_regex]:
            embed.description = "".join(description)

        elif self.regex_type == dl_regex:
            embed.description = f"Total number bundles: {len(description)}\n```{' $'.join(description)}```"

        embed.set_footer(text=f"Page {self.current_page + 1} / {len(characters_pages)}")
        return embed

    @discord.ui.button(emoji="<:RemLeft:1052054214634913882>", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        characters_pages = self.characters_pages()
        if self.current_page <= 0:
            return await interaction.response.send_message("list index out of range", ephemeral=True)
        self.current_page -= 1
        await interaction.response.edit_message(embed=self.format_embed(characters_pages))

    @discord.ui.button(emoji="<:RamRight:1052054203901673482>", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        characters_pages = self.characters_pages()
        if self.current_page >= len(characters_pages) - 1:
            return await interaction.response.send_message("list index out of range", ephemeral=True)
        self.current_page += 1
        await interaction.response.edit_message(embed=self.format_embed(characters_pages))

    @discord.ui.button(label="DM", emoji="\U0001f4eb", style=discord.ButtonStyle.secondary)
    async def dm(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        button.disabled = True
        if interaction.message:
            await interaction.message.edit(view=self)
        characters_pages = self.characters_pages()
        pages = [f"```{' $'.join(characters)}```" for characters in characters_pages]

        await interaction.response.send_message(f"sending {len(characters_pages)} messages", ephemeral=True)
        if self.regex_type == pin_regex:
            pages = [f"```{' '.join(pins)}```" for pins in characters_pages]

        elif self.regex_type in [note_regex, image_regex, ec_regex]:
            pages = ["".join(output) for output in characters_pages]

        for page in pages:
            await interaction.user.send(page)
        button.disabled = False
        if interaction.message:
            await interaction.message.edit(view=self)

    @discord.ui.button(label="Character Limit", style=discord.ButtonStyle.secondary, row=1)
    async def character_limit(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        modal = CharacterLimitModal()
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()

        if timed_out:
            await interaction.followup.send("Took too long", ephemeral=True)
            return

        value = int(modal.page.value)
        self.max_character_count = None if value == 0 else value
        self.current_page = 0
        await interaction.edit_original_response(embed=self.format_embed(self.characters_pages()))

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        tracks.pop(self.msg_id)
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Regex(bot))
