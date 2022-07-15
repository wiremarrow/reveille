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
p = open('places.json')

config = json.load(c)
secret = json.load(s)
subjects = json.load(ss)
places = json.load(p)

c.close()
s.close()
ss.close()
p.close()

PREFIX = config['BOT_COMMAND_PREFIX']
TOKEN = secret['BOT_TOKEN']
EMAIL = config['BOT_EMAIL']
EMAIL_PASS = secret['BOT_EMAIL_PASS']
SQL_USER = config['SQL_USER']
SQL_PASS = secret['SQL_PASS']
DB_NAME = config['SQL_DB_NAME']
USER_TBL_NAME = config['SQL_USER_TBL_NAME']
COURSE_TBL_NAME = config['SQL_COURSE_TBL_NAME']

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
    discord_guild_id = member.guild.id

    DISCORD_SVRS = config['DISCORD_SVRS']

    if discord_guild_id == DISCORD_SVRS['TAMU_2026']['SVR_ID']:
        WELC_CHNL_ID = DISCORD_SVRS['TAMU_2026']['WELC_CHNL_ID']
        welc_channel = bot.get_channel(WELC_CHNL_ID)

        await welc_channel.send(f'Howdy, {member.mention}! Welcome to the **TAMU Class of 2026+** Discord server. To access the rest of the server, please introduce yourself with your name/nickname, major/school, and year.')
        return
    elif discord_guild_id == DISCORD_SVRS['THE_COMMONS']['SVR_ID']:
        WELC_CHNL_ID = DISCORD_SVRS['THE_COMMONS']['WELC_CHNL_ID']
        ROLE_CHNL_ID = DISCORD_SVRS['THE_COMMONS']['ROLE_CHNL_ID']
        welc_channel = bot.get_channel(WELC_CHNL_ID)
        role_channel = bot.get_channel(ROLE_CHNL_ID)

        await welc_channel.send(f'Howdy, {member.mention}! Head over to {role_channel.mention} to join a residence hall.')
        return

# Sends embed w/ list of commands (command syntax, arguments, + description)
@bot.command()
async def help(ctx):
    title = '__Command Help Menu__'
    description = (f'`{PREFIX}help` - Produces a help menu for command descriptions and syntax.\n'
                   f'`{PREFIX}register [net_id]` - Register your NetID with the bot to verify yourself.\n'
                   f'`{PREFIX}verify [verif_code]` - Verifies user if correct verification code is passed.\n'
                   f'`{PREFIX}is_verified [@user]` - Checks if a user has verified their NetID.\n'
                   f'`{PREFIX}course [subject_code] [course_num]` - Returns info about a specified course.\n'
                   f'`{PREFIX}calendar (event_num)` - Lists chosen number of school events from now.\n'
                   f'`{PREFIX}search [search_num] [*terms]` - Shows chosen number of results for search terms.\n'
                   f'`{PREFIX}resources` - Displays school resources with descriptions and hyperlinks.\n'
                   f'`{PREFIX}add_class [subject_code] [course_num] [section_num]` - Adds a class to schedule.\n'
                   f'`{PREFIX}remove_class [subject_code] [course_num] [section_num]` - Removes a class from schedule.\n'
                   f'`{PREFIX}schedule` - Enumerates classes in schedule with credit information.\n'
                   f'`{PREFIX}students [subject_code] [course_num]` - Finds the students taking a specified course.\n'
                   f'`{PREFIX}nom (open/all)` - Generates on-campus dining locations filtered by mode.\n'
                   f'`{PREFIX}menu (breakfast/lunch/dinner) (simple/detailed)` - Lists the dining menus for a specified dining location.')
    footer = (f'[ ] = Required argument; '
              f'( ) = Optional argument; '
              f'* = Arbitrary number of arguments; '
              f'val1/val2 = Options for valid arguments.')
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=footer)
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
    if course_html is None:
        await ctx.send('The course you inputted wasn\'t recognized.')
        return

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
async def calendar(ctx, event_num=3):
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

        title = f'__{event.name}__'
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
    embed.add_field(name=':books: TAMU Library', value='An online library system for Texas A&M aggregating books, journals, and research databases. [Go](https://library.tamu.edu).', inline=True)
    embed.add_field(name=':computer: IT Help Desk Central', value='Provides reliable and timely IT service assistance/solutions on behalf of the Department of IT. [Go](https://it.tamu.edu/help).', inline=True)
    embed.add_field(name=':envelope: Gmail', value='Access your TAMU email account through Gmail along with other Google Workspace applications. [Go](https://mail.google.com).', inline=True)
    embed.add_field(name=':pill: Student Health Services', value='Helpful information and links for accessing a variety of TAMU medical services. [Go](https://shs.tamu.edu/services).', inline=True)
    embed.add_field(name=':map: Interactive Campus Map', value='A dynamic and layered digital map of the TAMU campus with search functionality. [Go](https://www.tamu.edu/map).', inline=True)
    embed.add_field(name=':card_box: Canvas', value='Texas A&M\'s official learning management system which integrates most course administration. [Go](https://canvas.tamu.edu).', inline=True)
    embed.add_field(name=':printer: Aggie Print', value='Unified on-the-go online printing to Open Access Labs print kiosks. [Go](https://aggieprint.tamu.edu/myprintcenter).', inline=True)

    await ctx.send(embed=embed)
    return

