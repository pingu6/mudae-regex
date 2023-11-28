from __future__ import annotations

import sys
import traceback
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import Bot


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[Bot], error: commands.CommandError) -> None:
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog and cog._get_overridden_method(cog.cog_command_error) is not None:
            return

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f"{ctx.command} has been disabled.")

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f"{ctx.command} can not be used in Private Messages.")
            except discord.HTTPException:
                pass
        elif isinstance(error, commands.MissingPermissions):
            try:
                if len(error.missing_permissions) > 1:
                    missing = ", ".join(list(error.missing_permissions))
                else:
                    missing = error.missing_permissions[0]
                await ctx.send(f"Command restricted to admins (Discord permissions: {missing})")
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)

        elif isinstance(error, commands.NotOwner):
            await ctx.send("https://http.cat/403")

        elif isinstance(error, (commands.BadArgument, commands.CommandOnCooldown)):
            await ctx.send(str(error))

        else:
            # All other Errors not returned come here. And we can just print the default TraceBack.
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


async def setup(bot: Bot) -> None:
    await bot.add_cog(CommandErrorHandler(bot))
