import inspect
import io
import logging
import os
import textwrap
import traceback
from contextlib import redirect_stdout

import aiohttp
import discord
from core import database
from core.checks import is_botAdmin, is_botAdmin3, is_botAdmin4
from core.common import Emoji
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class CoreBotConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['f'])
    async def filter(self, ctx):
        pass

    @filter.command()
    @is_botAdmin4
    async def modify(self, ctx, num: int, val: bool):
        CheckDB : database.CheckInformation =  database.CheckInformation.select().where(database.CheckInformation.id == 1).get()
        
        databaseValues = {
            1: "CheckDB.MasterMaintenance",
            2: "CheckDB.guildNone",
            3: "CheckDB.externalGuild",
            4: "CheckDB.ModRoleBypass",
            5: "CheckDB.ruleBypass",
            6: "CheckDB.publicCategories",
            7: "CheckDB.elseSituation"
        }


        if num == 1:
            CheckDB.MasterMaintenance = val
            CheckDB.save()
        elif num == 2:
            CheckDB.guildNone = val
            CheckDB.save()
        elif num == 3:
            CheckDB.externalGuild = val
            CheckDB.save()
        elif num == 4:
            CheckDB.ModRoleBypass = val
            CheckDB.save()
        elif num == 5:
            CheckDB.ruleBypass = val
            CheckDB.save()
        elif num == 6:
            CheckDB.publicCategories = val
            CheckDB.save()
        elif num == 7:
            CheckDB.elseSituation = val
            CheckDB.save()
        else:
            return await ctx.send(f"Not a valid option\n```py\n{databaseValues}\n```")

            
        await ctx.send(f"Field: {databaseValues[num]} has been set to {str(val)}")



    @filter.command()
    async def list(self, ctx):
        CheckDB : database.CheckInformation =  database.CheckInformation.select().where(database.CheckInformation.id == 1).get()

        embed = discord.Embed(title = "Command Filters", description = "Bot Filters that the bot is subjected towards.", color = discord.Colour.gold())
        embed.add_field(name = "Checks", value = f"1) `Maintenance Mode`\n{Emoji.barrow} {CheckDB.MasterMaintenance}\n\n2) `NoGuild`\n{Emoji.barrow} {CheckDB.guildNone}\n\n3) `External Guilds`\n{Emoji.barrow} {CheckDB.externalGuild}\n\n4) `ModBypass`\n{Emoji.barrow} {CheckDB.ModRoleBypass}\n\n5) `Rule Command Bypass`\n{Emoji.barrow} {CheckDB.ruleBypass}\n\n6) `Public Category Lock`\n{Emoji.barrow} {CheckDB.publicCategories}\n\n7) `Else Conditions`\n{Emoji.barrow} {CheckDB.elseSituation}")
        await ctx.send(embed = embed)



def setup(bot):
    bot.add_cog(CoreBotConfig(bot))
