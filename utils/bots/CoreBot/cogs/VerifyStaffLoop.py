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
        #TODO: Make useable for rolesync and different servers
    
    def cog_unload(self):
        pass


    @tasks.loop(seconds=10)
    async def verifyStaff(self):
        responses = SQS_CRED.sqs_client.receive_message(
            QueueUrl=SQS_CRED.SQS_URL,
            AttributeNames=[
                'All'
            ],
            MessageAttributeNames=[
                'All'
            ],
            MaxNumberOfMessages=1,
            VisibilityTimeout=0,
            WaitTimeSeconds=1
        )
        guild = TECH_ID.g_tech
        
        try:
            for message in responses["Messages"]:

                user_data = json.loads(message["Body"])
                user_data = user_data["MessageAttributes"]

                discord_id = int(user_data["discord_id"]["StringValue"])
                email = user_data["email"]["StringValue"]
                first = user_data["first"]["StringValue"]
                last = user_data["last"]["StringValue"]


                embed = discord.Embed(title = "Authentication Successful", description = f"Hello {first}, you have successfully authenticated with your GSuite account, {email}.", color = discord.Color.green())
                embed.set_footer(text = "Assigning you your staff role.")

                user_id = int(discord_id)

                member: discord.Member = guild.get_member(user_id)
                DMChannel = await member.create_dm()
                DMChannel.send(embed = embed)

                role = guild.get_role(self.staffrole)
                await member.add_roles(role, reason=f"Passed authentication: {email}")

                now = datetime.now()
                now = now.astimezone(pytz.timezone('US/Eastern')).strftime('%m/%d/%Y %I:%-M %p')
                logchannel: discord.TextChannel = await self.bot.fetch_channel(self.logchannel)

                embed = discord.Embed(title = "GSuite Authentication", description = f"{member.mention} has successfully authenticated with their GSuite account.", color = discord.Color.green())
                embed.add_field(name = "Verification Details", value = "**Name:** {}\n**Email:** {}\n**Date:** {} EST".format(f"{first} {last}", email, now))
                embed.set_footer(text = "This action was performed by {}".format(member.display_name))
                await logchannel.send(embed=embed)

                
                SQS_CRED.sqs_client.delete_message(QueueUrl=SQS_CRED.SQS_URL,ReceiptHandle=message["ReceiptHandle"])
        
        except KeyError:
            pass