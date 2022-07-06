import discord
from discord.ext import commands
import re
import json
import arrow
import random
import smtplib
import requests
import mysql.connector
from ics import Calendar
from bs4 import BeautifulSoup

# Initialize config/secret vars
c = open('config.json')
s = open('secret.json')
ss = open('subjects.json')

config = json.load(c)
secret = json.load(s)
subjects = json.load(ss)

c.close()
s.close()
ss.close()

PREFIX = config['BOT_COMMAND_PREFIX']
TOKEN = secret['BOT_TOKEN']
EMAIL = config['BOT_EMAIL']
EMAIL_PASS = secret['BOT_EMAIL_PASS']
SQL_USER = config['SQL_USER']
SQL_PASS = secret['SQL_PASS']
DB_NAME = config['SQL_DB_NAME']
USER_TBL_NAME = config['SQL_USER_TBL_NAME']

# Checks DB for registration val lookup from discord_user_id (duid)
async def is_registered(ctx, duid):
    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute('SELECT COUNT(1) '
                    f'FROM {USER_TBL_NAME} '
                    f'WHERE discord_user_id = {duid}')
            
        match_num = int(cur.fetchone()[0])

        if match_num != 0:
            return True
        else:
            return False
    except Exception as e:
        await ctx.send(f'Something went wrong while checking for user registration. {e}')
        return 404

# Checks DB if user is_verif = 1 by val comparison from discord_user_id (duid)
async def is_verified(ctx, duid):
    is_reg = await is_registered(ctx, duid)
    if (not is_reg):
        return False

    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute('SELECT is_verif '
                    f'FROM {USER_TBL_NAME} '
                    f'WHERE discord_user_id = {duid}')
            
        val = int(cur.fetchone()[0])

        if val == 0:
            return False
        elif val == 1:
            return True
    except Exception as e:
        await ctx.send(f'Something went wrong while checking for user verification. {e}')
        return 404

bot = commands.Bot(command_prefix=PREFIX, help_command=None)

# Sends embed w/ list of commands (command syntax, arguments, + description)
@bot.command()
async def help(ctx):
    title = 'Command Help Menu'
    description = (f'`{PREFIX}help` - Produces this menu for command descriptions and syntax.\n'
                   f'`{PREFIX}register <net_id>` - Register your NetID with the bot to verify yourself.\n'
                   f'`{PREFIX}verify <verif_code>` - Verifies user if correct verification code is passed.\n'
                   f'`{PREFIX}is_verified <@user>` - Checks if a user has verified their NetID.\n'
                   f'`{PREFIX}course <subject_code> <course_num>` - Returns info about a specified course.\n'
                   f'`{PREFIX}calendar <event_num>` - Lists chosen number of school events from now.')
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

# Initiates registration process w/ email verification (paired w/ verify command for verif completion)
@bot.command()
async def register(ctx, net_id):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (is_ver):
        await ctx.send('You can\'t register if you are already verified.')
        return

    domain = 'smtp.gmail.com'
    port = 587
    with smtplib.SMTP(domain, port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL, EMAIL_PASS)

        sender_email = EMAIL
        receiver_email = f'{net_id}@tamu.edu'
        verif_code = random.randint(100000, 999999)
        
        # Updates user DB records w/ new verif_code and net_id if is_registered, adds new user record to DB if not
        if (is_reg):
            try:
                db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
                cur = db.cursor()
                cur.execute(f'UPDATE {USER_TBL_NAME} '
                            f'SET net_id = \'{net_id}\', verif_code = {verif_code} '
                            f'WHERE discord_user_id = {discord_user_id}')

                db.commit()
            except Exception as e:
                await ctx.send(f'Something went wrong while updating user record in database. {e}')
                return
        else:
            try:
                db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
                cur = db.cursor()
                cur.execute(f'INSERT INTO {USER_TBL_NAME} (discord_user_id, net_id, verif_code, is_verif) '
                            f'VALUES ({discord_user_id}, \'{net_id}\', {verif_code}, 0)')

                db.commit()
            except Exception as e:
                await ctx.send(f'Something went wrong while adding user record to database. {e}')
                return

        # Makes + sends verification email to user TAMU email address via SMTP
        try:
            subject = 'Reveille Bot - Identity Verification'
            body = f'Your verification code is {verif_code}.\n\nIn order to finish verifying, go back to Discord and DM the bot, Reveille, with the following command:\n\n{PREFIX}verify {verif_code}'
            msg = f'Subject: {subject}\n\n{body}'

            smtp.sendmail(sender_email, receiver_email, msg)
            if (is_reg):
                await ctx.send(f'You\'ve already a registered user in the database. An email with a new verification code has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration and verify, please DM me, Reveille, your verification code in the form of the command `{PREFIX}verify <verif_code>`.\n\nMake sure to check your spam if you\'re having trouble!')
            else:
                await ctx.send(f'An email with a verification code has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration and verify, please DM me, Reveille, your verification code in the form of the command `{PREFIX}verify <verif_code>`.\n\nMake sure to check your spam if you\'re having trouble!')
        except Exception as e:
            await ctx.send(f'Something went wrong while sending verification email. {e}')
            return

