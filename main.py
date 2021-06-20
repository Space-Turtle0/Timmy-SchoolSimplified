import asyncio
import inspect
import io
import os
import subprocess
import sys
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import aiohttp
import chat_exporter
import discord
from discord.ext import commands
from discord_components import (Button, ButtonStyle, DiscordComponents,
                                InteractionType)
from discord_sentry_reporting import use_sentry
from dotenv import load_dotenv

from core import database
from core.checks import is_botAdmin, is_botAdmin2, is_botAdmin3


load_dotenv()

#Applying towards intents
intents = discord.Intents.all()  

#Defining client and SlashCommands
client = commands.Bot(command_prefix="+", intents=intents, case_insensitive = True)
client.remove_command('help')


use_sentry(
    client,  # Traceback tracking, DO NOT MODIFY THIS
    dsn="https://af048b30f3fc42248210246501ef83ea@o816669.ingest.sentry.io/5807400",
    traces_sample_rate=1.0    
)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_extensions():  # Gets extension list dynamically
    extensions = []
    for file in Path("utils").glob("**/*.py"):
        if "!" in file.name or "__" in file.name:
            continue
        extensions.append(str(file).replace("/", ".").replace(".py", ""))
    return extensions

async def force_restart(ctx): 
    try:
        result = subprocess.run("cd && cd SchoolSimplified-Utils", shell=True, text=True, capture_output=True, check=True)
        res = subprocess.run("nohup python3 main.py &", shell=True, text=True, capture_output=True, check=True)
        print("complete")
    except Exception as e:
        print(result)
        print(res)

        await ctx.send(f"❌ Something went wrong while trying to restart the bot!\nThere might have been a bug which could have caused this!\n**Error:**\n{e}")
    finally:
        sys.exit(0)



@client.event
async def on_ready():
    now = datetime.now()

    print(f"Logged in as: {client.user.name}")
    print(f"{bcolors.OKBLUE}CONNECTED TO DISCORD{bcolors.ENDC}")
    print(f"{bcolors.WARNING}Current Discord.py Version: {discord.__version__}{bcolors.ENDC}")
    print(f"{bcolors.WARNING}Current Time: {now}{bcolors.ENDC}")

    chat_exporter.init_exporter(client)
    DiscordComponents(client)
    '''
    guild = await client.fetch_guild(763119924385939498)

    voice = discord.utils.get(client.voice_clients, guild=guild)

    if voice == None:
        voiceChannel = await client.fetch_channel(784556875487248394)

        global vc
        vc = await voiceChannel.connect()
    else:
        pass
    '''


for ext in get_extensions():
    client.load_extension(ext)
    print(f"[LOGGING] Loaded: {ext}")


@client.group(aliases=['cog'])
@is_botAdmin2
async def cogs(ctx):
    pass


@cogs.command()
@is_botAdmin2
async def unload(ctx, ext):
    if "cogs." not in ext:
        ext = f"cogs.{ext}"
    if ext in get_extensions():
        client.unload_extension(ext)
        embed = discord.Embed(
            title="Cogs - Unload", description=f"Unloaded cog: {ext}", color=0xd6b4e8)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Cogs Reloaded", description=f"Cog '{ext}' not found", color=0xd6b4e8)
        await ctx.send(embed=embed)


@cogs.command()
@is_botAdmin2
async def load(ctx, ext):
    if "cogs." not in ext:
        ext = f"cogs.{ext}"
    if ext in get_extensions():
        client.load_extension(ext)
        embed = discord.Embed(title="Cogs - Load",
                              description=f"Loaded cog: {ext}", color=0xd6b4e8)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Cogs - Load", description=f"Cog '{ext}' not found.", color=0xd6b4e8)
        await ctx.send(embed=embed)


@cogs.command(aliases=['restart'])
@is_botAdmin2
async def reload(ctx, ext):
    if ext == "all":
        embed = discord.Embed(
            title="Cogs - Reload", description="Reloaded all cogs", color=0xd6b4e8)
        for extension in get_extensions():
            client.reload_extension(extension)
        await ctx.send(embed=embed)
        return

    if "cogs." not in ext:
        ext = f"cogs.{ext}"

    if ext in get_extensions():
        client.reload_extension(ext)
        embed = discord.Embed(
            title="Cogs - Reload", description=f"Reloaded cog: {ext}", color=0xd6b4e8)
        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="Cogs - Reload", description=f"Cog '{ext}' not found.", color=0xd6b4e8)
        await ctx.send(embed=embed)


@cogs.command()
@is_botAdmin2
async def view(ctx):
    msg = " ".join(get_extensions())
    embed = discord.Embed(title="Cogs - View", description=msg, color=0xd6b4e8)
    await ctx.send(embed=embed)


@client.command()
async def ping(ctx):
    pingembed = discord.Embed(title="Pong! ⌛", color=0xb10d9f, description="Current Discord API Latency")
    pingembed.add_field(name="Current Ping:",value=f'{round(client.latency * 1000)}ms')
    await ctx.send(embed=pingembed)

