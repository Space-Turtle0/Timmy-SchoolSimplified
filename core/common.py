import asyncio
import io
import json
import logging
import os
import random
import string
import subprocess
import sys
import typing
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Tuple, Union

import boto3
import chat_exporter
import configcatclient
import discord
from botocore.exceptions import ClientError
from discord import ApplicationCommandError, Button, ButtonStyle, DiscordException, SelectOption, ui
from discord.ext import commands
from dotenv import load_dotenv

from core import database

load_dotenv()
# global variables
coroutineType = Callable[[Any, Any], Awaitable[Any]]

class ConfigcatClient:
    MAIN_ID_CC = configcatclient.create_client(
        os.getenv("MAINID_CC")
    )
    STAFF_ID_CC = configcatclient.create_client(
        os.getenv("STAFFID_CC")
    )
    DIGITAL_ID_CC = configcatclient.create_client(
        os.getenv("DIGITALID_CC")
    )
    TECH_ID_CC = configcatclient.create_client(
        os.getenv("TECHID_CC")
    )
    MKT_ID_CC = configcatclient.create_client(
        os.getenv("MKTID_CC")
    )
    TUT_ID_CC = configcatclient.create_client(
        os.getenv("TUTID_CC")
    )
    ACAD_ID_CC = configcatclient.create_client(
        os.getenv("ACADID_CC")
    )
    HR_ID_CC = configcatclient.create_client(
        os.getenv("HRID_CC")
    )
    CHECK_DB_CC = configcatclient.create_client(
        os.getenv("CHECKDB_CC")
    )


async def rawExport(self, channel, response, user: discord.User):
    transcript = await chat_exporter.export(channel, None)

    if transcript is None:
        return

    embed = discord.Embed(
        title="Channel Transcript",
        description=f"**Channel:** {channel.name}"
        f"\n**User Invoked:** {user.name}*"
        f"\nTranscript Attached Below*",
        color=discord.Colour.green(),
    )
    transcript_file = discord.File(
        io.BytesIO(transcript.encode()), filename=f"transcript-{channel.name}.html"
    )

    msg: discord.Message = await response.send(embed=embed, file=transcript_file)
    return msg


async def paginate_embed(
    bot: discord.Client,
    ctx,
    embed: discord.Embed,
    population_func,
    end: int,
    begin: int = 1,
    page=1,
):
    emotes = ["◀️", "▶️"]

    def check_reaction(reaction, user):
        return user == ctx.author and str(reaction.emoji) in emotes

    embed = await population_func(embed, page)
    if isinstance(embed, discord.Embed):
        message = await ctx.send(embed=embed)
    else:
        await ctx.send(str(type(embed)))
        return
    await message.add_reaction(emotes[0])
    await message.add_reaction(emotes[1])
    while True:
        try:
            reaction, user = await bot.wait_for(
                "reaction_add", timeout=60, check=check_reaction
            )
            if user == bot.user:
                continue
            if str(reaction.emoji) == emotes[1] and page < end:
                page += 1
                embed = await population_func(embed, page)
                await message.remove_reaction(reaction, user)
                await message.edit(embed=embed)
            elif str(reaction.emoji) == emotes[0] and page > begin:
                page -= 1
                embed = await population_func(embed, page)
                await message.remove_reaction(reaction, user)
                await message.edit(embed=embed)
        except asyncio.TimeoutError:
            await message.clear_reactions()
            break

def get_extensions():
    extensions = []
    extensions.append("jishaku")
    if sys.platform == "win32" or sys.platform == "cygwin":
        dirpath = "\\"
    else:
        dirpath = "/"

    for file in Path("utils").glob("**/*.py"):
        if "!" in file.name or "DEV" in file.name:
            continue
        extensions.append(str(file).replace(dirpath, ".").replace(".py", ""))
    return extensions
    
def load_config(name) -> Tuple[dict, Path]:
    config_file = Path(f"utils/bots/RoleSync/{name}.json")
    config_file.touch(exist_ok=True)
    if config_file.read_text() == "":
        config_file.write_text("{}")
    with config_file.open("r") as f:
        config = json.load(f)
    return config, config_file


def prompt_config(msg, key):
    config, config_file = load_config()
    if key not in config:
        config[key] = input(msg)
        with config_file.open("w+") as f:
            json.dump(config, f, indent=4)


def prompt_config2(msg, key):
    config, config_file = load_config()
    config[key] = msg
    with config_file.open("w+") as f:
        json.dump(config, f, indent=4)


