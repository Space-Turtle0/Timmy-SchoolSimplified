import faulthandler
import json
import logging
import os
import subprocess
import time
import traceback
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path

import chat_exporter
import discord
import pytz
import requests
import sentry_sdk
from discord.commands import Option, permissions
from discord.ext import commands
from discord_sentry_reporting import use_sentry
from dotenv import load_dotenv
from logtail import LogtailHandler
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from core import database
from core.common import (MAIN_ID, TECH_ID, TUT_ID, CheckDB_CC, Emoji,
                         GSuiteVerify, LockButton, Others, bcolors,
                         get_extensions, hexColors, id_generator)
from utils.bots.CoreBot.cogs.tictactoe import TicTacToe, TicTacToeButton
from utils.events.VerificationStaff import VerifyButton

LogTail = LogtailHandler(source_token=os.getenv("LOGTAIL"))
load_dotenv()
faulthandler.enable()

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
logger.addHandler(LogTail)

logger.warning("Started Timmy");
print("Starting Timmy...")


class Timmy(commands.Bot):
    async def is_owner(self, user: discord.User):
        adminIDs = []

        query = database.Administrators.select().where(
            database.Administrators.TierLevel >= 3
        )
        for admin in query:
            adminIDs.append(admin.discordID)

        if user.id in adminIDs:
            return True

        return await super().is_owner(user)


bot = Timmy(
    command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
    intents=discord.Intents.all(),
    case_insensitive=True,
    activity=discord.Activity(
        type=discord.ActivityType.watching, name="+help | timmy.schoolsimplified.org"
    ),
)
bot.remove_command("help")


class Me:
    Timmy = Timmy
    publicCH = [
        MAIN_ID.cat_casual,
        MAIN_ID.cat_community,
        MAIN_ID.cat_lounge,
        MAIN_ID.cat_events,
        MAIN_ID.cat_voice,
    ]
    TechGuild = TECH_ID.g_tech
    TracebackChannel = TECH_ID.ch_tracebacks


if os.getenv("DSN_SENTRY") is not None:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    use_sentry(
        bot,  # Traceback tracking, DO NOT MODIFY THIS
        dsn=os.getenv("DSN_SENTRY"),
        traces_sample_rate=1.0,
        integrations=[FlaskIntegration(), sentry_logging],
    )

# Start Check
UpQ = database.Uptime.select().where(database.Uptime.id == 1)
CIQ = database.CheckInformation.select().where(database.CheckInformation.id == 1)
BTE = database.BaseTickerInfo.select().where(database.BaseTickerInfo.id == 1)

if not UpQ.exists():
    database.Uptime.create(UpStart="1")
    print("Created Uptime Entry.")

if not CIQ.exists():
    database.CheckInformation.create(
        MasterMaintenance=False,
        guildNone=False,
        externalGuild=True,
        ModRoleBypass=True,
        ruleBypass=True,
        publicCategories=True,
        elseSituation=True,
        PersistantChange=False,
    )
    print("Created CheckInformation Entry.")

if len(database.Administrators) == 0:
    for person in bot.owner_ids:
        database.Administrators.create(discordID=person, TierLevel=4)
        print("Created Administrator Entry.")
    database.Administrators.create(discordID=409152798609899530, TierLevel=4)

if not BTE.exists():
    database.BaseTickerInfo.create(
        counter=0,
    )
    print("Created BaseTickerInfo Entry.")

database.db.connect(reuse_if_open=True)
q: database.Uptime = database.Uptime.select().where(database.Uptime.id == 1).get()
q.UpStart = time.time()
q.save()

query: database.CheckInformation = (
    database.CheckInformation.select().where(database.CheckInformation.id == 1).get()
)
query.PersistantChange = False
query.save()
database.db.close()


@bot.slash_command(description="Play a game of TicTacToe with someone!")
async def tictactoe(ctx, user: Option(discord.Member, "Enter an opponent you want")):
    if ctx.channel.id != MAIN_ID.ch_commands:
        return await ctx.respond(
            f"{ctx.author.mention}\nMove to <#{MAIN_ID.ch_commands}> to play Tic Tac Toe!",
            ephemeral=True,
        )
    if user is None:
        return await ctx.respond("lonely :(, sorry but you need a person to play against!")
    elif user == bot.user:
        return await ctx.respond("i'm good.")
    elif user == ctx.author:
        return await ctx.respond(
            "lonely :(, sorry but you need an actual person to play against, not yourself!"
        )

    await ctx.respond(
        f"Tic Tac Toe: {ctx.author.mention} goes first",
        view=TicTacToe(ctx.author, user),
    )


