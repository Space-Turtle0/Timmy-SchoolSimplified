import json
import boto3
import os
from datetime import datetime

import discord
import pytz
from discord.ext import commands, tasks
from core.common import TECH_ID
from dotenv import load_dotenv

load_dotenv()

class SQS_CRED:
    sqs_client = boto3.client(
        "sqs",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1",
    )
    sqs = boto3.resource(
        "sqs",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1",
    )
    SQS_URL = "https://sqs.us-east-1.amazonaws.com/583903076756/TimmySSO"






class VerifyStaffLoop:
    def __init__(self, bot):
        self.bot = bot
        self.verifyStaff.start()
        self.staffrole = 932066545117585430
        self.logchannel = 932066545885134904
        #TODO: Make userable for rolesync and different servers
    
    def cog_unload(self):
        pass


    @tasks.loop(seconds=10)
    async def verifyStaff(self):
        responses = SQS_CRED.sqs_client.receive_message(
            QueueUrl=SQS_CRED.SQS_URL,
            AttributeNames=[
                'All'
            ],
            MaxNumberOfMessages=10,
            VisibilityTimeout=123,
        )
        guild = TECH_ID.g_tech
        

        for message in responses["Messages"]:

            user_data = json.loads(message["Body"])
            
            embed = discord.Embed(title = "Authentication Successful", description = f"Hello {user_data['name']}, you have successfully authenticated with your GSuite account, {user_data['email']}.", color = discord.Color.green())
            embed.set_footer(text = "Assigning you your staff role.")

            user_id = int(user_data["discordID"])

            member: discord.Member = guild.get_member(user_id)
            role = guild.get_role(self.staffrole)
            await member.add_roles(role, reason=f"Passed authentication: {user_data['email']}")

            now = datetime.now()
            now = now.astimezone(pytz.timezone('US/Eastern')).strftime('%m/%d/%Y %I:%-M %p')
            logchannel: discord.TextChannel = await self.bot.fetch_channel(self.logchannel)

            embed = discord.Embed(title = "GSuite Authentication", description = f"{member.mention} has successfully authenticated with their GSuite account.", color = discord.Color.green())
            embed.add_field(name = "Verification Details", value = "**Name:** {}\n**Email:** {}\n**Date:** {} EST".format(f"{user_data['name']} {user_data['lastName']}", user_data['email'], now))
            embed.set_footer(text = "This action was performed by {}".format(member.display_name))
            await logchannel.send(embed=embed)

            
            response = SQS_CRED.sqs_client.delete_message(
                QueueUrl=SQS_CRED.SQS_URL,ReceiptHandle=message["ReceiptHandle"])