def S3_upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)
    # Upload the file
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2",
    )
    try:
        response = s3_client.upload_file(
            file_name,
            bucket,
            object_name,
            ExtraArgs={"ContentType": "text/html", "ACL": "public-read"},
        )
        # s3_object = s3_client.Object('ch-transcriptlogs', file_name)
        # s3_object.metadata.update({'x-amz-meta-content-type':'text/html'})
        # s3_object.copy_from(CopySource={'Bucket':'ch-transcriptlogs', 'x-amz-meta-content-type':'binary/octet-stream'}, Metadata=s3_object.metadata, MetadataDirective='REPLACE')

    except ClientError as e:
        print(e)


class MAIN_ID:
    """
    IDs of the SS Main server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_main = int(ConfigcatClient.MAIN_ID_CC.get_value("g_main", 763119924385939498))

    ch_commands = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_commands", 763409002913595412))
    ch_seniorMods = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_seniormods", 878792926266810418))
    ch_moderators = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_moderators", 786068971048140820))
    ch_mutedChat = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_mutedchat", 808919081469739008))
    ch_modLogs = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_modlogs", 863177000372666398))
    ch_tutoring = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_tutoring", 865716647083507733))
    ch_transcriptLogs = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "ch_transcriptlogs", 767434763337728030
    ))
    ch_actionLogs = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_actionlogs", 767206398060396574))
    ch_modCommands = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_modcommands", 786057630383865858))
    ch_controlPanel = int(ConfigcatClient.MAIN_ID_CC.get_value("ch_controlpanel", 843637802293788692))
    ch_startPrivateVC = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "ch_startprivatevc", 784556875487248394
    ))

    # *** Categories ***
    cat_casual = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_casual", 763121170324783146))
    cat_community = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_community", 800163651805773824))
    cat_lounge = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_lounge", 774847738239385650))
    cat_events = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_events", 805299289604620328))
    cat_voice = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_voice", 763857608964046899))
    cat_scienceTicket = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "cat_scienceticket", 800479815471333406
    ))
    cat_fineArtsTicket = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "cat_fineartsticket", 833210452758364210
    ))
    cat_mathTicket = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_mathticket", 800472371973980181))
    cat_socialStudiesTicket = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "cat_socialstudiesticket", 800481237608824882
    ))
    cat_englishTicket = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "cat_englishticket", 800475854353596469
    ))
    cat_essayTicket = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_essayticket", 854945037875806220))
    cat_languageTicket = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "cat_languageticket", 800477414361792562
    ))
    cat_otherTicket = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_otherticket", 825917349558747166))
    cat_privateVC = int(ConfigcatClient.MAIN_ID_CC.get_value("cat_privatevc", 776988961087422515))

    # *** Roles ***
    r_codingClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_codingclub", 883169286665936996))
    r_debateClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_debateclub", 883170141771272294))
    r_musicClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_musicclub", 883170072355561483))
    r_cookingClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_cookingclub", 883162279904960562))
    r_chessClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_chessclub", 883564455219306526))
    r_bookClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_bookclub", 883162511560560720))
    r_advocacyClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_advocacyclub", 883169000866070539))
    r_speechClub = int(ConfigcatClient.MAIN_ID_CC.get_value("r_speechclub", 883170166161149983))
    r_clubPresident = int(ConfigcatClient.MAIN_ID_CC.get_value("r_clubpresident", 883160826180173895))

    r_chatHelper = int(ConfigcatClient.MAIN_ID_CC.get_value("r_chathelper", 811416051144458250))
    r_leadHelper = int(ConfigcatClient.MAIN_ID_CC.get_value("r_leadhelper", 810684359765393419))
    r_essayReviser = int(ConfigcatClient.MAIN_ID_CC.get_value("r_essayreviser", 854135371507171369))

    # *** Messages ***
    # Tutoring
    msg_math = int(ConfigcatClient.MAIN_ID_CC.get_value("msg_math", 866904767568543744))
    msg_science = int(ConfigcatClient.MAIN_ID_CC.get_value("msg_science", 866904901174427678))
    msg_english = int(ConfigcatClient.MAIN_ID_CC.get_value("msg_english", 866905061182930944))
    msg_language = int(ConfigcatClient.MAIN_ID_CC.get_value("msg_language", 866905971519389787))
    msg_art = int(ConfigcatClient.MAIN_ID_CC.get_value("msg_art", 866906016602652743))
    msg_socialStudies = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "msg_socialstudies", 866905205094481951
    ))
    msg_computerScience = int(ConfigcatClient.MAIN_ID_CC.get_value(
        "msg_computerscience", 867550791635566623
    ))


class STAFF_ID:
    """
    IDs of the SS Staff Community server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_staff = int(ConfigcatClient.STAFF_ID_CC.get_value("g_staff", 891521033700540457))

    # *** Channels ***
    ch_verificationLogs = int(ConfigcatClient.STAFF_ID_CC.get_value(
        "ch_verificationlogs", 894241199433580614
    ))
    ch_verification = int(ConfigcatClient.STAFF_ID_CC.get_value("ch_verification", 894240578651443232))
    ch_console = int(ConfigcatClient.STAFF_ID_CC.get_value("ch_console", 895041227123228703))
    ch_startPrivateVC = int(ConfigcatClient.STAFF_ID_CC.get_value(
        "ch_startprivatevc", 895041070956675082
    ))

    # *** Categories ***
    cat_privateVC = int(ConfigcatClient.STAFF_ID_CC.get_value("cat_privatevc", 895041016057446411))