@bot.user_command(name="Are they short?")
async def short(ctx, member: discord.Member):
    if (
            member.id == 736765405728735232
            or member.id == 518581570152693771
            or member.id == 544724467709116457
    ):
        await ctx.respond(f"{member.mention} is short!")
    else:
        await ctx.respond(f"{member.mention} is tall!")


@bot.slash_command(description="Check's if a user is short!")
async def short_detector(
        ctx, member: Option(discord.Member, "Enter a user you want to check!")
):
    if member.id in [736765405728735232, 518581570152693771, 544724467709116457]:
        await ctx.respond(f"{member.mention} is short!")
    else:
        await ctx.respond(f"{member.mention} is tall!")


@bot.user_command(name="Play TicTacToe with them!")
async def tictactoeCTX(ctx, member: discord.Member):
    if member is None:
        return await ctx.respond("lonely :(, sorry but you need a person to play against!")
    elif member == bot.user:
        return await ctx.respond("i'm good.")
    elif member == ctx.author:
        return await ctx.respond(
            "lonely :(, sorry but you need an actual person to play against, not yourself!"
        )

    await ctx.respond(
        f"Tic Tac Toe: {ctx.author.mention} goes first",
        view=TicTacToe(ctx.author, member),
    )


@bot.slash_command(
    name="schedule",
    description="Create a Tutor Session",
    guild_ids=[MAIN_ID.g_main, TUT_ID.g_tut],
)
@permissions.has_any_role("Tutor")
async def schedule(
        ctx,
        date: Option(str, "Enter a date in MM/DD format. EX: 02/02"),
        time: Option(str, "Enter a time in HH:MM format. EX: 3:00"),
        ampm: Option(str, "AM or PM", choices=["AM", "PM"]),
        student: Option(discord.Member,
                        "Enter the student you'll be tutoring for this session."),
        subject: Option(str, "Tutoring Subject"),
        repeats: Option(bool, "Does your Tutoring Session repeat?"),
):
    embed = discord.Embed(
        title="Schedule Confirmed",
        description="Created session.",
        color=discord.Color.green(),
    )
    now = datetime.now()
    now: datetime = now.astimezone(pytz.timezone("US/Eastern"))
    year = now.strftime("%Y")

    datetimeSession = datetime.strptime(
        f"{date}/{year} {time} {ampm.upper()}", "%m/%d/%Y %I:%M %p"
    )
    datetimeSession = pytz.timezone("America/New_York").localize(datetimeSession)

    if datetimeSession >= now:
        SessionID = await id_generator()

        daterev = datetimeSession.strftime("%m/%d")

        embed.add_field(
            name="Values",
            value=f"**Session ID:** `{SessionID}`\n**Student:** `{student.name}`\n**Tutor:** `{ctx.author.name}`\n**Date:** `{daterev}`\n**Time:** `{time}`\n**Repeat?:** `{repeats}`",
        )
        embed.set_footer(text=f"Subject: {subject}")
        query = database.TutorBot_Sessions.create(
            SessionID=SessionID,
            Date=datetimeSession,
            Time=time,
            StudentID=student.id,
            TutorID=ctx.author.id,
            Repeat=repeats,
            Subject=subject,
            ReminderSet=False,
        )
        query.save()
        await ctx.respond(embed=embed)
    else:
        embed = discord.Embed(
            title="Failed to Generate Session",
            description=f"Unfortunately this session appears to be in the past and Timmy does not support expired sessions.",
            color=discord.Color.red(),
        )
        await ctx.respond(embed=embed)


for ext in get_extensions():
    try:
        bot.load_extension(ext)
    except discord.ExtensionAlreadyLoaded:
        bot.unload_extension(ext)
        bot.load_extension(ext)
    except discord.ExtensionNotFound:
        raise discord.ExtensionNotFound(ext)


