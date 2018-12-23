import discord
from discord.ext import commands
import mysql.connector
import asyncio
import json
import random

fp = open('config.json')
data = json.load(fp)
token = data['token']
reportchannel = data['reportchannel']
queuechannel = data['queuechannel']
logchannel = data['logchannel']
dbname = data['database']
dbpassword = data['dbpassword']
serverid = data['server']
fp.close()

if serverid == 269112125316661248:
    servername = "Sky Kingdoms"
    forumsurl = 'https://www.skykingdoms.net'
if serverid == 260867503373156355:
    servername = "Project Wonder"
    forumsurl = 'https://eusurvival-mc.enjin.com'
if serverid == 508109177172918273:
    servername = "the testing server"
    forumsurl = 'forumsurl'

bot = commands.AutoShardedBot(command_prefix='!', case_insensitive=True, activity=discord.Game(name=f'on {servername}'), status=discord.Status.dnd)
bot.remove_command('help')

lrs = []
rs = []
qmr = []

def is_staff(user):
    server = bot.get_guild(int(serverid))
    helper = discord.utils.get(server.roles, name='Helper')
    moderator = discord.utils.get(server.roles, name='Moderator')
    admin = discord.utils.get(server.roles, name='Admin')
    owner = discord.utils.get(server.roles, name='Owner')
    user = server.get_member(user.id)
    if user in helper.members or user in moderator.members or user in admin.members or user in owner.members:
        return True
    return False

@bot.event
async def on_message(x):
    if x.author.id == bot.user.id:
        return
    if x.channel.id == 408777469290872843: # rank sync checkers
        if x.author.id != 408776943610363904 or x.author.id != 169275259026014208:
            await x.delete()
        elif x.author.id == 408776943610363904:
            await asyncio.sleep(10)
            await x.delete()
    if x.channel.id == 409739062182674432: # rank sync checkers
        if x.author.id != 409734806637641728 or x.author.id != 169275259026014208:
            await x.delete()
        elif x.author.id == 409734806637641728:
            await asyncio.sleep(10)
            await x.delete()
    else:
        if x.guild.id != serverid:
            return
        if x.author.id in lrs: # if the bot is expecting a response, don't do anything with the message here
            return
        if x.author.id in rs: # check if bot needs response to either a poll or a text question
            return await x.delete()
        if x.channel.id == queuechannel:
            return await x.delete()
        if x.channel.id == logchannel:
            return await x.delete()
        if x.channel.id == reportchannel and not x.content:
            await x.delete()
            cmdmsg = await x.channel.send(f'{x.author.mention}, to begin a report, try `!report`.')
            await asyncio.sleep(5)
            return await cmdmsg.delete()
        if x.channel.id == reportchannel and x.content.split()[0] != '!report': # if there's a message in #reports that isn't !report or a response
            await x.delete()
            cmdmsg = await x.channel.send(f'{x.author.mention}, to begin a report, try `!report`.')
            await asyncio.sleep(5)
            return await cmdmsg.delete()
        if x.channel.id == reportchannel and x.content.split()[0] == '!report':
            cnx = mysql.connector.connect(user='root', host='localhost', password=dbpassword, database=dbname)
            cursor = cnx.cursor()
            cursor.execute(f"SELECT * FROM blacklist WHERE id='{x.author.id}'")
            findata = []
            for data in cursor:
                findata.append(data)
            cursor.close()
            cnx.close()
            if findata:
                await x.delete()
                msg = await x.channel.send(f'{x.author.mention}, sorry! It looks like you\'ve been blocked from sending reports.\nYour report can be sent on the forums: {forumsurl}.')
                await asyncio.sleep(20)
                return await msg.delete()
        await bot.process_commands(x)

