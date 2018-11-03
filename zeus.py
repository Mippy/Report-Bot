import discord
from discord.ext import commands
import asyncio
import json

bot = commands.AutoShardedBot(command_prefix='!', case_insensitive=True, activity=discord.Game(name='on Sky Kingdoms'), status=discord.Status.dnd)
bot.remove_command('help')

@bot.event
async def on_message(x):
    if x.author.id != 169275259026014208:
        if x.channel.id == 408777469290872843:
            if x.author.id != 408776943610363904:
                await x.delete()
            else:
                await asyncio.sleep(10)
                await x.delete()

with open('config.json') as fp:
    data = json.load(fp)
    token = data['token']

bot.run(token)
