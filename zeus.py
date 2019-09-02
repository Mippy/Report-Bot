import discord
from discord.ext import commands
import mysql.connector
import asyncio
import json
import random
from datetime import datetime
import re
import os

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

bot = commands.AutoShardedBot(command_prefix='!', case_insensitive=True, activity=discord.Activity(type=discord.ActivityType.watching, name=f'the reports come in'), status=discord.Status.dnd)
bot.remove_command('help')

lrs = []
rs = []
qmr = []

async def is_staff(user):
    server = bot.get_guild(int(serverid))
    helper = discord.utils.get(server.roles, name='Helper')
    moderator = discord.utils.get(server.roles, name='Moderator')
    admin = discord.utils.get(server.roles, name='Admin')
    owner = discord.utils.get(server.roles, name='Owner')
    user = await server.fetch_member(user.id)
    if user in helper.members or user in moderator.members or user in admin.members or user in owner.members or user.id == 617450312625684523:
        return True
    return False

@bot.event
async def on_message(x):
    if x.author.id == bot.user.id:
        return
    if x.channel.id == 408777469290872843: # rank sync checkers
        if x.author.id != 408776943610363904 or x.author.id != 617450312625684523:
            await x.delete()
        elif x.author.id == 408776943610363904:
            await asyncio.sleep(10)
            await x.delete()
    if x.channel.id == 409739062182674432: # rank sync checkers
        if x.author.id != 409734806637641728 or x.author.id != 617450312625684523:
            await x.delete()
        elif x.author.id == 409734806637641728:
            await asyncio.sleep(10)
            await x.delete()
    else:
        if x.guild and x.guild.id != serverid:
            return
        if x.author.id in lrs and x.channel.id == reportchannel: # if the bot is expecting a response, don't do anything with the message here
            return
        if x.author.id in rs and x.channel.id == reportchannel: # check if bot needs response to either a poll or a text question
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
                msg = await x.channel.send(f'{x.author.mention}, sorry! It looks like you\'ve been blocked from sending reports.\nMessage a staff member to submit a report.')
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
    user = await server.fetch_member(payload.user_id)
    if payload.channel_id != queuechannel:
        return
    if not await is_staff(user):
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
        message = await channel.fetch_message(payload.message_id)
        queuechannel = server.get_channel(queuechannel)
        logchannel = server.get_channel(logchannel)
        reportembed = message.embeds[0]
        def check2(x):
            return x.author.id == user.id and x.channel.id == queuechannel.id
        if emojiname == '✅':
            rs.append(user.id)
            reportembed.set_footer(text='Report approved')
            reportembed.title = 'Report Approved'
            cmdmsg = await queuechannel.send(f'{user.mention}, it looks like you\'ve approved a report. Would you like to add a comment? (This will be sent to the user.)\n\nIf you did not mean to do this: Do not touch other options, wait a minute and it will be reverted.')
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
            if not comment:
                c = f"**The report below was approved by {user} ({user.mention}).** :white_check_mark:"
            else:
                c = f"**The report below was approved by {user} ({user.mention}) with the comment `{comment}`.** :white_check_mark:"
            await logchannel.send(c, embed=reportembed)
            await message.delete()
            try:
                await msg.delete()
            except: pass
            cmdmsg = await queuechannel.send(f'{user.mention} report successfully approved. :white_check_mark:')
            reporter = await server.fetch_member(int(findata[0][1]))
            try:
                if not comment:
                    await reporter.send(f"Your report against `{findata[0][2]}` has been approved.\nThanks for helping us out!")
                else:
                    await reporter.send(f"Your report against `{findata[0][2]}` has been approved!\nThanks for helping us out!\n\nP.S.: The staff member that approved your report left this comment: `{comment}`.")
            except: pass
            await asyncio.sleep(15)
            return await cmdmsg.delete()
        elif emojiname == '❌':
            rs.append(user.id)
            reportembed.set_footer(text='Report denied')
            reportembed.title = 'Report Denied'
            cmdmsg = await queuechannel.send(f'{user.mention}, it looks like you\'ve denied a report. Would you like to add a comment? (This will be sent to the user.)\n\nIf you did not mean to do this: Do not touch other options, wait a minute and it will be reverted.')
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
            if not comment:
                c = f"**The report below was denied by {user} ({user.mention}).** :x:"
            else:
                c = f"**The report below was denied by {user} ({user.mention}) with the comment `{comment}`.** :x:"
            await logchannel.send(c, embed=reportembed)
            await message.delete()
            try:
                await msg.delete()
            except: pass
            cmdmsg = await queuechannel.send(f'{user.mention} report successfully denied. :white_check_mark:')
            reporter = await server.fetch_member(int(findata[0][1]))
            try:
                if not comment:
                    await reporter.send(f"Your report against `{findata[0][2]}` has been denied.\nThanks for trying to help us out anyway!")
                else:
                    await reporter.send(f"Your report against `{findata[0][2]}` has been denied.\nThanks for trying to help us out anyway!\n\nP.S.: The staff member that denied your report left this comment: `{comment}`.")
            except: pass
            await asyncio.sleep(15)
            return await cmdmsg.delete()
    else:
        return