class DIGITAL_ID:
    """
    IDs of the SS Staff Community server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_digital = int(ConfigcatClient.DIGITAL_ID_CC.get_value("g_digital", 778406166735880202))

    # *** Channels ***
    ch_verification = int(ConfigcatClient.DIGITAL_ID_CC.get_value("ch_verification", 878681438462050356))
    ch_waitingRoom = int(ConfigcatClient.DIGITAL_ID_CC.get_value("ch_waitingroom", 878679747255750696))


class TECH_ID:
    """
    IDs of the SS Technical & Information Department server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_tech = int(ConfigcatClient.TECH_ID_CC.get_value("g_tech", 805593783684562965))

    # *** Channels ***
    ch_tracebacks = int(ConfigcatClient.TECH_ID_CC.get_value("ch_tracebacks", 851949397533392936))
    ch_commissionLogs = int(ConfigcatClient.TECH_ID_CC.get_value(
        "ch_commissionlogs", 849722616880300061
    ))
    ch_ticketLog = int(ConfigcatClient.TECH_ID_CC.get_value("ch_ticketlog", 872915565600182282))

    # *** Categories ***
    cat_developerComms = int(ConfigcatClient.TECH_ID_CC.get_value(
        "cat_developercomms", 873261268495106119
    ))

    # *** Roles ***
    r_developerManager = int(ConfigcatClient.TECH_ID_CC.get_value(
        "r_developermanager", 805596419066822686
    ))
    r_assistantBotDevManager = int(ConfigcatClient.TECH_ID_CC.get_value(
        "r_assistantbotdevmanager", 816498160880844802
    ))
    r_botDeveloper = int(ConfigcatClient.TECH_ID_CC.get_value("r_botdeveloper", 805610985594814475))


class MKT_ID:
    """
    IDs of the SS Marketing Department server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_mkt = int(ConfigcatClient.MKT_ID_CC.get_value("g_mkt", 799855854182596618))

    # *** Channels ***
    ch_commands = int(ConfigcatClient.MKT_ID_CC.get_value("ch_commands", 799855856295608345))
    ch_commissionTranscripts = int(ConfigcatClient.MKT_ID_CC.get_value(
        "ch_commissiontranscripts", 820843692385632287
    ))

    # *** Categories ***
    cat_design = int(ConfigcatClient.MKT_ID_CC.get_value("cat_design", 820873176208375838))
    cat_media = int(ConfigcatClient.MKT_ID_CC.get_value("cat_media", 882031123541143632))
    cat_discord = int(ConfigcatClient.MKT_ID_CC.get_value("cat_discord", 888668259220615198))

    # *** Roles ***
    r_discordManager = int(ConfigcatClient.MKT_ID_CC.get_value(
        "r_discordmanager", 890778255655841833
    ))
    r_discordTeam = int(ConfigcatClient.MKT_ID_CC.get_value("r_discordteam", 805276710404489227))
    r_designManager = int(ConfigcatClient.MKT_ID_CC.get_value("r_designmanager", 882755765910261760))
    r_designTeam = int(ConfigcatClient.MKT_ID_CC.get_value("r_designteam", 864161064526020628))
    r_contentCreatorManager = int(ConfigcatClient.MKT_ID_CC.get_value(
        "r_contentcreatormanager", 864165192148189224
    ))


class TUT_ID:
    """
    IDs of the SS Tutoring Division server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_tut = int(ConfigcatClient.TUT_ID_CC.get_value("g_tut", 860897711334621194))

    # *** Channels ***
    ch_botCommands = int(ConfigcatClient.TUT_ID_CC.get_value("ch_botcommands", 862480236965003275))
    ch_hourLogs = int(ConfigcatClient.TUT_ID_CC.get_value("ch_hourlogs", 873326994220265482))


