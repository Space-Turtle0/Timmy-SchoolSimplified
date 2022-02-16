import asyncio
from datetime import datetime
import os

import discord
import pytz
from core.checks import is_botAdmin
from core.common import ButtonHandler, Emoji, GSuiteVerify
from discord.ext import commands
from google_auth_oauthlib.flow import Flow

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

class GSuiteLogin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.flow  = Flow.from_client_secrets_file(
            'gsheetsadmin/staff_verifyClient.json',
            scopes=['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        self.staffrole = 932066545117585430
        self.logchannel = 932066545885134904
        self.est = pytz.timezone("US/Eastern")
        self.verify_link = "https://timmy-gsuite-verify.vercel.app" #TODO: Add real link

    @commands.Cog.listener("on_interaction")
    async def GSuiteVerify(self, interaction: discord.Interaction):
        InteractionResponse = interaction.data
        if interaction.message is None:
            return

        try:
            val = InteractionResponse["custom_id"]
        except KeyError:
            return

        if (
            InteractionResponse["custom_id"] == "persistent_view:gsuiteverify"
        ):
          
            channel = await self.bot.fetch_channel(interaction.channel_id)
            guild = interaction.message.guild
            author = interaction.user
            DMChannel = await author.create_dm()

            auth_url = self.verify_link + "?discordID=" + str(author.id)
            #auth_url = auth_url.replace('auth', 'auth/oauthchooseaccount', 1)
            embed = discord.Embed(title = "GSuite Verification", description = "Click on the button below and sign in with your **personal** @schoolsimplified.org account.", color = discord.Color.red())
            embed.add_field(name = "Getting Error Code '403: org_internal'?", value = "Make sure you sign in with your @schoolsimplified.org **Google Account**. If you are immediately being redirected to that webpage, make sure you sign in on your browser first and then try clicking the verification button again. ")
            
            
            view = discord.ui.View()
            emoji = Emoji.timmyBook
            view.add_item(
                ButtonHandler(
                    style=discord.ButtonStyle.green,
                    url=auth_url,
                    disabled=False,
                    label="Click here to sign in with your GSuite account!",
                    emoji=emoji,
                )
            )
            await DMChannel.send(embed=embed, view=view)
            

            

    @commands.command()
    @is_botAdmin
    async def pasteGSuiteButton(self, ctx):
        embed = discord.Embed(title = "Alternate Verification Method", description = "If you have a @schoolsimplified.org Google Account, choose this method to get immediately verified.", color = discord.Color.green())
        GSuiteButton = GSuiteVerify()
        await ctx.send(embed=embed ,view=GSuiteButton)

def setup(bot):
    bot.add_cog(GSuiteLogin(bot))
