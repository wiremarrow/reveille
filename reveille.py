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
COURSE_TBL_NAME = config['SQL_COURSE_TBL_NAME']
WELC_CHNL_ID = config['WELC_CHANNEL_ID']

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

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, help_command=None, intents=intents)

# Automatic welcome message for new member joins
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELC_CHNL_ID)

    await channel.send(f'Welcome to the Texas A&M 2026+ Discord, {member.mention}! To see the rest of the server, please introduce yourself with your name/nickname, major/school, year.')
    return

# Sends embed w/ list of commands (command syntax, arguments, + description)
@bot.command()
async def help(ctx):
    title = 'Command Help Menu'
    description = (f'`{PREFIX}help` - Produces this menu for command descriptions and syntax.\n'
                   f'`{PREFIX}register <net_id>` - Register your NetID with the bot to verify yourself.\n'
                   f'`{PREFIX}verify <verif_code>` - Verifies user if correct verification code is passed.\n'
                   f'`{PREFIX}is_verified <@user>` - Checks if a user has verified their NetID.\n'
                   f'`{PREFIX}course <subject_code> <course_num>` - Returns info about a specified course.\n'
                   f'`{PREFIX}calendar <event_num>` - Lists chosen number of school events from now.\n'
                   f'`{PREFIX}search <search_num> <*terms>` - Shows chosen number of results for search terms.\n'
                   f'`{PREFIX}resources` - Displays school resources with descriptions and hyperlinks.')
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)
    return

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

# Returns information for search terms from TAMU directory search
@bot.command()
async def search(ctx, search_num, *terms):
    search_url = f'https://directory.tamu.edu/?branch=people&cn={"+".join(terms)}'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    profile = soup.find_all(class_='link--secondary link--hollow-maroon')

    index = 0
    for ss in profile:
        if index == int(search_num):
            return

        index = index + 1

        profile_url = f'https://directory.tamu.edu/{ss["href"]}'
        html2_str = requests.get(profile_url).content
        soup = BeautifulSoup(html2_str, 'html.parser')

        res = soup.find(class_='result-listing')
        name = f'__{res.find("h2").text}__'
        contact = res.find(class_='contact-info')
        add_info = res.find(class_='additional-info')

        person_title = re.search(r'<strong>(.*)<\/strong>', str(contact))
        if person_title is not None:
            person_title = person_title.group(1)
        email = re.search(r'<a href="mailto:(.*@tamu.edu)">', str(contact))
        if email is not None:
            email = email.group(1)
        phone = re.search(r'<br\/>[\s\S]*(\(\d{3}\) \d{3}-\d{4}).*<br\/>', str(contact))
        if phone is not None:
            phone = phone.group(1)

        address = ''

        part_two = contact.find_all('p')
        if len(part_two) >= 2:
            address_parts = re.search(r'<p>[\s]*(.*)[\s]*<\/p>', str(part_two[1]))
            if address_parts is not None:
                address_parts = address_parts.group(1).replace('&amp;', '&')
                address = '\n'.join(address_parts.split('<br/>'))
        
        right_sections = add_info.find_all('li')

        s1 = None
        s2 = None

        s1_title = None
        s1_desc = None
        s2_title = None
        s2_desc = None

        if len(right_sections) >= 1:
            s1 = right_sections[0]
            s1_title = re.search(r'<h3 class="identification-title">(.*)<\/h3>(.*)<\/li>', str(s1)).group(1).replace('&amp;', '&')
            s1_desc = re.search(r'<h3 class="identification-title">(.*)<\/h3>(.*)<\/li>', str(s1)).group(2).replace('&amp;', '&')
        if len(right_sections) >= 2:
            s2 = right_sections[1]
            s2_title = re.search(r'<h3 class="identification-title">(.*)<\/h3>(.*)<\/li>', str(s2)).group(1).replace('&amp;', '&')
            s2_desc = re.search(r'<h3 class="identification-title">(.*)<\/h3>(.*)<\/li>', str(s2)).group(2).replace('&amp;', '&')

        field1 = ''

        if person_title is not None:
            if field1 == '':
                field1 = person_title
            else:
                field1 = f'{field1}\n{person_title}'
        if email is not None:
            if field1 == '':
                field1 = email
            else:
                field1 = f'{field1}\n{email}'
        if phone is not None:
            if field1 == '':
                field1 = phone
            else: field1 = f'{field1}\n{phone}'
        if address is not None:
            if field1 == '':
                field1 = address
            else:
                field1 = f'{field1}\n\n{address}'

        color = 0x500000

        embed = discord.Embed(title=name, color=color)

        if field1 != '':
            embed.add_field(name='Contact', value=field1, inline=True)

        info_desc = ''

        if s1_title is not None and s1_desc is not None:
            info_desc = f'__{s1_title}__\n{s1_desc}'
        
        if s2_title is not None and s2_desc is not None:
            if info_desc != '':
                info_desc = f'{info_desc}\n\n__{s2_title}__\n{s2_desc}'
            else:
                info_desc = f'__{s2_title}__\n{s2_desc}'
        
        if info_desc != '':
            embed.add_field(name='Information', value=info_desc, inline=True)
        
        await ctx.send(embed=embed)
    return