@bot.event
async def on_raw_reaction_add(payload):
    fp = open('config.json')
    data = json.load(fp)
    queuechannel = data['queuechannel']
    logchannel = data['logchannel']
    fp.close()
    emojiname = payload.emoji.name
    server = bot.get_guild(serverid)
    user = server.get_member(payload.user_id)
    if payload.channel_id != queuechannel:
        return
    if not is_staff(user):
        return
    if user.id in rs:
        return
    if payload.message_id in qmr:
        return
    def check(x, y):
        return (str(x.emoji) == '✅' or str(x.emoji) == '❌') and y.id == user.id
    cnx = mysql.connector.connect(user='root', host='localhost', password=dbpassword, database=dbname)
    cursor = cnx.cursor()
    cursor.execute(f"SELECT * FROM reports WHERE messageid='{payload.message_id}'")
    findata = []
    for data in cursor:
        findata.append(data)
    cursor.close()
    cnx.close()
    if findata:
        findata = findata
        channel = server.get_channel(queuechannel)
        message = await channel.get_message(payload.message_id)
        queuechannel = server.get_channel(queuechannel)
        logchannel = server.get_channel(logchannel)
        def check2(x):
            return x.author.id == user.id and x.channel.id == queuechannel.id
        if emojiname == '✅':
            rs.append(user.id)
            cmdmsg = await queuechannel.send(f'{user.mention}, it looks like you\'ve approved a report. Would you like to add a comment? (This will be sent to the user)')
            qmr.append(cmdmsg.id)
            await cmdmsg.add_reaction('✅')
            await cmdmsg.add_reaction('❌')
            try:
                reaction = await bot.wait_for('reaction_add', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                rs.remove(user.id)
                await cmdmsg.delete()
                try:
                    return await message.remove_reaction(emoji='✅', member=user)
                except: pass
            rs.remove(user.id)
            if str(reaction[0].emoji) == '✅':
                await cmdmsg.delete()
                cmdmsg = await queuechannel.send(f'{user.mention}, what is your comment?')
                try:
                    msg = await bot.wait_for('message', check=check2, timeout=120.0)
                except asyncio.TimeoutError:
                    await cmdmsg.delete()
                    try:
                        return await message.remove_reaction(emoji='✅', member=user)
                    except: pass
                comment = msg.content
                await cmdmsg.delete()
            if str(reaction[0].emoji) == '❌':
                comment = None
                await cmdmsg.delete()
            splitdata = message.content.split('The report above needs to be approved, or denied.')
            if not comment:
                logmessage = splitdata[0] + f"**Report approved by {user} ({user.mention}).** :white_check_mark:"
            else:
                logmessage = splitdata[0] + f"**Report approved by {user} ({user.mention}) with the comment `{comment}`.** :white_check_mark:"
            await logchannel.send(logmessage)
            await message.delete()
            try:
                await msg.delete()
            except: pass
            cmdmsg = await queuechannel.send(f'{user.mention} report successfully approved. :white_check_mark:')
            reporter = server.get_member(int(findata[0][1]))
            try:
                if not comment:
                    await reporter.send(f"Hey {reporter.mention},\nJust letting you know that your report against {findata[0][2]} has been APPROVED!\nThanks for helping us out!")
                else:
                    await reporter.send(f"Hey {reporter.mention},\nJust letting you know that your report against {findata[0][2]} has been APPROVED!\nThanks for helping us out!\n\nP.S.: The staff member that approved your report left this comment: `{comment}`.")
            except: pass
            await asyncio.sleep(15)
            return await cmdmsg.delete()
        elif emojiname == '❌':
            rs.append(user.id)
            cmdmsg = await queuechannel.send(f'{user.mention}, it looks like you\'ve denied a report. Would you like to add a comment? (This will be sent to the user)')
            qmr.append(cmdmsg.id)
            await cmdmsg.add_reaction('✅')
            await cmdmsg.add_reaction('❌')
            try:
                reaction = await bot.wait_for('reaction_add', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                rs.remove(user.id)
                await cmdmsg.delete()
                try:
                    return await message.remove_reaction(emoji='❌', member=user)
                except: pass
            rs.remove(user.id)
            if str(reaction[0].emoji) == '✅':
                await cmdmsg.delete()
                cmdmsg = await queuechannel.send(f'{user.mention}, what is your comment?')
                try:
                    msg = await bot.wait_for('message', check=check2, timeout=120.0)
                except asyncio.TimeoutError:
                    await cmdmsg.delete()
                    try:
                        return await message.remove_reaction(emoji='❌', member=user)
                    except: pass
                comment = msg.content
                await cmdmsg.delete()
            if str(reaction[0].emoji) == '❌':
                comment = None
                await cmdmsg.delete()
            splitdata = message.content.split('The report above needs to be approved, or denied.')
            if not comment:
                logmessage = splitdata[0] + f"**Report denied by {user} ({user.mention}).** :x:"
            else:
                logmessage = splitdata[0] + f"**Report denied by {user} ({user.mention}) with the comment `{comment}`.** :x:"
            await logchannel.send(logmessage)
            await message.delete()
            try:
                await msg.delete()
            except: pass
            cmdmsg = await queuechannel.send(f'{user.mention} report successfully denied. :white_check_mark:')
            reporter = server.get_member(int(findata[0][1]))
            try:
                if not comment:
                    await reporter.send(f"Hey {reporter.mention},\nJust letting you know that your report against {findata[0][2]} has been denied.\nThanks for trying to help us out, anyway! Good luck next time.")
                else:
                    await reporter.send(f"Hey {reporter.mention},\nJust letting you know that your report against {findata[0][2]} has been denied.\nThanks for trying to help us out, anyway! Good luck next time.\n\nP.S.: The staff member that denied your report left this comment: `{comment}`.")
            except: pass
            await asyncio.sleep(15)
            return await cmdmsg.delete()
    else:
        return

@bot.command()
async def report(ctx):
    reporter = ctx.author
    cmdmsg = ctx.message
    if ctx.channel.id != reportchannel:
        await ctx.message.delete()
        cmdmsg = await ctx.send(f'{reporter.mention}, please send your request in <#{reportchannel}> instead.')
        await asyncio.sleep(5)
        return await cmdmsg.delete()
    lrs.append(reporter.id)
    rs.append(reporter.id)
    await cmdmsg.delete()
    def check(x):
        return x.author.id == reporter.id and x.channel.id == ctx.channel.id
    def check2(x, y):
        return (str(x.emoji) == '✅' or str(x.emoji) == '❌') and y.id == reporter.id
    async def requestinfo(message, proof=""):
        cmdmsg = await ctx.send(f'{reporter.mention}\n\n**{message}**')
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
        except asyncio.TimeoutError:
            await cmdmsg.delete()
            msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
            lrs.remove(reporter.id)
            rs.remove(reporter.id)
            await asyncio.sleep(30)
            return await msg.delete()
        if message.startswith("P"):
            data = ''
            for attachment in msg.attachments:
                filehash = random.getrandbits(64)
                ext = attachment.filename.split('.')
                ext.reverse()
                ext = ext[0]
                await attachment.save(fp=f'/var/www/i.williamlomas.me/zeusuploads/{filehash}.{ext}')
                data = f'https://i.williamlomas.me/zeusuploads/{filehash}.{ext}'
                proof = data
                await cmdmsg.delete()
                await msg.delete()
                return proof
        else:
            if proof != "":
                data = data + f'\n{msg.content}'
            else:
                data = msg.content
            if message.startswith("What i"):
                data = data.split()
                data = data[0]
        if not data:
            data = msg.content
        await cmdmsg.delete()
        await msg.delete()
        return data

    async def requestproof(ctx, proof=""):
        async def requestupload(ctx, pr):
            proof = await requestinfo(f"Please upload proof of these offences happening. (link, or file upload)", proof=pr)
            if not proof:
                return
            return proof
        async def requestmore(ctx, pr):
            lrs.remove(reporter.id)
            cmdmsg = await ctx.send(f"{reporter.mention}\n\n**Do you have any additional proof?**")
            await cmdmsg.add_reaction('✅')
            await cmdmsg.add_reaction('❌')
            try:
                reaction = await bot.wait_for('reaction_add', check=check2, timeout=120.0)
            except asyncio.TimeoutError:
                await cmdmsg.delete()
                msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
                rs.remove(reporter.id)
                await asyncio.sleep(30)
                await msg.delete()
                return
            if str(reaction[0].emoji) == '✅':
                lrs.append(reporter.id)
                await cmdmsg.delete()
                pr = await requestproof(ctx, proof=pr)
                if not pr:
                    return
                pr = '\n' + proof + '\n' + pr
                return pr
            else:
                await cmdmsg.delete()
                return pr
        ru = await requestupload(ctx, proof)
        if not ru:
            return
        proof = ru
        proof = await requestmore(ctx, proof)
        return proof

    username = await requestinfo("What is the username of the person you are reporting?")
    if not username:
        return
    offenses = await requestinfo(f"What rules did `{username}` break?")
    if not offenses:
        return
    gamemode = await requestinfo(f"Which gamemode did this occur on?")
    if not gamemode:
        return
    proof = await requestproof(ctx)
    if not proof:
        return
    cmdmsg = await ctx.send(f'{reporter.mention}\n\n**Do you have any additional comments? (React accordingly)**')
    await cmdmsg.add_reaction('✅')
    await cmdmsg.add_reaction('❌')
    try:
        reaction = await bot.wait_for('reaction_add', check=check2, timeout=120.0)
    except asyncio.TimeoutError:
        await cmdmsg.delete()
        msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
        lrs.remove(reporter.id)
        rs.remove(reporter.id)
        await asyncio.sleep(30)
        return await msg.delete()
    if str(reaction[0].emoji) == '✅':
        lrs.append(reporter.id)
        await cmdmsg.delete()
        comments = await requestinfo("What are those additional comments?")
        lrs.remove(reporter.id)
        if not comments:
            return
    else:
        await cmdmsg.delete()
        comments = 'None'
    try:
        cmdmsg = await ctx.send(f'{reporter.mention}, **are you sure you would like to send this report to the staff team?:**\n\n**Username:** {username}\n**Offences:** {offenses}\n**Gamemode:** {gamemode}\n**Proof:** {proof}\n**Comments:** {comments}\n\nConfirmation here will send your report to the staff team.')
    except:
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(10)
        return await cmdmsg.delete()
    await cmdmsg.add_reaction('✅')
    await cmdmsg.add_reaction('❌')
    try:
        reaction = await bot.wait_for('reaction_add', check=check2, timeout=120.0)
    except asyncio.TimeoutError:
        await cmdmsg.delete()
        msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        await asyncio.sleep(30)
        return await msg.delete()
    if str(reaction[0].emoji) == '✅':
        await cmdmsg.delete()
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, thanks for your report!\nYou will receive updates about your report in a private message from me.')
        queue = ctx.guild.get_channel(queuechannel)
        qmsg = await queue.send(f'───────────────────\n**{reporter}** ({reporter.mention}) Reported:\n\n**Username:** {username}\n**Offences:** {offenses}\n**Gamemode:** {gamemode}\n**Proof:** {proof}\n**Additonal Comments:** {comments}\n\nThe report above needs to be approved, or denied.')
        await qmsg.add_reaction('✅')
        await qmsg.add_reaction('❌')
        cnx = mysql.connector.connect(user='root', host='localhost', password=dbpassword, database=dbname)
        cursor = cnx.cursor()
        sql = f"INSERT INTO reports (messageid,reporterid,defence) VALUES ('{qmsg.id}','{reporter.id}','{username}')"
        cursor.execute(sql)
        cnx.commit()
        cursor.close()
        cnx.close()
        await asyncio.sleep(20)
        await cmdmsg.delete()
    else:
        await cmdmsg.delete()
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, alright, your report has been closed. You can always open another using `!report`.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()

bot.run(token)