# Add a class for a particular section to course DB
@bot.command()
async def add_class(ctx, subject_code, course_num, section_num):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t add a class if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (not is_ver):
        await ctx.send('You can\'t add a class if you are not verified.')
        return

    search_url = f'https://catalog.tamu.edu/search/?search={subject_code.upper()}+{course_num}'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    course_html = soup.find(class_='searchresult search-courseresult')
    if course_html is None:
        await ctx.send('The course you inputted wasn\'t recognized.')
        return

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
        await ctx.send(f'Something went wrong while adding class to database. {e}')
        return

    await ctx.send(f'Successfully added your {subject_code.upper()} {course_num} class for section {section_num} to your schedule.')
    return

# Remove a class for a particular section from course DB
@bot.command()
async def remove_class(ctx, subject_code, course_num, section_num):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t remove a class if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (not is_ver):
        await ctx.send('You can\'t remove a class if you are not verified.')
        return

    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute(f'DELETE FROM {COURSE_TBL_NAME} '
                    f'WHERE discord_user_id = {discord_user_id} '
                    f'AND subject_code = \'{subject_code.upper()}\' '
                    f'AND course_num = {course_num} '
                    f'AND section_num = {section_num}')

        db.commit()
    except Exception as e:
        await ctx.send(f'Something went wrong while removing class from database. {e}')
        return

    await ctx.send(f'Successfully removed your {subject_code.upper()} {course_num} class for section {section_num} from your schedule.')
    return

# Show user schedule from course DB
@bot.command()
async def schedule(ctx):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t manage a schedule if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (not is_ver):
        await ctx.send('You can\'t manage a schedule if you are not verified.')
        return

    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute(f'SELECT * FROM {COURSE_TBL_NAME} '
                    f'WHERE discord_user_id = {discord_user_id}')

        courses = cur.fetchall()

        title = f'__{ctx.message.author.display_name}\'s Schedule__'
        description = ''
        color = 0x500000

        total_hours = 0

        for i in range(len(courses)):
            description = f'{description}\n`{i+1}` **{courses[i][2]} {courses[i][3]}**-{courses[i][4]} ({courses[i][1]})'
            total_hours = total_hours + courses[i][1]
        
        description = description.strip()

        if description == '':
            await ctx.send('You don\'t have any classes in your schedule.')
            return

        description = f'{description}\n\n**Total Credits:** {total_hours}'

        embed = discord.Embed(title=title, description=description, color=color)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f'Something went wrong while retrieving classes from database. {e}')
        return

# Iterates through users that have specified course in their schedule
@bot.command()
async def students(ctx, subject_code, course_num):
    discord_user_id = ctx.message.author.id

    # Criteria restriction filter
    is_reg = await is_registered(ctx, discord_user_id)
    if (is_reg == 404):
        return
    elif (not is_reg):
        await ctx.send('You can\'t query a student class search if you are not registered.')
        return

    is_ver = await is_verified(ctx, discord_user_id)
    if (is_ver == 404):
        return
    elif (not is_ver):
        await ctx.send('You can\'t query a student class search if you are not verified.')
        return

    search_url = f'https://catalog.tamu.edu/search/?search={subject_code.upper()}+{course_num}'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    course_html = soup.find(class_='searchresult search-courseresult')
    if course_html is None:
        await ctx.send('The course you inputted wasn\'t recognized.')
        return

    course_name = course_html.find('h2').text

    try:
        db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
        cur = db.cursor()
        cur.execute(f'SELECT DISTINCT discord_user_id FROM {COURSE_TBL_NAME} '
                    f'WHERE subject_code = \'{subject_code.upper()}\' '
                    f'AND course_num = {course_num}')

        students = cur.fetchall()

        title = f'__Students in {subject_code.upper()} {course_num}__'
        description = ''
        color = 0x500000

        for i in range(len(students)):
            user_id = students[i][0]
            user = bot.get_user(user_id)
            description = f'{description}\n`{i+1}` {user.display_name} ({user.name}#{user.discriminator})'

        description = description.strip()

        if description == '':
            await ctx.send('No other verified students appear in the specified course.')
            return

        description = f'**{course_name}**\n{description}'

        embed = discord.Embed(title=title, description=description, color=color)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f'Something went wrong while accessing student classes from database. {e}')
        return