@bot.event
async def on_ready():
    now = datetime.now()
    query: database.CheckInformation = (
        database.CheckInformation.select()
            .where(database.CheckInformation.id == 1)
            .get()
    )

    if not query.PersistantChange:
        bot.add_view(LockButton(bot))
        bot.add_view(VerifyButton())
        bot.add_view(GSuiteVerify())
        query.PersistantChange = True
        query.save()

    if not os.getenv("USEREAL"):
        IP = os.getenv("IP")
        databaseField = (
            f"{bcolors.OKGREEN}Selected Database: External ({IP}){bcolors.ENDC}"
        )
    else:
        databaseField = f"{bcolors.FAIL}Selected Database: localhost{bcolors.ENDC}\n{bcolors.WARNING}WARNING: Not recommended to use SQLite.{bcolors.ENDC}"

    try:
        p = subprocess.run(
            "git describe --always",
            shell=True,
            text=True,
            capture_output=True,
            check=True,
        )
        output = p.stdout
    except subprocess.CalledProcessError:
        output = "ERROR"

    # chat_exporter.init_exporter(bot)

    print(
        f"""
    ╭━━┳╮
    ╰╮╭╋╋━━┳━━┳┳╮
    ╱┃┃┃┃┃┃┃┃┃┃┃┃
    ╱╰╯╰┻┻┻┻┻┻╋╮┃
    ╱╱╱╱╱╱╱╱╱╱╰━╯
    
    Bot Account: {bot.user.name} | {bot.user.id}
    {bcolors.OKCYAN}Discord API Wrapper Version: {discord.__version__}{bcolors.ENDC}
    {bcolors.WARNING}TimmyOS Version: {output}{bcolors.ENDC}
    {databaseField}

    {bcolors.OKCYAN}Current Time: {now}{bcolors.ENDC}
    {bcolors.OKGREEN}Cogs, libraries, and views have successfully been initalized.{bcolors.ENDC}
    ==================================================
    {bcolors.WARNING}Statistics{bcolors.ENDC}

    Guilds: {len(bot.guilds)}
    Members: {len(bot.users)}
    """
    )


@bot.check
async def mainModeCheck(ctx: commands.Context):
    MT = discord.utils.get(ctx.guild.roles, name="Moderator")
    VP = discord.utils.get(ctx.guild.roles, name="VP")
    CO = discord.utils.get(ctx.guild.roles, name="CO")
    SS = discord.utils.get(ctx.guild.roles, name="Secret Service")

    blacklistedUsers = []
    for p in database.Blacklist:
        blacklistedUsers.append(p.discordID)

    adminIDs = []
    query = database.Administrators.select().where(
        database.Administrators.TierLevel == 4
    )
    for admin in query:
        adminIDs.append(admin.discordID)

    # Permit 4 Check
    if ctx.author.id in adminIDs:
        return True

    # Maintenance Check
    elif CheckDB_CC.MasterMaintenance:
        embed = discord.Embed(
            title="Master Maintenance ENABLED",
            description=f"{Emoji.deny} The bot is currently unavailable as it is under maintenance, check back later!",
            color=discord.Colour.gold(),
        )
        embed.set_footer(
            text="Need an immediate unlock? Message a Developer or SpaceTurtle#0001"
        )
        await ctx.send(embed=embed)

        return False

    # Blacklist Check
    elif ctx.author.id in blacklistedUsers:
        return False

    # DM Check
    elif ctx.guild is None:
        return CheckDB_CC.guildNone

    # External Server Check
    elif ctx.guild.id != MAIN_ID.g_main:
        return CheckDB_CC.externalGuild

    # Mod Role Check
    elif (
            MT in ctx.author.roles
            or VP in ctx.author.roles
            or CO in ctx.author.roles
            or SS in ctx.author.roles
    ):
        return CheckDB_CC.ModRoleBypass

    # Rule Command Check
    elif ctx.command.name == "rule":
        return CheckDB_CC.ruleBypass

    # Public Category Check
    elif ctx.channel.category_id in Me.publicCH:
        return CheckDB_CC.publicCategories

    # Else...
    else:
        return CheckDB_CC.elseSituation