class ACAD_ID:
    """
    IDs of the SS Academics Department server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_acad = int(ConfigcatClient.ACAD_ID_CC.get_value("g_acad", 801974357395636254))
    cat_essay = int(ConfigcatClient.ACAD_ID_CC.get_value("cat_essay", 854945037875806220))
    cat_english = int(ConfigcatClient.ACAD_ID_CC.get_value("cat_english", 800475854353596469))


class HR_ID:
    """
    IDs of the SS HR Department server.
    NOTE: If you want to add IDs, please use the format as below.
    Format:
        g: discord.Guild
        ch: discord.TextChannel, discordVoiceChannel, discordStageChannel
        cat: discord.CategoryChannel
        r: discord.Role
        msg: discord.Message
    """

    # *** Guilds ***
    g_hr = int(ConfigcatClient.HR_ID_CC.get_value("g_hr", 815753072742891532))


class CheckDB_CC:
    """
    Checks and Safeguards for the Bot.
    """

    MasterMaintenance = int(ConfigcatClient.CHECK_DB_CC.get_value("mastermaintenance", False))
    guildNone = int(ConfigcatClient.CHECK_DB_CC.get_value("guildnone", False))
    externalGuild = int(ConfigcatClient.CHECK_DB_CC.get_value("externalguild", True))
    ModRoleBypass = int(ConfigcatClient.CHECK_DB_CC.get_value("modrolebypass", True))
    ruleBypass = int(ConfigcatClient.CHECK_DB_CC.get_value("rulebypass", True))
    publicCategories = int(ConfigcatClient.CHECK_DB_CC.get_value("publiccategories", False))
    elseSituation = int(ConfigcatClient.CHECK_DB_CC.get_value("elsesituation", True))
    PersistantChange = int(ConfigcatClient.CHECK_DB_CC.get_value("persistantchange", True))


def get_value(
    classType: Union[
        MAIN_ID, STAFF_ID, DIGITAL_ID, TECH_ID, MKT_ID, TUT_ID, ACAD_ID, HR_ID
    ],
    value: str,
) -> int:
    """
    Get a value of a ID class within ConfigCat.

    Parameters:
        classType: The class of the ID which should be returned
        value: The variable name (name of the ID)
    """

    if ConfigcatClient.get_value(value, None) is None:
        raise ValueError(f"Cannot find {value} within ConfigCat!")

    if value in classType.ID_DICT:
        return int(ConfigcatClient.get_value(value, classType.ID_DICT[value]))
    else:
        return int(ConfigcatClient.get_value(value, None))

class ErrorCodes:
    {
        "TOE-": [discord.errors, DiscordException, ApplicationCommandError],
        "TOE-": [KeyError, TypeError, ]
    }

class Emoji:
    """
    Emojis to use for the bot.
    """

    space = "<:space:834967357632806932>"
    confirm = "<:confirm:860926261966667806>"
    deny = "<:deny:860926229335375892>"
    question = "<:question:861794223027519518>"
    warn = "<:warn:860926255443345409>"
    lock = "<:lock:860926195087835137>"
    unlock = "<:unlock:860926246937427989>"
    time = "<:time:860926238737825793>"
    loading = None
    redissue = "<:issue:860587949263290368>"
    archive = "<:file:861794167578689547>"
    cycle = "<:cycle:861794132585611324>"
    calender = "<:calendar:861794038739238943>"
    addgear = "<:add5x:862875088311025675>"
    minusgear = "<:minusgear:862875088217702421>"
    invalidchannel = "<:invalidchannel:862875088361619477>"
    barrow = "<:SS:865715703545069568>"
    person = "<:person:883771751127990333>"
    activity = "<:note:883771751190908989>"
    check = "<:success:834967474101420032>"
    cancel = "<:cancel:834967460075012106>"
    arrow = "<:rightDoubleArrow:834967375735422996>"
    mute = "<:mute:834967579264155658>"
    ban = "<:ban:834967435642929162>"
    reason = "<:activity:834968852558249999>"
    profile = "<:profile:835213199070593035>"
    creation = "<:creation:835213216299745291>"
    date = "<:thewickthing:835213229294223400>"
    discordLogo = "<:discord:812757175465934899>"
    discordLoad = "<a:Discord:866408537503694869>"

    timmyBook = "<:timmy_book:880875405962264667>"
    loadingGIF = "<a:Loading:904192577094426626>"
    loadingGIF2 = "<a:Loading:905563298089541673>"
    gsuitelogo = "<:gsuitelogo:932034284724834384>"


class hexColors:
    """
    Hex colors for the bot.
    """

    # *** Standard Colors ***
    yellow = 0xF5DD42
    orange = 0xFCBA03
    blurple = 0x6C7DFE
    light_purple = 0xD6B4E8
    dark_gray = 0x2F3136

    yellow_ticketBan = 0xEFFA16
    green_general = 0x3AF250
    green_confirm = 0x37E32B
    red_cancel = 0xE02F2F
    red_error = 0xF5160A
    orange_error = 0xFC3D03
    mod_blurple = 0x4DBEFF
    ss_blurple = 0x7080FA


class Others:
    """
    Other things to use for the bot. (Images, characters, etc.)
    """

    ssLogo_png = "https://media.discordapp.net/attachments/864060582294585354/878682781352362054/ss_current.png"
    error_png = "https://icons.iconarchive.com/icons/paomedia/small-n-flat/1024/sign-error-icon.png"
    nitro_png = "https://i.imgur.com/w9aiD6F.png"

    # *** Timmy Images ***
    timmyDog_png = "https://cdn.discordapp.com/attachments/875233489727922177/876610305852051456/unknown.png"
    timmyLaptop_png = "https://i.gyazo.com/5cffb6cd45e5e1ee9b1d015bccbdf9e6.png"
    timmyHappy_png = "https://i.gyazo.com/a0b221679db0f980504e64535885a5fd.png"
    timmyBook_png = "https://media.discordapp.net/attachments/875233489727922177/876603875329732618/timmy_book.png?width=411&height=533"
    timmyTeacher_png = "https://media.discordapp.net/attachments/875233489727922177/877378910214586368/tutoring.png?width=411&height=532"
    timmyDonation_png = "timmydonation.png"
    timmyDonation_path = "./utils/bots/CoreBot/LogFiles/timmydonation.png"

    space_character = "　"
    TICKET_INACTIVE_TIME = 1440
    CHID_DEFAULT = 905217698865225728


CHHelperRoles = {
    "Essay": 854135371507171369,
    "Essay Reviser": 854135371507171369,
    "English": 862160296914714645,
    "English Language": 862160080896000010,
    "English Literature": 862160567921541171,
    "Math": 862160874214129705,
    "Algebra": 862161250656976896,
    "Geometry": 862160836029317160,
    "Precalculus": 862160740509024337,
    "Calculus": 862160709252939837,
    "Statistics": 862160620563202079,
    "Science": 862160358264274944,
    "Biology": 862160682472439828,
    "Chemistry": 862160317794615296,
    "Physics": 862160774075383808,
    "Psych": 862160362677993493,
    "Social Studies": 862160071466811412,
    "World History": 862159919943254056,
    "US History": 862159910254673982,
    "US Gov": 862160366096482314,
    "Euro": 862159915660476427,
    "Human Geo": 862960195108601866,
    "Economy": 862159734257352724,
    "Languages": 862160078370635796,
    "French": 862160075559665724,
    "Chinese": 862143325683318804,
    "Korean": 862143319458316298,
    "Spanish": 856704808807563294,
    "Computer Science": 862160355622780969,
    "Fine Arts": 862160360626716733,
    "Research": 862159906148450314,
    "SAT/ACT": 862159736384258048,
}


rulesDict = {
    1: f"All Terms of Service and Community Guidelines apply. && {Emoji.barrow} https://discord.com/terms\n{Emoji.barrow} https://discord.com/guidelines",
    2: f"Keep chats and conversations mainly in English. && {Emoji.barrow} Full-blown conversations in a different language that disrupt the environment are not allowed.\n{Emoji.barrow} Disrupting an existing conversation in English in voice chat is not allowed.",
    3: f"Keep chats and conversations relevant. && {Emoji.barrow} Keep discussions about politics or anything else in <#773366189648642069>.\n{Emoji.barrow} Ask homework questions in the homework channels or tickets.",
    4: f"No content that does not belong in a school server. && {Emoji.barrow} No inappropriate user profiles, avatars, banners, statuses, about me, usernames, or nicknames.\n{Emoji.barrow} No sharing of content that glorifies or promotes suicide or self-harm.\n{Emoji.barrow} No trolling, raiding, epileptic, disturbing, suggestive, or offensive behavior.\n{Emoji.barrow} No sexist, racist, homophobic, transphobic, xenophobic, islamophobic, pedophilic, creepy behavior, etc.",
    5: f"No advertising or self-promotion (unless given explicit permission). && {Emoji.barrow} Self-advertising a website, group, or anything else through DMs, VC or in the server is not allowed.\n{Emoji.barrow} Explicitly asking users to look at advertisements in status/About Me is not allowed.",
    6: f"No toxic behavior or harassment. && {Emoji.barrow} No discriminatory jokes or language towards an individual or group due to race, ethnicity, nationality, sex, gender, sexual orientation, religious affiliation, or disabilities.\n{Emoji.barrow} Disrespect of members is not allowed, especially if it is continuous, repetitive, or severe.\n{Emoji.barrow} Encouraging toxicity, harassment, bullying, and anything of the sort is prohibited.",
    7: f"No illegal or explicit material. && {Emoji.barrow} Discussing or sharing illegal content is prohibited. This includes, but is not limited to: copyrighted content, pirated content, illegal activities, crimes, IPGrabbers, phishing links.\n{Emoji.barrow} Any form of NSFW, NSFL, or explicit content (pornographic, overtly sexual, overly gory) is prohibited.",
    8: f"No DDoS, dox, death or any other sort of threats. && {Emoji.barrow} Indirect or direct threats to harm someone else are strictly prohibited and causes for immediate ban.\n{Emoji.barrow} DDoS (Distributed Denial of Service): sending a large amount of requests in a short amount of time.\n{Emoji.barrow} Dox: revealing any private information of another member, such as real name or address, without consent.",
    9: f"No slurs and excessive or harmful profanity usage. && {Emoji.barrow} Using or attempting to use slurs and racist terms is prohibited.\n{Emoji.barrow} Excessive profanity, verbal abuse and insults are prohibited.",
    10: f"No cheating in any form. && {Emoji.barrow} It is strictly prohibited to cheat or engage in academic dishonesty anywhere in the server.",
    11: f"No spamming in any form. && {Emoji.barrow} Spamming links, images, messages, roles, emojis, emotes, emote reactions, or anything else is not allowed.",
    12: f"No impersonation in any form. && {Emoji.barrow} Changing your username or avatar to something similar as any staff or members with the intent to mimic them and create confusion is prohibited. ",
    13: f"No disruptive behavior in voice chat. && {Emoji.barrow} No continuous hopping between voice chats.\n{Emoji.barrow} No starting and closing streams in short intervals.\n{Emoji.barrow} No loud, annoying, or high-pitched noises.\n{Emoji.barrow} No voice changers if asked to stop.",
    14: f"No evading user blocks, punishments, or bans by using alternate accounts. && {Emoji.barrow} Sending unwanted, repeated friend requests or messages to contact someone who has blocked you is prohibited.\n{Emoji.barrow} Creating alternate accounts to evade a punishment or ban, harass or impersonate someone, or participate in a raid are all strictly prohibited.\n{Emoji.barrow} Suspicions of being an alternate account are cause for a ban with no prior warning.\n{Emoji.barrow} To discuss punishments or warnings, create a support ticket or talk to a moderator in DMs.",
}


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class EmbeddedActivity:
    awkword = 879863881349087252
    betrayal = 773336526917861400
    cg2_qa = 832012815819604009
    cg2_staging = 832012730599735326
    cg3_dev = 832012682520428625
    cg3_prod = 832013003968348200
    cg3_qa = 832012894068801636
    cg3_staging = 832012938398400562
    cg4_dev = 832013108234289153
    cg4_prod = 832025144389533716
    cg4_qa = 832025114077298718
    cg4_staging = 832025061657280566
    chess_in_the_park_dev = 832012586023256104
    chess_in_the_park = 832012774040141894
    decoders_dev = 891001866073296967
    doodle_crew = 878067389634314250
    doodle_crew_dev = 878067427668275241
    fishington = 814288819477020702
    letter_tile = 879863686565621790
    pn_staging = 763116274876022855
    poker_night = 755827207812677713
    poker_qa = 801133024841957428
    putts = 832012854282158180
    sketchy_artist = 879864070101172255
    sketchy_artist_dev = 879864104980979792
    spell_cast = 852509694341283871
    watch_together = 880218394199220334
    watch_together_dev = 880218832743055411
    word_snacks = 879863976006127627
    word_snacks_dev = 879864010126786570
    youtube_together = 755600276941176913


class SelectMenuHandler(ui.Select):
    """Adds a SelectMenu to a specific message and returns it's value when option selected.

    Usage:
        To do something after the callback function is invoked (the button is pressed), you have to pass a
        coroutine to the class. IMPORTANT: The coroutine has to take two arguments (discord.Interaction, discord.View)
        to work.
    """

    def __init__(
        self,
        options: typing.List[SelectOption],
        custom_id: typing.Union[str, None] = None,
        place_holder: typing.Union[str, None] = None,
        max_values: int = 1,
        min_values: int = 1,
        disabled: bool = False,
        select_user: typing.Union[discord.Member, discord.User, None] = None,
        roles: List[discord.Role] = None,
        interaction_message: typing.Union[str, None] = None,
        ephemeral: bool = True,
        coroutine: coroutineType = None,
        view_response=None,
    ):
        """
        Parameters:
            options: List of discord.SelectOption
            custom_id: Custom ID of the view. Default to None.
            place_holder: Place Holder string for the view. Default to None.
            max_values Maximum values that are selectable. Default to 1.
            min_values: Minimum values that are selectable. Default to 1.
            disabled: Whenever the button is disabled or not. Default to False.
            select_user: The user that can perform this action, leave blank for everyone. Defaults to None.
            interaction_message: The response message when pressing on a selection. Default to None.
            ephemeral: Whenever the response message should only be visible for the select_user or not. Default to True.
        """

        self.options_ = options
        self.custom_id_ = custom_id
        self.select_user = select_user
        self.roles = roles
        self.disabled_ = disabled
        self.placeholder_ = place_holder
        self.max_values_ = max_values
        self.min_values_ = min_values
        self.interaction_message_ = interaction_message
        self.ephemeral_ = ephemeral
        self.coroutine = coroutine
        self.view_response = view_response

        if self.custom_id_:
            super().__init__(
                options=self.options_,
                placeholder=self.placeholder_,
                custom_id=self.custom_id_,
                disabled=self.disabled_,
                max_values=self.max_values_,
                min_values=self.min_values_,
            )
        else:
            super().__init__(
                options=self.options_,
                placeholder=self.placeholder_,
                disabled=self.disabled_,
                max_values=self.max_values_,
                min_values=self.min_values_,
            )

    async def callback(self, interaction: discord.Interaction):
        if self.select_user in [None, interaction.user] or any(
            role in interaction.user.roles for role in self.roles
        ):
            if self.custom_id_ is None:
                self.view.value = self.values[0]
            else:
                # self.view.value = self.custom_id_
                self.view_response = self.values[0]

            if self.interaction_message_:
                await interaction.response.send_message(
                    content=self.interaction_message_, ephemeral=self.ephemeral_
                )

            if self.coroutine is not None:
                await self.coroutine(interaction, self.view)
            else:
                self.view.stop()
        else:
            await interaction.response.send_message(
                content="You're not allowed to interact with that!", ephemeral=True
            )


class ButtonHandler(ui.Button):
    """
    Adds a Button to a specific message and returns it's value when pressed.

    Usage:
        To do something after the callback function is invoked (the button is pressed), you have to pass a
        coroutine to the class. IMPORTANT: The coroutine has to take two arguments (discord.Interaction, discord.View)
        to work.
    """

    def __init__(
        self,
        style: ButtonStyle,
        label: str,
        custom_id: typing.Union[str, None] = None,
        emoji: typing.Union[str, None] = None,
        url: typing.Union[str, None] = None,
        disabled: bool = False,
        button_user: typing.Union[discord.Member, discord.User, None] = None,
        roles: List[discord.Role] = None,
        interaction_message: typing.Union[str, None] = None,
        ephemeral: bool = True,
        coroutine: coroutineType = None,
    ):
        """
        Parameters:
            style: Label for the button
            label: Custom ID that represents this button. Default to None.
            custom_id: Style for this button. Default to None.
            emoji: An emoji for this button. Default to None.
            url: A URL for this button. Default to None.
            disabled: Whenever the button should be disabled or not. Default to False.
            button_user: The user that can perform this action, leave blank for everyone. Defaults to None.
            roles: The roles which the user needs to be able to click the button.
            interaction_message: The response message when pressing on a selection. Default to None.
            ephemeral: Whenever the response message should only be visible for the select_user or not. Default to True.
            coroutine: A coroutine that gets invoked after the button is pressed. If None is passed, the view is stopped after the button is pressed.  Default to None.
        """
        self.style_ = style
        self.label_ = label
        self.custom_id_ = custom_id
        self.emoji_ = emoji
        self.url_ = url
        self.disabled_ = disabled
        self.button_user = button_user
        self.roles = roles
        self.interaction_message_ = interaction_message
        self.ephemeral_ = ephemeral
        self.coroutine = coroutine

        if self.custom_id_:
            super().__init__(
                style=self.style_,
                label=self.label_,
                custom_id=self.custom_id_,
                emoji=self.emoji_,
                url=self.url_,
                disabled=self.disabled_,
            )
        else:
            super().__init__(
                style=self.style_,
                label=self.label_,
                emoji=self.emoji_,
                url=self.url_,
                disabled=self.disabled_,
            )

    async def callback(self, interaction: discord.Interaction):
        if self.button_user in [None, interaction.user] or any(
            role in interaction.user.roles for role in self.roles
        ):
            if self.custom_id_ is None:
                self.view.value = None
            else:
                self.view.value = self.custom_id_

            if self.interaction_message_:
                await interaction.response.send_message(
                    content=self.interaction_message_, ephemeral=self.ephemeral_
                )

            if self.coroutine is not None:
                await self.coroutine(interaction, self.view)
            else:
                self.view.stop()
        else:
            await interaction.response.send_message(
                content="You're not allowed to interact with that!", ephemeral=True
            )


def getGuildList(bot: commands.Bot, exemptServer: List[int] = None) -> list:
    guildList = []
    for guild in bot.guilds:
        if guild.id in exemptServer:
            continue
        guildList.append(guild.id)

    return guildList


class TechnicalCommissionConfirm(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.value = None
        self.bot = bot

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="persistent_view:tempconfirm",
    )
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        TranscriptLOG = self.bot.get_channel(TECH_ID.ch_ticketLog)
        ch = await self.bot.fetch_channel(interaction.channel_id)

        await rawExport(self, ch, TranscriptLOG, interaction.user)
        await ch.delete()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.response.send_message(
            "ok, not removing this channel.", ephemeral=True
        )
        self.value = False
        self.stop()


class LockButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.value = None
        self.bot = bot

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:lock",
        emoji="🔒",
    )
    async def lock(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        ch = await self.bot.fetch_channel(interaction.channel_id)
        TempConfirmInstance = TechnicalCommissionConfirm(self.bot)

        msg = await ch.send(
            "Are you sure you want to close this ticket?", view=TempConfirmInstance
        )



class GSuiteVerify(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None
    

    @discord.ui.button(
        label="Verify with GSuite",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:gsuiteverify",
        emoji=Emoji.gsuitelogo,
    )
    async def lock(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True



class TempConfirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="persistent_view:tempconfirm",
    )
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False
        self.stop()


class NitroConfirmFake(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:nitrofake",
    )
    async def claim(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            await interaction.response.send_message(
                "https://images-ext-2.discordapp.net/external/YTk-6Mfxbbr8KwIc-3Pyy5Z_06tfpcO65MflxYgbjA8/%3Fcid%3D73b8f7b119cc9225923f70c7e25a1f8e8932c7ae8ef48fe7%26rid%3Dgiphy.mp4%26ct%3Dg/https/media2.giphy.com/media/Ju7l5y9osyymQ/giphy.mp4",
                ephemeral=True,
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                "https://images-ext-2.discordapp.net/external/YTk-6Mfxbbr8KwIc-3Pyy5Z_06tfpcO65MflxYgbjA8/%3Fcid%3D73b8f7b119cc9225923f70c7e25a1f8e8932c7ae8ef48fe7%26rid%3Dgiphy.mp4%26ct%3Dg/https/media2.giphy.com/media/Ju7l5y9osyymQ/giphy.mp4",
                ephemeral=True,
            )
        self.value = True


class TicketLockButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.value = None
        self.bot = bot

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:lock",
        emoji="🔒",
    )
    async def lock(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        ch = await self.bot.fetch_channel(interaction.channel_id)
        TempConfirmInstance = TicketTempConfirm(self.bot)

        msg = await ch.send(
            "Are you sure you want to close this ticket?", view=TempConfirmInstance
        )


class TicketTempConfirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="persistent_view:tempconfirm",
    )
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False
        self.stop()




async def id_generator(size=3, chars=string.ascii_uppercase):
    while True:
        ID = "".join(random.choice(chars) for _ in range(size))
        query = database.TutorBot_Sessions.select().where(
            database.TutorBot_Sessions.SessionID == ID
        )

        if query.exists():
            continue
        else:
            return ID


async def force_restart(ctx):
    p = subprocess.run(
        "git status -uno", shell=True, text=True, capture_output=True, check=True
    )

    embed = discord.Embed(
        title="Restarting...",
        description="Doing GIT Operation (1/3)",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Checking GIT (1/3)", value=f"**Git Output:**\n```shell\n{p.stdout}\n```"
    )

    msg = await ctx.send(embed=embed)
    try:
        result = subprocess.run(
            "cd && cd Timmy-SchoolSimplified && nohup python3 main.py &",
            shell=True,
            text=True,
            capture_output=True,
            check=True,
        )

        embed.add_field(
            name="Started Environment and Additional Process (2/3)",
            value="Executed `source` and `nohup`.",
            inline=False,
        )
        await msg.edit(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Operation Failed", description=e, color=discord.Color.red()
        )
        embed.set_footer(text="Main bot process will be terminated.")

        await ctx.send(embed=embed)

    else:
        embed.add_field(
            name="Killing Old Bot Process (3/3)",
            value="Executing `sys.exit(0)` now...",
            inline=False,
        )
        await msg.edit(embed=embed)
        sys.exit(0)