# Lists all food options on campus w/ operating times and open status
@bot.command()
async def nom(ctx, mode='open'):
    now = arrow.utcnow().to('US/Central')
    fnow = now.format('YYYY-MM-DD HH:mm:ss.SSS')
    fnow = f'{fnow[:10]}T{fnow[10:]}Z'

    search_url = f'https://api.dineoncampus.com/v1/locations/weekly_schedule?site_id=5751fd4290975b60e0489534&date={fnow}'
    json_str = requests.get(search_url).content

    weekly_schedule = json.loads(json_str)
    locations = weekly_schedule['the_locations']

    day_num = int(now.format('d')) - 1

    vendors = []

    for location in locations:
        name = location['name']

        day_info = [x for x in location['week'] if x['day'] == day_num][0]
        day_closed = day_info['closed']

        if not day_closed:
            hours = day_info['hours']

            times = ''
            is_open = False

            for hour in hours:
                start_hour = hour['start_hour']
                start_minutes = hour['start_minutes']
                end_hour = hour['end_hour']
                end_minutes = hour['end_minutes']

                start = arrow.get(now.year, now.month, now.day, start_hour, start_minutes, tzinfo='US/Central')
                end = arrow.get(now.year, now.month, now.day, end_hour, end_minutes, tzinfo='US/Central')

                if start < now and now < end:
                    is_open = True

                times_str = f'{start.format("h:mm a")} - {end.format("h:mm a")}'
                times = f'{times}, {times_str}'

            times = times[2:]

            if is_open:
                vendors.append(f'+ {name} ({times}) [OPEN]')
            else:
                if mode == 'all':
                    vendors.append(f'- {name} ({times}) [CLOSED]')

        else:
            if mode == 'all':
                vendors.append(f'- {name} [DAY CLOSED]')

    if mode == 'open':
        if not vendors:
            await ctx.send('Nothing is open!')
            await ctx.send(':sob:')
            return

        description = '\n'.join(vendors)

        await ctx.send(f'__**Open Campus Dining Options**__ ({now.format("M/D @ h:mm a")})\n```diff\n{description}\n```')
        return
    elif mode == 'all':
        curated_vendors = vendors[1:52]
        description1 = '\n'.join(curated_vendors[:len(curated_vendors)//2]).strip()
        description2 = '\n'.join(curated_vendors[len(curated_vendors)//2:]).strip()

        await ctx.send(f'__**All Campus Dining Options**__ ({now.format("M/D @ h:mm a")})\n```diff\n{description1}\n```')
        await ctx.send(f'```diff\n{description2}\n```')
        return
    else:
        await ctx.send('Invalid command argument.')
        return

# Returns the menu of a dining place with menu item information
@bot.command()
async def menu(ctx, place, kind='BREAKFAST', mode='SIMPLE'):
    now = arrow.utcnow().to('US/Central')
    fnow = now.format('YYYY-M-D')

    id = places[str(place)][0]
    place_name = places[str(place)][1]

    search_url1 = f'https://api.dineoncampus.com/v1/location/{id}/periods?platform=0&date={fnow}'
    json_str1 = requests.get(search_url1).content

    period_json = json.loads(json_str1)
    periods_info = period_json['periods']

    period = None

    if kind.upper() == 'BREAKFAST' or kind.upper() == 'GENERAL':
        period = periods_info[0]['id']
        await ctx.send(f'__**{place_name} Breakfast Menus**__ ({now.format("M/D @ h:mm a")})')
    elif kind.upper() == 'LUNCH':
        period = periods_info[1]['id']
        await ctx.send(f'__**{place_name} Lunch Menus**__ ({now.format("M/D @ h:mm a")})')
    elif kind.upper() == 'DINNER':
        period = periods_info[2]['id']
        await ctx.send(f'__**{place_name} Dinner Menus**__ ({now.format("M/D @ h:mm a")})')
    else:
        await ctx.send(f'Invalid command argument.')
        return

    search_url2 = f'https://api.dineoncampus.com/v1/location/{id}/periods/{period}?platform=0&date={fnow}'
    json_str2 = requests.get(search_url2).content

    menu_json = json.loads(json_str2)
    menu = menu_json['menu']
    periods = menu['periods']
    categories = periods['categories']

    for category in categories:
        desc_strs = []

        name = category['name']
        items = category['items']

        for i in range(len(items)):
            item_str = ''

            item_name = items[i]['name']
            desc = items[i]['desc']
            portion = items[i]['portion']
            ingredients = None

            try:
                ingredients = items[i]['ingredients'].replace('*Menu More', '')
            except:
                pass

            nutrients = items[i]['nutrients']
            calories = str(nutrients[0]['value']).replace('less than 1 gram', '<1')
            proteins_uom = None

            try:
                proteins_uom = nutrients[1]['uom']
            except:
                pass
            if proteins_uom is None:
                proteins_uom = 'cal'

            proteins = str(nutrients[1]['value']).replace('less than 1 gram', '<1')
            carbs_uom = None

            try:
                carbs_uom = nutrients[2]['uom']
            except:
                pass
            if carbs_uom is None:
                carbs_uom = 'cal'

            carbs = str(nutrients[2]['value']).replace('less than 1 gram', '<1')
            fats_uom = None

            try:
                fats_uom = nutrients[4]['uom']
            except:
                pass
            if fats_uom is None:
                fats_uom = 'cal'

            fats = str(nutrients[4]['value']).replace('less than 1 gram', '<1')

            desc_part = f'__Description:__ {desc}\n' if desc is not None else ''
            ingredients_part = f'__Ingredients__ {ingredients}\n' if ingredients is not None else ''

            if mode.upper() == 'SIMPLE':
                item_str = f'`{i+1}` **{item_name}** ({portion}) [{calories} cal]'
            elif mode.upper() == 'DETAILED':
                item_str = f'`{i+1}` **{item_name}** ({portion}) [{calories} cal]\n{desc_part}{ingredients_part}'
            else:
                await ctx.send('Invalid command argument.')
                return

            desc_strs.append(item_str)

        total_len = 0
        last_index_stop = 0

        for i in range(len(desc_strs)):
            desc_str = desc_strs[i]
            if total_len + len(desc_str) >= 3800:
                title = f'__{name} Menu__'
                description = '\n'.join(desc_strs[last_index_stop:i]).strip()
                color = 0x500000

                embed = discord.Embed(title=title, description=description, color=color)
                await ctx.send(embed=embed)

                total_len = 0
                last_index_stop = i
            elif i == len(desc_strs) - 1:
                title = f'__{name} Menu__'
                description = '\n'.join(desc_strs[last_index_stop:i]).strip()
                color = 0x500000

                embed = discord.Embed(title=title, description=description, color=color)
                await ctx.send(embed=embed)
            total_len += len(desc_str)
    return

# Gives a list of dining places w/ id nums categorized by a mode
@bot.command()
async def dining(ctx, mode='HALL'):
    search_url = 'https://api.dineoncampus.com/v1/locations/all_locations?platform=0&site_id=5751fd4290975b60e0489534&for_menus=true&with_address=false&with_buildings=true'
    json_str = requests.get(search_url).content

    location_json = json.loads(json_str)
    buildings = location_json['buildings']

    index = 1

    for building in buildings:
        building_str = ''

        name = building['name']
        locations = building['locations']

        for location in locations:
            if mode.upper() == 'HALL' and name != 'Dining Halls (All-You-Care-To-Eat)':
                index = index + 1
                continue
            elif mode.upper() == 'NORTH' and name != 'North Campus':
                index = index + 1
                continue
            elif mode.upper() == 'SOUTH' and name != 'South Campus':
                index = index + 1
                continue
            elif mode.upper() == 'CENTRAL' and name != 'Central Campus':
                index = index + 1
                continue
            elif mode.upper() == 'WEST' and name != 'West Campus':
                index = index + 1
                continue
            elif mode.upper() == 'EAST' and name != 'East Campus':
                index = index + 1
                continue
            elif mode.upper() == 'ALL':
                pass
            else:
                if mode.upper() != 'HALL' and mode.upper() != 'NORTH' and mode.upper() != 'SOUTH' and mode.upper() != 'CENTRAL' and mode.upper() != 'WEST' and mode.upper() != 'EAST':
                    await ctx.send('Invalid command argument.')
                    return

            loc_name = location['name']
            # id = location['id']
            # building_id = location['building_id']
            # active = location['active']
            # desc = location['short_description']
            # pay_with_apple_pay = location['pay_with_apple_pay']
            # pay_with_cash = location['pay_with_cash']
            # pay_with_cc = location['pay_with_cc']
            # pay_with_dining_dollars = location['pay_with_dining_dollars']
            # pay_with_google_pay = location['pay_with_google_pay']
            # pay_with_meal_exchange = location['pay_with_meal_exchange']
            # pay_with_meal_swipe = location['pay_with_meal_swipe']
            # pay_with_meal_trade = location['pay_with_meal_trade']
            # pay_with_retail_swipe = location['pay_with_retail_swipe']
            # pay_with_samsung_pay = location['pay_with_samsung_pay']
            # pay_with_meal_plan = location['pay_with_meal_plan']

            building_str = f'{building_str}\n`{index}` {loc_name}'

            index = index + 1

        building_str = building_str.strip()

        if building_str != '':
            title = f'__{name}__'
            description = building_str
            color = 0x500000

            embed = discord.Embed(title=title, description=description, color=color)
            await ctx.send(embed=embed)
    return

bot.run(TOKEN)
