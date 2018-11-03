import discord
from discord.ext import commands
import mysql.connector
import asyncio
import json

with open('config.json') as fp:
    data = json.load(fp)
    token = data['token']
    reportchannel = data['reportchannel']

bot = commands.AutoShardedBot(command_prefix='!', case_insensitive=True, activity=discord.Game(name='on Sky Kingdoms'), status=discord.Status.dnd)
bot.remove_command('help')

lrs = []

@bot.event
async def on_message(x):
    if x.author.id == bot.user.id:
        return
    if x.channel.id == 408777469290872843:
        if x.author.id != 408776943610363904 or x.author.id != 169275259026014208:
            await x.delete()
        elif x.author.id != 408776943610363904:
            await asyncio.sleep(10)
            await x.delete()
    else:
        if x.author.id in lrs:
            return
        if x.channel.id == reportchannel and not x.content.startswith('!report'):
            await x.delete()
        else:
            await bot.process_commands(x)

@bot.command()
async def report(ctx):
    reporter = ctx.author
    cmdmsg = ctx.message
    lrs.append(reporter.id)
    if ctx.channel.id != reportchannel:
        return await ctx.send(f'{reporter.mention}, please send your request in <#{reportchannel}> instead.')
    await cmdmsg.delete()
    def check(x):
        return x.author.id == reporter.id and x.channel.id == ctx.channel.id
    def check2(x, y):
        return str(x.emoji) == '✅' or str(x.emoji) == '❌' and y.id == reporter.id
    async def requestinfo(message):
        cmdmsg = await ctx.send(f'{reporter.mention}\n\n**{message}**')
        try:
            msg = await bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await cmdmsg.delete()
            msg = await ctx.send(f'{reporter.mention}, since it has been over a minute without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
            lrs.remove(reporter.id)
            await asyncio.sleep(30)
            return await msg.delete()
        data = msg.content
        await cmdmsg.delete()
        await msg.delete()
        return data

    username = await requestinfo("What is the username of the person you are reporting?")
    offenses = await requestinfo(f"What rules did `{username}` break?")
    proof = await requestinfo(f"Please paste your proof of these offenses occuring in a link format.")
    cmdmsg = await ctx.send(f'{reporter.mention}\n\n**Do you have any additional comments? (React accordingly)**')
    lrs.remove(reporter.id)
    await cmdmsg.add_reaction('✅')
    await cmdmsg.add_reaction('❌')
    try:
        reaction = await bot.wait_for('reaction_add', check=check2, timeout=60.0)
    except asyncio.TimeoutError:
        await cmdmsg.delete()
        msg = await ctx.send(f'{reporter.mention}, since it has been over a minute without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
        lrs.remove(reporter.id)
        await asyncio.sleep(30)
        return await msg.delete()
    if str(reaction[0].emoji) == '✅':
        lrs.append(reporter.id)
        await cmdmsg.delete()
        comments = await requestinfo("What are those additional comments?")
    else:
        await cmdmsg.delete()
        comments = 'None'
    await ctx.send(username + '\n' + offenses + '\n' + proof + '\n' + comments) # debug stuff
    lrs.remove(reporter.id)

bot.run(token)
