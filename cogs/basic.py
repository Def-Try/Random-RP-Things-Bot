import inspect
import select
import socket
import random
import subprocess

import discord
from discord.ext import commands
from discord.ext import tasks

from config import CONFIG
from localisation import DEFAULT_LOCALE
from localisation import localise


activities = [
    lambda bot: discord.Game(localise("activities.game.api", DEFAULT_LOCALE)),
    lambda bot: discord.Game(localise("activities.game.discord", DEFAULT_LOCALE)),
    lambda bot: discord.Game(localise("activities.game.you", DEFAULT_LOCALE)),
    lambda bot: discord.Activity(type=discord.ActivityType.listening, name=localise("activities.listen.lofi", DEFAULT_LOCALE)),
    lambda bot: discord.Activity(type=discord.ActivityType.listening, name=localise("activities.listen.archiso", DEFAULT_LOCALE)),
    lambda bot: discord.Activity(type=discord.ActivityType.watching, name=localise("activities.watch.you", DEFAULT_LOCALE)),
    lambda bot: discord.Activity(type=discord.ActivityType.watching, name=localise("activities.watch.xservers", DEFAULT_LOCALE).format(num=len(bot.guilds))),
]


def collect_commands(to_collect):
    to_do_commands = []
    for command in to_collect:
        if isinstance(command, discord.SlashCommandGroup):
            to_do_commands += collect_commands(command.walk_commands())
        else:
            to_do_commands.append(command)
    return to_do_commands


def do_name(ctx, command):
    name = (
        command.name_localizations.get(ctx.interaction.locale, command.name)
        if command.name_localizations
        else command.name
    )
    if command.parent:
        name = do_name(ctx, command.parent) + " " + name
    return name


def do_commands(ctx, cmds):
    string = ""

    cmds = collect_commands(cmds)
    for command in cmds[:5]:
        string += "`" + do_name(ctx, command) + "` - `" + command.name + "`\n"
    if len(cmds[5:]) > 0:
        string += localise(
            "cog.basic.answers.help.hidden", ctx.interaction.locale
        ).format(amount=len(cmds[5:]))
    return string.strip()


def guess_cog(bot, ctx, command):
    command_parts = command.split(" ")

    for _, cog in bot.cogs.items():
        for cmd in collect_commands(cog.walk_commands()):
            if cmd.name == command_parts[0]:
                return cog
            if do_name(ctx, cmd) == " ".join(command_parts):
                return cog


def find_command(bot, ctx, command, cog):
    command_parts = command.split(" ")

    ccommands = []
    if not cog:
        for _, cog_ in bot.cogs.items():
            ccommands += collect_commands(cog_.walk_commands())
    else:
        ccommands += collect_commands(cog.walk_commands())
    for cmd in ccommands:
        if cmd.name == command_parts[0]:
            return cmd
        if do_name(ctx, cmd) == " ".join(command_parts):
            return cmd