@bot.before_invoke
async def before_invoke(ctx: commands.Context):
    sentry_sdk.set_user(None)
    sentry_sdk.set_user({"id": ctx.author.id, "username": ctx.author.name})
    sentry_sdk.set_tag("username", f"{ctx.author.name}#{ctx.author.discriminator}")
    if ctx.command == None:
        sentry_sdk.set_context("user", {
        "name": ctx.author.name,
        "id": ctx.author.id,
        "command": ctx.command.name,
        "guild": ctx.guild.name,
        "guild_id": ctx.guild.id,
        "channel": ctx.channel.name,
        "channel_id": ctx.channel.id,
    })
    else:
        sentry_sdk.set_context("user", {
            "name": ctx.author.name,
            "id": ctx.author.id,
            "command": "Unknown",
            "guild": ctx.guild.name,
            "guild_id": ctx.guild.id,
            "channel": ctx.channel.name,
            "channel_id": ctx.channel.id,
        })


@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    ctx: discord.ApplicationContext = await bot.get_application_context(interaction)
    pass  # TODO implement something here


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    tb = error.__traceback__
    etype = type(error)
    exception = traceback.format_exception(etype, error, tb, chain=True)
    exception_msg = ""
    for line in exception:
        exception_msg += line

    error = getattr(error, "original", error)
    if ctx.command is not None:
        if ctx.command.name == "rule":
            return "No Rule..."

    if isinstance(error, (commands.CheckFailure, commands.CheckAnyFailure)):
        return

    if hasattr(ctx.command, "on_error"):
        return

    elif isinstance(error, (commands.CommandNotFound, commands.errors.CommandNotFound)):
        cmd = ctx.invoked_with
        cmds = [cmd.name for cmd in bot.commands]
        matches = get_close_matches(cmd, cmds)
        slash_cmds = [cmd.qualified_name for cmd in bot.application_commands]
        slash_matches = get_close_matches(slash_cmds, cmd)

        if len(matches) > 0:
            return await ctx.send(
                f'Command "{cmd}" not found, maybe you meant "{matches[0]}"?'
            )
        elif len(slash_matches) > 0:
            return await ctx.send(
                f'Command "{cmd}" not found, command: {slash_matches[0]} is now a slash command! '
                f'Please check https://timmy.schoolsimplified.org/#slash-command-port for more updates!'
            )
        else:
            return await ctx.send(
                f'Command "{cmd}" not found, use the help command to know what commands are available. '
                f'Some commands have moved over to slash commands, please check '
                f'https://timmy.schoolsimplified.org/#slash-command-port '
                f'for more updates! '
            )

    elif isinstance(
            error, (commands.MissingRequiredArgument, commands.TooManyArguments)
    ):
        signature = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"

        if ctx.command.name == "schedule":
            em = discord.Embed(
                title="Missing/Extra Required Arguments Passed In!",
                description=f"Looks like you messed up an argument somewhere here!\n\n**Check the "
                            f"following:**\nUsage:\n`{signature}`\n\n-> If you seperated the time and the AM/PM. (Eg; "
                            f"5:00 PM)\n-> If you provided a valid student's ID\n-> If you followed the MM/DD "
                            f"Format.\n-> Keep all the arguments in one word.\n-> If you followed the [documentation "
                            f"for schedule.](https://timmy.schoolsimplified.org/tutorbot#schedule)",
                color=hexColors.red_error,
            )
            em.set_thumbnail(url=Others.error_png)
            em.set_footer(
                text="Consult the Help Command if you are having trouble or call over a Bot Manager!"
            )
            return await ctx.send(embed=em)
        else:
            em = discord.Embed(
                title="Missing/Extra Required Arguments Passed In!",
                description="You have missed one or several arguments in this command"
                            "\n\nUsage:"
                            f"\n`{signature}`",
                color=hexColors.red_error,
            )
            em.set_thumbnail(url=Others.error_png)
            em.set_footer(
                text="Consult the Help Command if you are having trouble or call over a Bot Manager!"
            )
            return await ctx.send(embed=em)

    elif isinstance(
            error,
            (commands.MissingAnyRole,
             commands.MissingRole,
             commands.MissingPermissions,
             commands.errors.MissingAnyRole,
             commands.errors.MissingRole,
             commands.errors.MissingPermissions,
             ),
    ):
        em = discord.Embed(
            title="Invalid Permissions!",
            description="You do not have the associated role in order to successfully invoke this command! Contact an "
                        "administrator/developer if you believe this is invalid.",
            color=hexColors.red_error,
        )
        em.set_thumbnail(url=Others.error_png)
        em.set_footer(
            text="Consult the Help Command if you are having trouble or call over a Bot Manager!"
        )
        await ctx.send(embed=em)
        return

    elif isinstance(error, commands.BadArgument):
        signature = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"
        if ctx.command.name == "schedule":
            em = discord.Embed(
                title="Bad Argument!",
                description=f"Looks like you messed up an argument somewhere here!\n\n**Check the "
                            f"following:**\nUsage:\n`{signature}`\n-> If you seperated the time and the AM/PM. (Eg; "
                            f"5:00 PM)\n-> If you provided a valid student's ID\n-> If you followed the MM/DD "
                            f"Format.\n-> Keep all the arguments in one word.\n-> If you followed the [documentation "
                            f"for schedule.](https://timmy.schoolsimplified.org/tutorbot#schedule)",
                color=hexColors.red_error,
            )
            em.set_thumbnail(url=Others.error_png)
            em.set_footer(
                text="Consult the Help Command if you are having trouble or call over a Bot Manager!"
            )
            return await ctx.send(embed=em)
        else:
            em = discord.Embed(
                title="Bad Argument!",
                description=f"Unable to parse arguments, check what arguments you provided.\n\nUsage:\n`{signature}`",
                color=hexColors.red_error,
            )
            em.set_thumbnail(url=Others.error_png)
            em.set_footer(
                text="Consult the Help Command if you are having trouble or call over a Bot Manager!"
            )
            return await ctx.send(embed=em)

    elif isinstance(
            error, (commands.CommandOnCooldown, commands.errors.CommandOnCooldown)
    ):
        m, s = divmod(error.retry_after, 60)
        h, m = divmod(m, 60)

        msg = "This command cannot be used again for {} minutes and {} seconds".format(
            round(m), round(s)
        )

        embed = discord.Embed(
            title="Command On Cooldown", description=msg, color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    else:
        error_file = Path("error.txt")
        error_file.touch()
        with error_file.open("w") as f:
            f.write(exception_msg)
        with error_file.open("r") as f:
            # config, _ = core.common.load_config()
            data = "\n".join([l.strip() for l in f])

            GITHUB_API = "https://api.github.com"
            API_TOKEN = os.getenv("GIST")
            url = GITHUB_API + "/gists"
            print(f"Request URL: {url}")
            headers = {"Authorization": "token %s" % API_TOKEN}
            params = {"scope": "gist"}
            payload = {
                "description": "Timmy encountered a Traceback!",
                "public": True,
                "files": {"error": {"content": f"{data}"}},
            }
            res = requests.post(
                url, headers=headers, params=params, data=json.dumps(payload)
            )
            j = json.loads(res.text)
            ID = j["id"]
            gisturl = f"https://gist.github.com/{ID}"
            print(gisturl)

            permitlist = []
            query = database.Administrators.select().where(
                database.Administrators.TierLevel >= 3
            )
            for user in query:
                permitlist.append(user.discordID)

            if ctx.author.id not in permitlist:
                embed = discord.Embed(
                    title="Traceback Detected!",
                    description="Timmy here has ran into an error!\nPlease check what you sent and/or check out the help command!",
                    color=hexColors.orange_error,
                )
                embed.set_thumbnail(url=Others.timmyDog_png)
                embed.set_footer(text=f"Error: {str(error)}")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Traceback Detected!",
                    description="Timmy here has ran into an error!\nTraceback has been attached below.",
                    color=hexColors.orange_error,
                )
                embed.add_field(name="GIST URL", value=gisturl)
                embed.set_thumbnail(url=Others.timmyDog_png)
                embed.set_footer(text=f"Error: {str(error)}")
                await ctx.send(embed=embed)

            guild = bot.get_guild(Me.TechGuild)
            channel = guild.get_channel(Me.TracebackChannel)

            embed2 = discord.Embed(
                title="Traceback Detected!",
                description=f"**Information**\n**Server:** {ctx.message.guild.name}\n**User:** {ctx.message.author.mention}\n**Command:** {ctx.command.name}",
                color=hexColors.orange_error,
            )
            embed2.add_field(
                name="Gist URL",
                value=f"[Uploaded Traceback to GIST](https://gist.github.com/{ID})",
            )
            await channel.send(embed=embed2)

            error_file.unlink()

    raise error


bot.run(os.getenv("TOKEN"))