@client.command(name='eval')
@is_botAdmin3
async def _eval(ctx, *, body):
    """Evaluates python code"""
    env = {
        'ctx': ctx,
        'bot': client,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        'source': inspect.getsource
    }

    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    env.update(globals())

    body = cleanup_code(body)
    stdout = io.StringIO()
    err = out = None

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    def paginate(text: str):
        '''Simple generator that paginates text.'''
        last = 0
        pages = []
        for curr in range(0, len(text)):
            if curr % 1980 == 0:
                pages.append(text[last:curr])
                last = curr
                appd_index = curr
        if appd_index != len(text)-1:
            pages.append(text[last:curr])
        return list(filter(lambda a: a != '', pages))
    
    try:
        exec(to_compile, env)
    except Exception as e:
        err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
        return await ctx.message.add_reaction('\u2049')

    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        if ret is None:
            if value:
                try:
                    
                    out = await ctx.send(f'```py\n{value}\n```')
                except:
                    paginated_text = paginate(value)
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.send(f'```py\n{page}\n```')
                            break
                        await ctx.send(f'```py\n{page}\n```')
        else:
            try:
                out = await ctx.send(f'```py\n{value}{ret}\n```')
            except:
                paginated_text = paginate(f"{value}{ret}")
                for page in paginated_text:
                    if page == paginated_text[-1]:
                        out = await ctx.send(f'```py\n{page}\n```')
                        break
                    await ctx.send(f'```py\n{page}\n```')

    if out:
        await ctx.message.add_reaction('\u2705')  # tick
    elif err:
        await ctx.message.add_reaction('\u2049')  # x
    else:
        await ctx.message.add_reaction('\u2705')

@client.command()
async def help(ctx):
    embed = discord.Embed(title = "Help Commands", description = "All avaliable commands under this bot!", color = discord.Colour.blue())
    embed.add_field(name = "Notion Page" ,value = "**Notion Page:** [https://spaceturtle.tech](https://spaceturtle.tech \"Masa if you see this, ur short\")")
    embed.set_footer(text = "DM SpaceTurtle#0001 for any questions or concerns!")
    embed.set_thumbnail(url = "https://i.gyazo.com/a236dbfb03e11a210cccbbb718bf3539.png")
    await ctx.send(embed = embed)

@client.command()
@is_botAdmin2
async def kill(ctx):
    await ctx.send("Goodbye!\n- **Ended Process**")
    sys.exit(0)

@client.group(aliases=['w'])
@is_botAdmin
async def whitelist(ctx):
    pass

@whitelist.command()
@is_botAdmin
async def list(ctx):
    adminList = []

    query1 = database.Administrators.select().where(database.Administrators.TierLevel == 1)
    for admin in query1:
        user = await client.fetch_user(admin.discordID)
        adminList.append(f"`{user.name}` -> `{user.id}`")

    adminLEVEL1 = "\n".join(adminList)



    adminList = []
    query2 = database.Administrators.select().where(database.Administrators.TierLevel == 2)
    for admin in query2:
        user = await client.fetch_user(admin.discordID)
        adminList.append(f"`{user.name}` -> `{user.id}`")

    adminLEVEL2 = "\n".join(adminList)



    adminList = []
    query3 = database.Administrators.select().where(database.Administrators.TierLevel == 3)
    for admin in query3:
        user = await client.fetch_user(admin.discordID)
        adminList.append(f"`{user.name}` -> `{user.id}`")

    adminLEVEL3 = "\n".join(adminList)



    embed = discord.Embed(title = "Bot Administrators", description = "Whitelisted Users that have Increased Authorization", color = discord.Color.green())
    embed.add_field(name = "Whitelisted Users", value = f"Format:\n**Username** -> **ID**\n\n**Permit 3:** *Sudo Administrators*\n{adminLEVEL3}\n\n**Permit 2:** *Administrators*\n{adminLEVEL2}\n\n**Permit 1:** *Bot Managers*\n{adminLEVEL1}")
    embed.set_footer(text = "Only Owners can add Bot Administrators. | Permit 3 is the HIGHEST Authorization Level")

    await ctx.send(embed = embed)
    

@whitelist.command()
@commands.is_owner()
async def remove(ctx, ID: discord.User):
    database.db.connect(reuse_if_open=True)
    
    query = database.Administrators.select().where(database.Administrators.discordID == ID.id)
    if query.exists():
        query = query.get()

        query.delete_instance()

        await ctx.send("Removed user!")

    else:
        await ctx.send("Invalid Provided: (No Record Found)")

    database.db.close()

@whitelist.command()
@commands.is_owner()
async def add(ctx, ID: discord.User, level: int):
    database.db.connect(reuse_if_open=True)

    q: database.Administrators = database.Administrators.create(discordID = ID.id, TierLevel = level)
    q.save()

    await ctx.send(f"{ID.name} has been added successfully with permit level `{str(level)}``.")

    database.db.close()


client.run(os.getenv("TOKEN"))