# Shows embed w/ school resources using quick-access hyperlinks
@bot.command()
async def resources(ctx):
    title = 'School Resources Panel'
    color = 0x500000

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name=':page_facing_up: Texas A&M Website', value='The official TAMU homepage consolidates most school resources and information. [Go](https://www.tamu.edu).', inline=True)
    embed.add_field(name=':wave: Howdy Web Portal', value='A comprehensive web portal connecting students, faculty, staff, etc. with online TAMU services. [Go](https://howdy.tamu.edu).', inline=True)
    embed.add_field(name=':books: TAMU Library', value='An online library system for Texas A&M aggregating books journals, and research databases. [Go](https://library.tamu.edu).', inline=True)
    embed.add_field(name=':computer: IT Help Desk Central', value='Provides reliable and timely IT service assistance/solutions on behalf of the Department of IT. [Go](https://it.tamu.edu/help).', inline=True)
    embed.add_field(name=':envelope: Gmail', value='Access your TAMU email account through Gmail along with other Google Workspace applications. [Go](https://mail.google.com).', inline=True)
    embed.add_field(name=':pill: Student Health Services', value='Helpful information and links for accessing a variety of TAMU medical services. [Go](https://shs.tamu.edu/services).', inline=True)

    await ctx.send(embed=embed)
    return

# Add a class registry for a particular section to course DB
@bot.command()
async def add_course(ctx, subject_code, course_num, section_num):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t add a course if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (not is_ver):
        await ctx.send('You can\'t add a course if you are not verified.')
        return

    search_url = f'https://catalog.tamu.edu/search/?search={subject_code.upper()}+{course_num}'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    course_html = soup.find(class_='searchresult search-courseresult')
    course_hrs = course_html.find(class_='hours noindent').text.strip()

    hours_parts = [x.strip() for x in course_hrs.split('\n') if x != '']
    course_cred = " ".join(hours_parts[0].split(" ")[1:]).split(".")[0]
    course_hours = int(course_cred[0])
    
    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute(f'INSERT INTO {COURSE_TBL_NAME} (discord_user_id, course_hours, subject_code, course_num, section_num) '
                    f'VALUES ({discord_user_id}, {course_hours}, \'{subject_code.upper()}\', {course_num}, {section_num})')

        db.commit()
    except Exception as e:
        await ctx.send(f'Something went wrong while adding course to database. {e}')
        return

    await ctx.send(f'Successfully added your {subject_code} {course_num} class for section {section_num} to your schedule.')
    return

bot.run(TOKEN)