# Verifies users w/ DB verif_code val lookup comparison, updates is_verif val to 1 if code match
@bot.command()
async def verify(ctx, verif_code):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t verify if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (is_ver):
        await ctx.send('You can\'t verify if you are already verified.')
        return
    
    # Checks if true verif code = given verif code, terminates if not
    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute('SELECT verif_code '
                    f'FROM {USER_TBL_NAME} '
                    f'WHERE discord_user_id = {discord_user_id}')
            
        true_verif_code = int(cur.fetchone()[0])

        if (true_verif_code != int(verif_code)):
            await ctx.send('Incorrect verification code. Ensure you\'re using proper command syntax and your typed code matches the emailed code.')
            return
    except Exception as e:
        await ctx.send(f'Something went wrong while checking user verification code. {e}')
        return
    
    # Updates user is_verif to 1 in DB
    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute(f'UPDATE {USER_TBL_NAME} '
                    f'SET is_verif = 1 '
                    f'WHERE discord_user_id = {discord_user_id}')

        db.commit()
    except Exception as e:
        await ctx.send(f'Something went wrong while verifying user. {e}')
        return
    
    await ctx.send('You\'ve successfully verified! You now have full server/bot functionality.')
    return

# Checks is a user is verified in DB
@bot.command(name='is_verified')
async def is_user_verified(ctx, member : discord.Member):
    is_ver = await is_verified(ctx, member.id)
    if (is_ver == 404):
        return
    elif (is_ver):
        await ctx.send(f'{member.mention} is verified.')
    else:
        await ctx.send(f'{member.mention} is not verified.')

# Displays info embed for specified course using TAMU catalog search
@bot.command()
async def course(ctx, subject_code, course_num):
    SUBJECT_NAME = subjects[f'{subject_code.upper()}']

    search_url = f'https://catalog.tamu.edu/search/?search={subject_code.upper()}+{course_num}'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    course_html = soup.find(class_='searchresult search-courseresult')

    course_name = course_html.find('h2').text
    course_hrs = course_html.find(class_='hours noindent').text.strip()
    course_desc = course_html.find(class_='courseblockdesc').text.strip()

    hours_parts = [x.strip() for x in course_hrs.split('\n') if x != '']
    course_cred = f'{" ".join(hours_parts[0].split(" ")[1:]).split(".")[0]} {hours_parts[0].split(" ")[0].lower()}'
    course_hrs_info = '\n'.join(hours_parts[1:])

    has_prereq = False

    prereq = re.search(r'Prerequisite(s)?: ([^.]+).', course_desc)
    if prereq != None:
        has_prereq = True
        prereq_str = prereq.group().strip()
        prereq_sentence = f'**{prereq_str.split(" ")[0]}** {" ".join(prereq_str.split(" ")[1:])}'
        course_desc = f'{course_desc.replace(prereq_str, "")}\n\n{prereq_sentence}'
    
    clist = re.search(r'Cross Listing(s)?: ([^.]+).', course_desc)
    if clist != None:
        clist_str = clist.group().strip()
        clist_sentence = f'**{" ".join(clist_str.split(" ")[0:2])}** {" ".join(clist_str.split(" ")[2:])}'
        if has_prereq:
            course_desc = f'{course_desc.replace(clist_str, "")}\n{clist_sentence}'
        else:
            course_desc = f'{course_desc.replace(clist_str, "")}\n\n{clist_sentence}'

    title = f'__{course_name}__ ({course_cred})'
    description = f'**{SUBJECT_NAME}**\n{course_desc}\n\n{course_hrs_info}'

    embed = discord.Embed(title=title, description=description, color=0x500000)

    await ctx.send(embed=embed)
    return

# Sends first event_num calendar events in the TAMU academic calendar from now
@bot.command()
async def calendar(ctx, event_num):
    calendar_url = 'https://registrar.tamu.edu/Catalogs,-Policies-Procedures/Academic-Calendar/Second-Fall/Download-Calendar'
    ics_str = requests.get(calendar_url, verify=False).text
    calendar = Calendar(ics_str)

    now = arrow.utcnow()
    events = list(calendar.timeline.start_after(now.shift(days=-1)))

    index = 0
    for event in events:
        if index == int(event_num):
            return

        index = index + 1

        title = event.name
        description = "".join(x for x in event.description.split('\n')[0] if ord(x) < 128)
        color = 0x500000
        footer = event.begin.format("MMMM DD")

        if event.begin.day != event.end.shift(minutes=-1).day:
            footer = f'{event.begin.format("MMMM DD")} - {event.end.shift(minutes=-1).format("MMMM DD")}'

        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=footer)

        await ctx.send(embed=embed)
    return

bot.run(TOKEN)