@bot.command()
async def restart(ctx):
    m = ctx.message
    u = ctx.author
    c = await is_staff(u)
    if not c:
        try:
            await m.delete()
        except: pass
        m = await ctx.send(f'{u.mention}, you do not have permission for this command.')
        await asyncio.sleep(5)
        return await m.delete()
    os.system('python3.6 zeus.py &')
    await bot.logout()

@bot.command()
async def report(ctx):
    reporter = ctx.author
    cmdmsg = ctx.message
    if ctx.channel.id != reportchannel:
        try:
            await cmdmsg.delete()
        except: pass
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
    async def requestinfo(message, previewmessage, proof=""):
        cmdmsg = await ctx.send(f'{reporter.mention}\n\n**{message}**')
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
        except asyncio.TimeoutError:
            await cmdmsg.delete()
            msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
            lrs.remove(reporter.id)
            rs.remove(reporter.id)
            await previewmessage.delete()
            await asyncio.sleep(30)
            return await msg.delete()
        if message.startswith("P"):
            data = ''
            for attachment in msg.attachments:
                filehash = random.getrandbits(64)
                ext = attachment.filename.split('.')
                ext.reverse()
                ext = ext[0]
                await attachment.save(fp=f'/var/www/zeusuploads/{filehash}.{ext}')
                data = f'https://zeusuploads-i.sabel.dev/{filehash}.{ext}'
                await cmdmsg.delete()
                await msg.delete()
                return data
        data = msg.content
        if not data:
            if not message.startswith("That's not"):
                message = f"That's not the data I was looking for. Try again?\n\n{message}"
            await cmdmsg.delete()
            await msg.delete()
            return await requestinfo(message, previewmessage)
        if not re.match('^[a-zA-Z0-9$%#()[\]<>+-="\'/:.,@_|?!šŠčČžŽ& ]*$', data):
            if not message.startswith("That's not"):
                message = f"That's not the data I was looking for. Try again?\n\n{message}"
            await cmdmsg.delete()
            await msg.delete()
            return await requestinfo(message, previewmessage)
        await cmdmsg.delete()
        await msg.delete()
        return data

    async def requestproof(ctx, previewmessage, proof=""):
        async def requestupload(ctx, pr, previewmessage):
            proof = await requestinfo(f"Please upload proof of these offences happening. (link, or file upload)", previewmessage, proof=pr)
            if not proof:
                return
            return proof
        async def requestmore(ctx, pr, previewmessage):
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
                pr = await requestproof(ctx, previewmessage, proof=pr)
                if not pr:
                    return
                pr = proof + pr
                return pr
            else:
                await cmdmsg.delete()
                return pr
        ru = await requestupload(ctx, proof, previewmessage)
        if not ru:
            return
        proof = '\n- ' + ru
        proof = await requestmore(ctx, proof, previewmessage)
        return proof

    epreview = discord.Embed(color=0x448cff, title='Report Preview', description=f'Reported by {reporter} ({reporter.mention})')
    epreview.add_field(name='Username', value='???', inline=False)
    epreview.add_field(name='Offence', value='???', inline=False)
    epreview.add_field(name='Gamemode', value='???', inline=False)
    epreview.add_field(name='Proof', value='???', inline=False)
    epreview.add_field(name='Comments', value='???', inline=False)
    epreview.timestamp = datetime.utcnow()
    preview = await ctx.send(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    username = await requestinfo("What is the username of the person you are reporting?", preview)
    if not username:
        return
    epreview.set_field_at(0, name='Username', value=username, inline=False)
    try:
        await preview.edit(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    except:
        await preview.delete()
        lrs.remove(reporter.id)
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()
    offenses = await requestinfo(f"What rules did `{username}` break?", preview)
    if not offenses:
        return
    epreview.set_field_at(1, name='Offence', value=offenses, inline=False)
    try:
        await preview.edit(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    except:
        await preview.delete()
        lrs.remove(reporter.id)
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()
    gamemode = await requestinfo(f"Which gamemode did this occur on?", preview)
    if not gamemode:
        return
    epreview.set_field_at(2, name='Gamemode', value=gamemode, inline=False)
    try:
        await preview.edit(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    except:
        await preview.delete()
        lrs.remove(reporter.id)
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()
    proof = await requestproof(ctx, preview)
    if not proof:
        return
    epreview.set_field_at(3, name='Proof', value=proof, inline=False)
    try:
        await preview.edit(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    except:
        await preview.delete()
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()
    cmdmsg = await ctx.send(f'{reporter.mention}\n\n**Would you like to add a comment? (React accordingly)**')
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
        comments = await requestinfo("What is the comment?", preview)
        lrs.remove(reporter.id)
        if not comments:
            return
    else:
        await cmdmsg.delete()
        comments = 'None'
    epreview.set_field_at(4, name='Comments', value=comments, inline=False)
    try:
        await preview.edit(embed=epreview, content=f'**Report Preview**: {reporter.mention}')
    except:
        await preview.delete()
        lrs.remove(reporter.id)
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, it appears your report is too long. Please rephrase your report so it may be submitted properly.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()
    cmdmsg = await ctx.send(f'{reporter.mention}, **are you sure you would like to send the report? A preview can be found above.**\n\nConfirmation here will send your report to the staff team.')
    await cmdmsg.add_reaction('✅')
    await cmdmsg.add_reaction('❌')
    try:
        reaction = await bot.wait_for('reaction_add', check=check2, timeout=120.0)
    except asyncio.TimeoutError:
        await preview.delete()
        await cmdmsg.delete()
        msg = await ctx.send(f'{reporter.mention}, since it has been over a couple minutes without a response, this report has been closed automatically.\nYou can always open another with `!report`.')
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        await asyncio.sleep(30)
        return await msg.delete()
    if str(reaction[0].emoji) == '✅':
        await preview.delete()
        await cmdmsg.delete()
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, thanks for your report!\nYou will receive updates about your report in a private message from me.')
        queue = ctx.guild.get_channel(queuechannel)
        epreview.title = 'Report'
        epreview.timestamp = datetime.utcnow()
        epreview.set_footer(text='The above report needs to be approved or denied.')
        try:
            await reporter.send(content='For your reference, here is a copy of the report you just submitted:', embed=epreview)
        except: pass
        qmsg = await queue.send(embed=epreview)
        await qmsg.add_reaction('✅')
        await qmsg.add_reaction('❌')
        cnx = mysql.connector.connect(user='root', host='localhost', password=dbpassword, database=dbname)
        cursor = cnx.cursor()
        sql = "INSERT INTO reports (messageid,reporterid,defence) VALUES ('%s','%s',%s)"
        cursor.execute(sql, (qmsg.id, reporter.id, username))
        cnx.commit()
        cursor.close()
        cnx.close()
        await asyncio.sleep(20)
        await cmdmsg.delete()
    else:
        await preview.delete()
        await cmdmsg.delete()
        try:
            lrs.remove(reporter.id)
        except: pass
        rs.remove(reporter.id)
        cmdmsg = await ctx.send(f'{reporter.mention}, alright, your report has been closed. You can always open another using `!report`.')
        await asyncio.sleep(20)
        return await cmdmsg.delete()

bot.run(token)