class Basic(commands.Cog, name="basic"):
    author = "googer_"

    def __init__(self, bot):
        self.bot = bot

        self.activity.start()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind(("", 41080))
        except:
            self.bot.logger.warning("Failed to bind to monitoring port!")
            return
        self.socket.setblocking(0)
        self.socket.listen()
        self.listen_ping.start()
        self.pinginfo = "AiOBus "
        try:
            subprocess.run("git", capture_output=True)
            self.pinginfo += f"commit {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True).stdout.decode().strip()}"
        except:
            self.pinginfo += "commit unknown"

    @tasks.loop(seconds=0.5)
    async def listen_ping(self):
        ready, _, _ = select.select([self.socket], [], [], 0)
        if not ready:
            return
        try:
            self.socket.settimeout(0.02)
            conn, _ = self.socket.accept()
        except:
            return
        try:
            conn.settimeout(0.02)
            conn.recv(1024)
        except:
            pass
        pinginfo = self.pinginfo
        pinginfo += f"\nloaded cogs:"
        for cog in self.bot.cogs.keys():
            pinginfo += "\n  " + cog
        conn.send(pinginfo.encode())
        conn.close()

    @tasks.loop(seconds=1)
    async def activity(self):
        await self.bot.change_presence(activity=random.choice(activities)(self.bot))

    def cog_unload(self):
        self.activity.cancel()
        try:
            self.listen_ping.cancel()
            self.socket.close()
        except: pass

    @commands.slash_command(
        guild_ids=CONFIG["g_ids"],
        description=localise("cog.basic.commands.help.desc", DEFAULT_LOCALE),
        name_localizations=localise("cog.basic.commands.help.name"),
        description_localizations=localise("cog.basic.commands.help.desc"),
    )
    async def help(
        self,
        ctx: discord.ApplicationContext,
        command: discord.Option(
            str,
            name_localizations=localise("cog.basic.commands.help.options.command.name"),
            description=localise(
                "cog.basic.commands.help.options.command.desc", DEFAULT_LOCALE
            ),
            description_localizations=localise(
                "cog.basic.commands.help.options.command.desc"
            ),
        ) = None,
        cog: discord.Option(
            str,
            name_localizations=localise("cog.basic.commands.help.options.cog.name"),
            description=localise(
                "cog.basic.commands.help.options.cog.desc", DEFAULT_LOCALE
            ),
            description_localizations=localise(
                "cog.basic.commands.help.options.cog.desc"
            ),
        ) = None,
    ):
        if not cog and not command:
            return await self.help_general(ctx)
        if not cog and command:
            return await self.help_command(ctx, None, command)
        if cog and not command:
            return await self.help_cog(ctx, cog)
        if cog and command:
            return await self.help_command(ctx, cog, command)

    async def help_general(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title=localise("cog.basic.answers.help.title", ctx.interaction.locale),
            description=localise(
                "cog.basic.answers.help.desc", ctx.interaction.locale
            ).format(mention=self.bot.user.mention),
        )

        for name, cog in self.bot.cogs.items():
            embed.add_field(
                name=f"Cog `{name}` - "
                + localise(
                    f"cog.{cog.qualified_name}.info.brief", ctx.interaction.locale
                ),
                value=do_commands(ctx, cog.get_commands()),
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)

    async def help_error(self, ctx: discord.ApplicationContext, error):
        embed = discord.Embed(
            title=localise("cog.basic.answers.help.title", ctx.interaction.locale),
            description=localise(
                "cog.basic.answers.help.error." + error, ctx.interaction.locale
            ),
            color=discord.Color.red(),
        )
        await ctx.respond(embed=embed, ephemeral=True)

    async def help_command(self, ctx: discord.ApplicationContext, cog, command):
        if isinstance(cog, str):
            if not cog in self.bot.cogs.keys():
                await self.help_error(ctx, "unknown_cog")
                return
            cog = self.bot.cogs[cog]

        command = find_command(self.bot, ctx, command, cog)
        if not command:
            await self.help_error(ctx, "unknown_command")
            return
        command_name = do_name(ctx, command)
        embed = discord.Embed(
            title=localise("cog.basic.answers.help.title", ctx.interaction.locale),
            description=localise(
                "cog.basic.answers.help.command", ctx.interaction.locale
            ).format(command=command_name),
        )
        desc = (
            command.description_localizations.get(
                ctx.interaction.locale,
                command.description_localizations.get(
                    DEFAULT_LOCALE, command.description
                ),
            )
            if command.description_localizations
            else command.description
        )
        embed.add_field(
            name=localise(
                "cog.basic.answers.help.elements.desc", ctx.interaction.locale
            ),
            value=desc,
            inline=False,
        )
        embed.add_field(
            name=localise(
                "cog.basic.answers.help.elements.cog", ctx.interaction.locale
            ),
            value=(
                dict([tuple(reversed(i)) for i in self.bot.cogs.items()])[command.cog]
            ),
            inline=False,
        )

        sig = inspect.signature(command.callback)

        parameters = ""

        for parameter in [
            i[1] for i in list(sig.parameters.items())[(2 if command.cog else 1) :]
        ]:
            parameters += "`"
            parameters += (
                "["
                if parameter.default
                or (
                    parameter.annotation
                    and isinstance(parameter.annotation, discord.Option)
                    and not parameter.annotation.required
                )
                else "<"
            )
            parameters += (
                parameter.name
                if not isinstance(parameter.annotation, discord.Option)
                or not parameter.annotation
                or (
                    not parameter.annotation.name
                    and not parameter.annotation.name_localizations
                )
                else (
                    parameter.annotation.name
                    if isinstance(parameter.annotation, discord.Option)
                    and not parameter.annotation.name_localizations
                    else parameter.annotation.name_localizations.get(
                        ctx.interaction.locale, parameter.annotation.name
                    )
                )
            )
            parameters += (
                "]"
                if parameter.default
                or (
                    parameter.annotation
                    and isinstance(parameter.annotation, discord.Option)
                    and not parameter.annotation.required
                )
                else ">"
            )
            parameters += "` "
        parameters = parameters.strip()
        embed.add_field(
            name=localise(
                "cog.basic.answers.help.elements.parameters", ctx.interaction.locale
            ),
            value=f"`/{command_name}` " + parameters,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    async def help_cog(self, ctx: discord.ApplicationContext, cog):
        if not cog in self.bot.cogs.keys():
            await self.help_error(ctx, "unknown_cog")
            return
        cog_name = cog
        cog = self.bot.cogs[cog]
        embed = discord.Embed(
            title=localise("cog.basic.answers.help.title", ctx.interaction.locale),
            description=localise(f"cog.{cog_name}.info.desc", ctx.interaction.locale),
        )

        embed.add_field(name="Author", value="`" + cog.author + "`", inline=False)
        embed.add_field(
            name="Commands", value=do_commands(ctx, cog.get_commands()), inline=False
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.slash_command(
        guild_ids=CONFIG["g_ids"],
        description=localise("cog.basic.commands.ping.desc", DEFAULT_LOCALE),
        name_localizations=localise("cog.basic.commands.ping.name"),
        description_localizations=localise("cog.basic.commands.ping.desc"),
    )
    async def ping(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title=localise("cog.basic.answers.ping.title", ctx.interaction.locale),
            description=localise("cog.basic.answers.ping.desc", ctx.interaction.locale),
        )
        embed.add_field(
            name=localise("cog.basic.answers.ping.dwpl", ctx.interaction.locale),
            value=f"{round(self.bot.latency*1000, 2)}"
            f"{localise('cog.basic.answers.ping.unit', ctx.interaction.locale)}",
            inline=False,
        )

        await ctx.respond(embed=embed)

    @commands.slash_command(
        guild_ids=CONFIG["g_ids"],
        description=localise("cog.basic.commands.reload_cogs.desc", DEFAULT_LOCALE),
        name_localizations=localise("cog.basic.commands.reload_cogs.name"),
        description_localizations=localise("cog.basic.commands.reload_cogs.desc"),
    )
    @commands.is_owner()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        msg = await ctx.respond(
            localise(
                "cog.basic.answers.reload_cogs.in_progress", ctx.interaction.locale
            ),
            ephemeral=True,
        )
        failed_to_reload, ok_reload, timings = self.bot.reload_cogs(self.bot)
        embed = discord.Embed(
            title=localise(
                "cog.basic.answers.reload_cogs.title", ctx.interaction.locale
            ),
            description=localise(
                "cog.basic.answers.reload_cogs.description", ctx.interaction.locale
            ).format(errored=len(failed_to_reload), success=len(ok_reload)),
            color=discord.Colour.blurple(),
        )
        for cog in failed_to_reload:
            embed.add_field(
                name=localise(
                    "cog.basic.answers.reload_cogs.cog.name", ctx.interaction.locale
                ).format(
                    status=localise(
                        "cog.basic.answers.reload_cogs.cog.error",
                        ctx.interaction.locale,
                    ),
                    name=cog,
                ),
                value=localise(
                    "cog.basic.answers.reload_cogs.cog.desc", ctx.interaction.locale
                ).format(
                    unload=timings["unload"].get(cog, "undefined"),
                    load=timings["load"].get(cog, "undefined"),
                ),
                inline=False,
            )
        for cog in ok_reload:
            embed.add_field(
                name=localise(
                    "cog.basic.answers.reload_cogs.cog.name", ctx.interaction.locale
                ).format(
                    status=localise(
                        "cog.basic.answers.reload_cogs.cog.ok", ctx.interaction.locale
                    ),
                    name=cog,
                ),
                value=localise(
                    "cog.basic.answers.reload_cogs.cog.desc", ctx.interaction.locale
                ).format(
                    unload=timings["unload"].get(cog, "undefined"),
                    load=timings["load"].get(cog, "undefined"),
                ),
                inline=False,
            )
        await msg.edit_original_response(content="", embed=embed)


def setup(bot):
    bot.add_cog(Basic(bot))
