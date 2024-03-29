from tkinter import W
import discord
from discord.ext import commands
import os
import re
import json
import arrow
import random
import smtplib
import requests
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt
from ics import Calendar
from bs4 import BeautifulSoup
from shapely.geometry import Point, LineString

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
async def help(ctx, cmd=''):
    title = f'__{cmd.upper()} Command Help__'
    description = (f'**Utility**\n'
                   f':raised_hand: `{PREFIX}help` - Produces a help menu for command descriptions and syntax.\n'
                   f':email: `{PREFIX}register [net_id]` - Register your NetID with the bot to verify yourself.\n'
                   f':white_check_mark: `{PREFIX}verify [verif_code]` - Verifies you if correct verification code is passed.\n'
                   f':eye: `{PREFIX}is_verified [@user]` - Checks if a user has verified their NetID with the bot.\n\n'
                   f'**School**\n'
                   f':books: `{PREFIX}resources` - Displays school resources with descriptions and hyperlinks.\n'
                   f':calendar: `{PREFIX}calendar (event_num)` - Lists next `event_num` academic events from now.\n'
                   f':newspaper: `{PREFIX}events (\'today\'/\'tomorrow\')` - Lists student events for a specified day.\n'
                   f':mag: `{PREFIX}search [search_num] [*terms]` - Shows `search_num` results from the TAMU directory for an arbitrary amount of search terms.\n\n'
                   f'**Courses & Schedule**\n'
                   f':notebook_with_decorative_cover: `{PREFIX}course [subject_code] [course_num]` - Returns credit information, a description, and important attributes about a specified course.\n'
                   f':trophy: `{PREFIX}rank [subject_code] [course_num] (year_min)` - Lists professors along with their basic info for a specified course in descending order of mean GPA.\n'
                   f':teacher: `{PREFIX}prof [first] [last] [subject_code] [course_num] (year_min)` - Provides detailed data on a specified professor\'s grading history for a course.\n'
                   f':page_facing_up: `{PREFIX}schedule` - Enumerates the classes in your schedule with credit information.\n'
                   f':green_book: `{PREFIX}add_class [subject_code] [course_num] [section_num]` - Adds a specified class to your schedule.\n'
                   f':closed_book: `{PREFIX}remove_class [subject_code] [course_num] [section_num]` - Removes a specified class from your schedule.\n'
                   f':student: `{PREFIX}students [subject_code] [course_num]` - Finds all verified students with a specified course in their schedule.\n\n'
                   f'**Campus Dining**\n'
                   f':receipt: `{PREFIX}nom (\'open\'/\'all\')` - Generates a list of on-campus dining places filtered by mode with hours-of-operation and open status.\n'
                   f':office: `{PREFIX}dining (\'hall\'/\'north\'/\'south\'/\'central\'/\'west\'/\'east\'/\'all\')` - Enumerates the `place_id`s for dining locations in a specified area to be used with the `{PREFIX}menu` command.\n'
                   f':hamburger: `{PREFIX}menu [place_id] ((\'general\'/\'breakfast\')/\'lunch\'/\'dinner\') (\'simple\'/\'detailed\')` - Lists the dining menus for a specified dining location (using a `place_id`) for a particular specified menu type and presentation.\n\n'
                   f'**Transportation**\n'
                   f':blue_car: `{PREFIX}garage` - Displays the real-time available spaces for all parking garages.\n'
                   f':bus: `{PREFIX}bus (\'all\'/\'on_campus\'/\'off_campus\'/\'game_day\')` - Lists the `route_code`s for bus routes in a specified route group to be used with the `{PREFIX}route` command.\n'
                   f':tram: `{PREFIX}route [route_code] (\'scaled\'/\'real\')` - Returns information for a specified route (using a `route_code`) with accompanying estimated stop times, route visualization, and real-time bus tracking.\n\n'
                   f'**Extra & Fun**\n'
                   f':partly_sunny: `{PREFIX}weather (\'hourly\'/\'bidaily\') (step_num)` - Reports weather info given a specified forecast mode at `step_num` steps of forecast mode iteration.\n'
                   f':thumbsup: `{PREFIX}gigem` - Responds with a "Gig \'em" message.')
    footer = ('[ ] = Required argument; '
              '( ) = Optional argument; '
              '* = Arbitrary number of arguments; '
              'val1/val2 = Options for valid arguments; '
              '\'val\' = Literal argument.')
    color = 0x500000

    if cmd == '':
        title = '__Command Help Menu__'
    elif cmd.upper() == 'HELP':
        description = (f'**Format:**\n`{PREFIX}help`\n\nNo arguments.\n\n'
                       f'**Description:**\nThis command will produce a help menu for command descriptions and syntax. It\'s pretty concise and useful for a quick reference when trying to format a correct command call. There\'s really nothing much else to it.')
    elif cmd.upper() == 'REGISTER':
        description = (f'**Format:**\n`{PREFIX}register [net_id]`\n\n`net_id` is a required argument: The NetID of the user.\n\n'
                       f'**Examples:**\n`{PREFIX}register doe.jane`\n`{PREFIX}register alexbrown`\n\n'
                       f'**Description:**\nThis command will initiate a registration process with Reveille Bot by sending an automated email to `net_id`@tamu.edu with a user-specific verification code. To be clear, `net_id` is literally your TAMU NetID that you use for school services. You can use the emailed verification code along with the `{PREFIX}verify` command as an argument in order to verify your identity with Reveille Bot to gain access to schedule and class management commands. Use `{PREFIX}help verify` to get more information about the `{PREFIX}verify` command.')
    elif cmd.upper() == 'VERIFY':
        description = (f'**Format:**\n`{PREFIX}verify [verif_code]`\n\n`verif_code` is a required argument: The emailed verification code sent to the user\'s TAMU school email (from the `{PREFIX}register` command).\n\n'
                       f'**Examples:**\n`{PREFIX}verify 498382`\n`{PREFIX}verify 810255`\n\n'
                       f'**Description:**\nThis command will initiate a verification process with Reveille Bot and check whether `verif_code` matches the actual verification code sent to `net_id`@tamu.edu (sent as a result of using the `{PREFIX}register` command). If `verif_code` successfully matches, your Discord user is marked as verified. Once you\'re verified you gain access to schedule and class management commands. Use `{PREFIX}help register` to get more information about the `{PREFIX}register` command.')
    elif cmd.upper() == 'IS_VERIFIED':
        description = (f'**Format:**\n`{PREFIX}is_verified [@user]`\n\n`@user` is a required argument: A mention of a user in the Discord server.\n\n'
                       f'**Examples:**\n`{PREFIX}is_verified @ProudAggieMother79`\n`{PREFIX}is_verified @xXxTacticalGhostxXx`\n\n'
                       f'**Description:**\nThis command will check whether the specified user is verified or not and return the answer in the form of a message.')
    elif cmd.upper() == 'RESOURCES':
        description = (f'**Format:**\n`{PREFIX}resources`\n\nNo arguments.\n\n'
                       f'**Examples:**\n`{PREFIX}resources`\n\n'
                       f'**Description:**\nThis command will display descriptions and hyperlinks of and to TAMU school resources such as: the Texas A&M website, Howdy web portal, the TAMU library website, TAMU IT Help Desk, Gmail, the Student Health Services website, the interactive campus map, Canvas, and the Aggie Print webpage.')
    elif cmd.upper() == 'CALENDAR':
        description = (f'**Format:**\n`{PREFIX}calendar (event_num)`\n\n`event_num` is an optional argument: The number of events to be retrieved. The default value for `event_num` is set to 3.\n\n'
                       f'**Examples:**\n`{PREFIX}calendar`\n`{PREFIX}calendar 6`\n\n'
                       f'**Description:**\nThis command will list the next `event_num` academic events from the TAMU Academic Calendar from now.')
    elif cmd.upper() == 'EVENTS':
        description = (f'**Format:**\n`{PREFIX}events (\'today\'/\'tomorrow\')`\n\n`mode` is an optional argument: The target day to list school events from. The default value for `mode` is set to `today`.\n\n'
                       f'**Examples:**\n`{PREFIX}events`\n`{PREFIX}events tomorrow`\n\n'
                       f'**Description:**\nThis command will list the student events for a specified day.')
    elif cmd.upper() == 'SEARCH':
        description = (f'**Format:**\n`{PREFIX}search [search_num] [*terms]`\n\n`search_num` is a required argument: The maximum amount of search results to display.\n`*terms` is a required argument: The specified search terms to query the TAMU directory with.\n\n'
                       f'**Examples:**\n`{PREFIX}search 3 john doe`\n`{PREFIX}search 10 thomas`\n\n'
                       f'**Description:**\nThis command will show `search_num` results from the TAMU directory for an arbitrary amount of search terms.')
    elif cmd.upper() == 'COURSE':
        description = (f'**Format:**\n`{PREFIX}course [subject_code] [course_num]`\n\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n\n'
                       f'**Examples:**\n`{PREFIX}course MATH 151`\n{PREFIX}course CHEM 107\n\n'
                       f'**Description:**\nThis command will return the credit information, a description, and important attributes of a specified course.')
    elif cmd.upper() == 'RANK':
        description = (f'**Format:**\n`{PREFIX}rank [subject_code] [course_num] (year_min)`\n\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n`year_min` is an optional argument: The minimum year a professor must have taught to be considered in the ranking pool. The default value set for `year_min` is set to 2021.\n\n'
                       f'**Examples:**\n`{PREFIX}rank MATH 151`\n{PREFIX}rank CHEM 107 2016\n\n'
                       f'**Description:**\nThis command will list professors along with their basic information for a specified course in descending order of mean GPA.')
    elif cmd.upper() == 'PROF':
        description = (f'**Format:**\n`{PREFIX}prof [first] [last] [subject_code] [course_num] (year_min)`\n\n`first` is a required argument: The first name of the specified professor.\n`last` is a required argument: The last name of the specified professor.\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n`year_min` is an optional argument: The minimum year recorded data for a specified professor is considered for assessment. The default value set for `year_min` is set to 0.\n\n'
                       f'**Examples:**\n`{PREFIX}prof ALLEN AUSTIN MATH 151`\n{PREFIX}prof JANE DOE CHEM 107 2016\n\n'
                       f'**Description:**\nThis command will provide detailed data on a specified professor\'s grading history for a desired course.')
    elif cmd.upper() == 'SCHEDULE':
        description = (f'**Format:**\n`{PREFIX}schedule`\n\nNo arguments.\n\n'
                       f'**Examples:**\n`{PREFIX}schedule\n\n'
                       f'**Description:**\nThis command will enumerate the classes in your schedule with credit information.')
    elif cmd.upper() == 'ADD_CLASS':
        description = (f'**Format:**\n`{PREFIX}add_class [subject_code] [course_num] [section_num]`\n\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n `section_num` is a required argument: The section number of a specified course designating a particular class.\n\n'
                       f'**Examples:**\n`{PREFIX}add_class MATH 151 506`\n{PREFIX}add_class CHEM 107 201\n\n'
                       f'**Description:**\nThis command will add a specified class to your schedule.')
    elif cmd.upper() == 'REMOVE_CLASS':
        description = (f'**Format:**\n`{PREFIX}remove_class [subject_code] [course_num] [section_num]`\n\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n `section_num` is a required argument: The section number of a specified course designating a particular class.\n\n'
                       f'**Examples:**\n`{PREFIX}remove_class MATH 151 506`\n{PREFIX}remove_class CHEM 107 201\n\n'
                       f'**Description:**\nThis command will remove a specified class from your schedule.')
    elif cmd.upper() == 'STUDENTS':
        description = (f'**Format:**\n`{PREFIX}students [subject_code] [course_num]`\n\n`subject_code` is a required argument: The TAMU department subject code for a specified course.\n`course_num` is a required argument: The TAMU course number for a specified course.\n\n'
                       f'**Examples:**\n`{PREFIX}students MATH 151`\n{PREFIX}students CHEM 107\n\n'
                       f'**Description:**\nThis command will find all verified students with a specified course in their schedule.')
    elif cmd.upper() == 'NOM':
        description = (f'**Format:**\n`{PREFIX}nom (\'open\'/\'all\')`\n\n`mode` is an optional argument: The display mode for the kinds of dining places that are shown.\n\n'
                       f'**Examples:**\n`{PREFIX}nom`\n{PREFIX}nom all\n\n'
                       f'**Description:**\nThis command will generate a list of on-campus dining places filtered by mode with hours-of-operation and open status.\n')
    elif cmd.upper() == 'DINING':
        description = (f'**Format:**\n`{PREFIX}dining (\'hall\'/\'north\'/\'south\'/\'central\'/\'west\'/\'east\'/\'all\')`\n\n`mode` is an optional argument: The display mode for the kinds of dining places that are shown.\n\n'
                       f'**Examples:**\n`{PREFIX}dining`\n{PREFIX}dining central\n\n'
                       f'**Description:**\nThis command will enumerate the `place_id`s for dining locations in a specified area to be used with the `{PREFIX}menu` command.\n')
    elif cmd.upper() == 'MENU':
        description = (f'**Format:**\n`{PREFIX}menu [place_id] ((\'general\'/\'breakfast\')/\'lunch\'/\'dinner\') (\'simple\'/\'detailed\')\n\n`place_id` is a required argument: The identification number of a particular dining location to return menus for.\n`menu_type` is an optional argument: The type of menu returned for a specified dining location. The default value set for `menu_type` is set to \'GENERAL\'.\n`display_mode` \n\n'
                       f'**Examples:**\n`{PREFIX}menu 1 breakfast`\n{PREFIX}menu 16 general\n\n'
                       f'**Description:**\nThis command will list the dining menus for a specified dining location (using a `place_id`) for a particular specified menu type and presentation.\n')
    elif cmd.upper() == 'GARAGE':
        description = (f'**Format:**\n`{PREFIX}garage\n\nNo arguments.\n\n'
                       f'**Examples:**\n`{PREFIX}garage`\n\n'
                       f'**Description:**\nThis command will display the real-time available spaces for all parking garages.\n')
    elif cmd.upper() == 'BUS':
        description = (f'**Format:**\n`{PREFIX}bus\n\nNo arguments.\n\n'
                       f'**Examples:**\n`{PREFIX}bus`\n\n'
                       f'**Description:**\nThis command will list the `route_code`s for bus routes in a specified route group to be used with the `{PREFIX}route` command.\n')
    else:
        description = 'WIP'

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
    embed.add_field(name=':email: Gmail', value='Access your TAMU email account through Gmail along with other Google Workspace applications. [Go](https://mail.google.com).', inline=True)
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

                times_str = f'{start.format("h:mma")} - {end.format("h:mma")}'
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
            await ctx.send('Nothing is open!\n:sob:')
            return

        description = '\n'.join(vendors)

        await ctx.send(f'__**Open Campus Dining Options**__ ({now.format("M/D @ h:mma")})\n```diff\n{description}\n```')
        return
    elif mode == 'all':
        curated_vendors = vendors[1:52]
        description1 = '\n'.join(curated_vendors[:len(curated_vendors)//2]).strip()
        description2 = '\n'.join(curated_vendors[len(curated_vendors)//2:]).strip()

        await ctx.send(f'__**All Campus Dining Options**__ ({now.format("M/D @ h:mma")})\n```diff\n{description1}\n```')
        await ctx.send(f'```diff\n{description2}\n```')
        return
    else:
        await ctx.send('Invalid command argument.')
        return

# Returns the menu of a dining place with menu item information
@bot.command()
async def menu(ctx, place, kind='GENERAL', mode='SIMPLE'):
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
        await ctx.send(f'__**{place_name} Breakfast Menus**__ ({now.format("M/D @ h:mma")})')
    elif kind.upper() == 'LUNCH':
        period = periods_info[1]['id']
        await ctx.send(f'__**{place_name} Lunch Menus**__ ({now.format("M/D @ h:mma")})')
    elif kind.upper() == 'DINNER':
        period = periods_info[2]['id']
        await ctx.send(f'__**{place_name} Dinner Menus**__ ({now.format("M/D @ h:mma")})')
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

            desc_part = f'__Description:__ {desc}\n' if desc is not None else ''
            ingredients_part = f'__Ingredients:__ {ingredients}\n' if ingredients is not None else ''

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

# Sends a Gig 'em message
@bot.command()
async def gigem(ctx):
    await ctx.send('Gig \'em, Aggies!')
    return

# Lists school events from TAMU events calendar
@bot.command()
async def events(ctx, days='TODAY'):
    now = arrow.utcnow().to('US/Central')

    if days.upper() == 'TODAY':
        await ctx.send(f'__**School Events for Today**__ ({now.format("M/D")})')
    elif days.upper() == 'TOMORROW':
        now = now.shift(days=1)
        await ctx.send(f'__**School Events for Tomorrow**__ ({now.format("M/D")})')
    else:
        await ctx.send('Invalid command argument.')
        return

    search_url = f'https://calendar.tamu.edu/live/calendar/view/day/audience/Students/date/{now.format("YYYYMMDD")}?user_tz=America%2FChicago&template_vars=id,href,image_src,title_link,date_title,time,latitude,longitude,location,summary&syntax=%3Cwidget%20type%3D%22events_calendar%22%3E%3Carg%20id%3D%22mini_cal_heat_map%22%3Efalse%3C%2Farg%3E%3Carg%20id%3D%22thumb_width%22%3E363%3C%2Farg%3E%3Carg%20id%3D%22thumb_height%22%3E220%3C%2Farg%3E%3Carg%20id%3D%22hide_repeats%22%3Efalse%3C%2Farg%3E%3Carg%20id%3D%22enable_home_view%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22search_all_events_only%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_groups%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_tags%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_locations%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22use_modular_templates%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22default_view%22%3Ehome%3C%2Farg%3E%3Carg%20id%3D%22group%22%3E%2A%20Main%20University%20Calendar%3C%2Farg%3E%3C%2Fwidget%3E'
    json_str = requests.get(search_url).content

    events_json = json.loads(json_str)
    events = events_json['events']

    for event in events:
        name = event['title']
        location = event['location']
        image_src = None

        try:
            image_src = event['image_src']
        except:
            pass

        summary = event['summary']
        href = event['href']
        event_url = f'https://calendar.tamu.edu/{href}'

        event_id = int(re.search(r'\d+', href.split('-')[0]).group())
        event_search_url = f'https://calendar.tamu.edu/live/calendar/view/event/event_id/{str(event_id)}?user_tz=America%2FChicago&template_vars=group,title,date_time,add_to_google,add_to_yahoo,ical_download_href,repeats,until,location,custom_room_number,summary,description,contact_info,related_content,cost,registration,tags_calendar,id,image,online_url,online_button_label,online_instructions,share_links&syntax=%3Cwidget%20type%3D%22events_calendar%22%3E%3Carg%20id%3D%22mini_cal_heat_map%22%3Efalse%3C%2Farg%3E%3Carg%20id%3D%22thumb_width%22%3E363%3C%2Farg%3E%3Carg%20id%3D%22thumb_height%22%3E220%3C%2Farg%3E%3Carg%20id%3D%22hide_repeats%22%3Efalse%3C%2Farg%3E%3Carg%20id%3D%22enable_home_view%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22search_all_events_only%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_groups%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_tags%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22show_locations%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22use_modular_templates%22%3Etrue%3C%2Farg%3E%3Carg%20id%3D%22default_view%22%3Ehome%3C%2Farg%3E%3Carg%20id%3D%22group%22%3E%2A%20Main%20University%20Calendar%3C%2Farg%3E%3C%2Fwidget%3E'
        event_json = requests.get(event_search_url).content

        event_detail = json.loads(event_json)
        date = event_detail['event']['date']

        title = name
        description = f'**Location:** {location}\n**Description:** {summary}'
        description = description.replace('<em>', '*').replace('</em>', '*').replace('&amp;', '&').replace('&quot;', '"').replace('<br />', '\n').replace('<p>', '').replace('</p>', '').strip()
        description = re.sub(r'\n\s*\n', '\n', description)
        color = 0x500000
        url = event_url
        footer = date.replace(' CDT', '')
        footer = re.sub(r'<span(.+)</span>', '-', footer)

        embed = discord.Embed(title=title, description=description, color=color, url=url)

        if image_src is not None:
            embed.set_image(url=image_src)

        embed.set_footer(text=footer)

        await ctx.send(embed=embed)
    return

# Reports weather conditions given a specified step mode.
@bot.command()
async def weather(ctx, mode='HOURLY', val=1):
    lat = round(30.618057377264176, 4)
    lon = round(-96.33628848619472, 4)

    search_url = f'https://api.weather.gov/points/{lat},{lon}'
    json_str1 = requests.get(search_url).content
    weather_json = json.loads(json_str1)

    properties1 = weather_json['properties']
    forecast_url = properties1['forecast']

    if mode.upper() == 'HOURLY':
        forecast_url += '/hourly'
    elif mode.upper() == 'BIDAILY':
        pass
    else:
        await ctx.send('Invalid command argument.')
        return

    json_str2 = requests.get(forecast_url).content
    forecast_json = json.loads(json_str2)

    try:
        properties2 = forecast_json['properties']
        periods = properties2['periods']
    except Exception as e:
        await ctx.send(f'Something went wrong while accessing weather API data. {e}')
        return

    for period in periods:
        number = period['number']
        name = period['name']
        start = arrow.get(period['startTime'])
        end = arrow.get(period['endTime'])
        temp = period['temperature']
        temp_unit = period['temperatureUnit']
        wind_speed = period['windSpeed']
        wind_dir = period['windDirection']
        icon_url = period['icon']
        short_forecast = period['shortForecast']
        detailed_forecast = period['detailedForecast']

        if mode.upper() == 'HOURLY' and number == int(val):
            title = '__Weather at TAMU Campus__'
            if int(val) == 1:
                description = f'{start.format("M/D h:mma")} - {end.format("M/D h:mma")}\n\n**Time Period:** Now\n**Temperature:** {temp} °{temp_unit}\n**Wind Speed:** {wind_speed} {wind_dir}\n**Forecast:** {short_forecast}'
            else:
                description = f'{start.format("M/D h:mma")} - {end.format("M/D h:mma")}\n\n**Time Period:** {start.format("dddd")}\n**Temperature:** {temp} °{temp_unit}\n**Wind Speed:** {wind_speed} {wind_dir}\n**Forecast:** {short_forecast}'
            color = 0x500000
            footer = 'Accuracy: Hourly'

            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_thumbnail(url=icon_url)
            embed.set_footer(text=footer)

            await ctx.send(embed=embed)
            return
        elif mode.upper() == 'BIDAILY' and number == int(val):
            title = '__Weather at TAMU Campus__'
            description = f'{start.format("M/D h:mma")} - {end.format("M/D h:mma")}\n\n**Time Period:** {name}\n**Temperature:** {temp} °{temp_unit}\n**Wind Speed:** {wind_speed} {wind_dir}\n**Forecast:** {detailed_forecast}'
            color = 0x500000
            footer = 'Accuracy: Bi-daily'

            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_thumbnail(url=icon_url)
            embed.set_footer(text=footer)

            await ctx.send(embed=embed)
            return
    return

# Generates a ranked list of professors for a specified course.
@bot.command()
async def rank(ctx, subject_code, course_num, year_min=2021):
    data = {'dept': subject_code.upper(), 'number': course_num.upper()}

    search_url = 'https://anex.us/grades/getData/'
    json_str = requests.post(search_url, data).content

    course_json = json.loads(json_str)
    classes = course_json['classes']

    d1 = {'Section': [], 'Professor': [], 'Year': [], 'Semester': [], 'GPA': [],
         'A': [], 'B': [], 'C': [], 'D': [], 'F': [], 'I': [], 'S': [], 'U': [], 'Q': [], 'X': []}
    classes_df = pd.DataFrame(d1)

    for class_ in classes:
        section = class_['section']
        a_freq = class_['A']
        b_freq = class_['B']
        c_freq = class_['C']
        d_freq = class_['D']
        f_freq = class_['F']
        i_freq = class_['I']
        s_freq = class_['S']
        u_freq = class_['U']
        q_freq = class_['Q']
        x_freq = class_['X']
        prof_name = class_['prof']
        year = class_['year']
        semester = class_['semester']
        gpa = float(class_['gpa'])

        d2 = {'Section': [section], 'Professor': [prof_name], 'Year': [year], 'Semester': [semester], 'GPA': [gpa],
                    'A': [a_freq], 'B': [b_freq], 'C': [c_freq], 'D': [d_freq], 'F': [f_freq], 'I': [i_freq], 'S': [s_freq],
                    'U': [u_freq], 'Q': [q_freq], 'X': [x_freq]}
        class_df = pd.DataFrame(d2)

        classes_df = pd.concat([classes_df, class_df], ignore_index=True)

    classes_df = classes_df.sort_values(by=['GPA'], ascending=False).loc[classes_df['Year'].astype('int') >= int(year_min)]

    unique_profs = []
    ordered_profs = []

    for index, row in classes_df.iterrows():
        prof = row['Professor']

        if prof not in unique_profs:
            unique_profs.append(prof)

    profs_mean_df = pd.DataFrame(columns=classes_df.columns)

    for unique_prof in unique_profs:
        prof_df = classes_df.loc[classes_df['Professor'] == unique_prof]
        prof_mean = prof_df['GPA'].mean()

        d3 = {'Professor': [unique_prof], 'Mean GPA': [prof_mean]}
        prof_mean_df = pd.DataFrame(d3)

        profs_mean_df = pd.concat([profs_mean_df, prof_mean_df], ignore_index=True)

    profs_mean_df = profs_mean_df.sort_values(by=['Mean GPA'], ascending=False)
    ordered_profs = profs_mean_df['Professor'].values.tolist()

    title = f'__Professors Ranked for Course__'
    description = ''
    color = 0x500000

    display_tresh = 8

    for i in range(len(ordered_profs)):
        if i == display_tresh:
            break

        unique_prof = ordered_profs[i]
        unique_prof_df = classes_df.loc[classes_df['Professor'] == unique_prof].sort_values(by=['Year'], ascending=False)
        mean = round(unique_prof_df['GPA'].mean(), 2)
        std = round(unique_prof_df['GPA'].std(), 2)
        start_year = unique_prof_df.iloc[-1, unique_prof_df.columns.get_loc('Year')]
        last_year = unique_prof_df.iloc[0, unique_prof_df.columns.get_loc('Year')]
        class_n = len(unique_prof_df.index)

        grade_df = unique_prof_df.loc[:, unique_prof_df.columns.isin(['A', 'B', 'C', 'D', 'F', 'I', 'S', 'U', 'Q', 'X'])].astype('int')
        cum_grade_df = grade_df.sum().to_frame().T

        grade_df_str = cum_grade_df.to_string(index=False)

        description = f'{description}\n**{unique_prof}** | **μGPA:** {mean}; **σGPA:** {std}; **Taught:** {start_year[2:]}-{last_year[2:]} **Class N:** {class_n}```\n{grade_df_str}\n```'

    year_min = 'None' if year_min == 0 else year_min

    description = f'**Course:** {subject_code.upper()} {course_num}\n**Year Min:** {year_min}\n\n{description.strip()}'

    embed = discord.Embed(title=title, description=description, color=color)

    await ctx.send(embed=embed)
    return

# Returns information for a professor for a specified course.
@bot.command()
async def prof(ctx, first, last, subject_code, course_num, year_min=0):
    now = arrow.utcnow().to('US/Central')

    data = {'dept': subject_code.upper(), 'number': course_num}

    search_url = 'https://anex.us/grades/getData/'
    json_str = requests.post(search_url, data).content

    course_json = json.loads(json_str)
    classes = course_json['classes']

    d1 = {'Section': [], 'Professor': [], 'Year': [], 'Semester': [], 'GPA': [],
         'A': [], 'B': [], 'C': [], 'D': [], 'F': [], 'I': [], 'S': [], 'U': [], 'Q': [], 'X': []}
    classes_df = pd.DataFrame(d1)

    for class_ in classes:
        section = class_['section']
        a_freq = class_['A']
        b_freq = class_['B']
        c_freq = class_['C']
        d_freq = class_['D']
        f_freq = class_['F']
        i_freq = class_['I']
        s_freq = class_['S']
        u_freq = class_['U']
        q_freq = class_['Q']
        x_freq = class_['X']
        prof_name = class_['prof']
        year = class_['year']
        semester = class_['semester']
        gpa = float(class_['gpa'])

        d2 = {'Section': [section], 'Professor': [prof_name], 'Year': [year], 'Semester': [semester], 'GPA': [gpa],
                    'A': [a_freq], 'B': [b_freq], 'C': [c_freq], 'D': [d_freq], 'F': [f_freq], 'I': [i_freq], 'S': [s_freq],
                    'U': [u_freq], 'Q': [q_freq], 'X': [x_freq]}
        class_df = pd.DataFrame(d2)

        classes_df = pd.concat([classes_df, class_df], ignore_index=True)

    prof_df = classes_df[classes_df['Professor'] == f'{last.upper()} {first[0].upper()}']

    if prof_df.empty:
        await ctx.send(f'No past records were found of Professor {first[0].upper()}{first[1:].lower()} {last[0].upper()}{last[1:].lower()} teaching {subject_code.upper()} {course_num}.')
        return

    display_df = prof_df.loc[prof_df['Year'].astype('int') >= int(year_min), ~prof_df.columns.isin(['Section', 'Professor'])].sort_values(by='Year', ascending=False)
    display_df['GPA'] = display_df['GPA'].round(4)
    mean = round(display_df['GPA'].mean(), 4)
    std = round(display_df['GPA'].std(), 4)
    start_year = display_df.iloc[-1, 0]
    last_year = display_df.iloc[0, 0]
    class_n = len(display_df.index)

    display_tresh = 12

    grade_df = display_df.loc[:, ['A', 'B', 'C', 'D', 'F', 'I', 'S', 'U', 'Q', 'X']].astype('int')
    cum_grade_df = grade_df.sum().to_frame().T

    grade_df_str = cum_grade_df.to_string(index=False)
    display_df_str = display_df.iloc[0:display_tresh, :].to_string(index=False)

    center_spacing = len(display_df_str.split('\n')[0]) // 2 - 1
    dots = f'\n{" "*center_spacing}...' if class_n > display_tresh else ''

    file_name = f'{now.timestamp()}_{first.upper()}_{last.upper()}.png'

    plot = plt.bar(x=cum_grade_df.columns, height=cum_grade_df.values[0])
    plt.title(f'Grading Distribution for Professor {first[0].upper()}{first[1:].lower()} {last[0].upper()}{last[1:].lower()}')
    plt.xlabel('Letter Grade')
    plt.ylabel('Frequency')
    plt.savefig(f'tmp/{file_name}')
    plt.close()

    file = discord.File(f'tmp/{file_name}', filename=file_name)
    os.remove(f'tmp/{file_name}')

    year_min = 'None' if year_min == 0 else year_min

    title = '__Professor-Course Grading Information__'
    description = f'**Professor:** {first[0].upper()}{first[1:].lower()} {last[0].upper()}{last[1:].lower()}\n**Course:** {subject_code.upper()} {course_num}\n**Year Min:** {year_min}\n**Mean GPA:** {mean}\n**Std GPA:** {std}\n**Years Taught:** {start_year} - {last_year}\n**Classes Taught:** {class_n}\n\n**Cumulative Grade Distribution:**```\n{grade_df_str}\n```\n**Raw Data:**```\n{display_df_str}{dots}\n```'
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_image(url=f'attachment://{file_name}')

    await ctx.send(file=file, embed=embed)
    return

# Shows real-time open parking garage spaces
@bot.command()
async def garage(ctx):
    search_url = 'https://transport.tamu.edu/Parking/realtime.aspx'
    html_str = requests.get(search_url).content
    soup = BeautifulSoup(html_str, 'html.parser')

    table = soup.find(class_='table table-striped table-condensed')
    trs = table.find_all('tr')[1:]

    tr_parts = []

    for tr in trs:
        td_parts = []

        tds = tr.find_all('td')

        for td in tds:
            td_str = re.sub(r'\n\s*\n', '\n', td.text).strip()
            td_str = re.sub(r'\n\s+', '\n', td_str)
            td_parts.extend([td_str])

        tr_parts.extend([td_parts])

    desc = ''

    spaces_info = [(x[0].split('\r\n'), x[1]) for x in tr_parts]

    for i in range(len(spaces_info)):
        space = spaces_info[i]
        code = space[0][0]
        name = space[0][1]
        space_num = space[1]

        desc = f'{desc}**{name}** ({code}) has {space_num} spaces available.\n\n'

    title = '__Open Parking Garage Spaces__'
    description = desc.strip()
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)

    await ctx.send(embed=embed)
    return

# Shows all of the available bus routes for a specified route group
@bot.command()
async def bus(ctx, group_code='ALL'):
    now = arrow.utcnow().to('US/Central')

    announcements_url = f'https://transport.tamu.edu/BusRoutesFeed/api/Announcements?request.preventCache={now.timestamp()}'
    json_str1 = requests.get(announcements_url).content

    try:
        announcements = json.loads(json_str1)
        items = announcements['Items']

        for item in items:
            links = item['Links']
            url = f'https:{links[0]["Uri"]}'
            datetime = arrow.get(item['PublishDate']).format('M/D/YY @ h:mma')
            a_title = item['Title']['Text']
            summary = item['Summary']['Text']

            title = f'__{a_title}__'
            description = f'**Announcement:** {summary}\n\n**Publish Date:** {datetime}'
            color = 0x500000

            embed = discord.Embed(title=title, description=description, color=color, url=url)

            await ctx.send(embed=embed)
    except:
        pass

    routes_url = f'https://transport.tamu.edu/BusRoutesFeed/api/Routes?request.preventCache={now.timestamp()}'
    json_str2 = requests.get(routes_url).content

    routes = json.loads(json_str2)

    desc = ''

    for route in routes:
        group_name = route['Group']['Name'].replace(' ', '_')

        if group_name.upper() == group_code.upper() or group_code.upper() == 'ALL':
            name = route['Name'].strip()
            code = route['ShortName']

            desc = f'{desc}\n`{code}` {name}'

    category_name = ''

    if group_code.upper() == 'ALL':
        category_name = 'All'
    elif group_code.upper() == 'ON_CAMPUS':
        category_name = 'On Campus'
    elif group_code.upper() == 'OFF_CAMPUS':
        category_name = 'Off Campus'
    elif group_code.upper() == 'GAME_DAY':
        category_name = 'Game Day'
    else:
        await ctx.send('Invalid command argument.')
        return

    title = f'__{category_name} Bus Routes__'
    description = desc.strip()
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)

    await ctx.send(embed=embed)
    return

# Displays information for a specified bus route
@bot.command()
async def route(ctx, route_code, mode='SCALED'):
    now = arrow.utcnow().to('US/Central')

    routes_url = f'https://transport.tamu.edu/BusRoutesFeed/api/Routes?request.preventCache={now.timestamp()}'
    json_str1 = requests.get(routes_url).content

    routes = json.loads(json_str1)

    for route in routes:
        group_name = route['Group']['Name']
        route_name = route['Name'].strip()
        code = route['ShortName']
        # route_color = route['Color']

        if route_code.upper() == code:
            file_name = f'{now.timestamp()}_{code}.png'

            route_url = f'https://transport.tamu.edu/BusRoutesFeed/api/route/{code}/pattern/{now.format("YYYY-MM-DD")}?request.preventCache={now.timestamp()}'
            json_str2 = requests.get(route_url).content

            points = json.loads(json_str2)

            point_list = []
            name_list = []
            rank_list = []
            unique_name_list = []

            for point in points:
                point_name = point['Name']
                lat = float(point['Latitude'])
                lon = float(point['Longtitude'])
                header_rank = point['RouteHeaderRank']

                point = Point(lon, lat)

                point_list.append(point)
                name_list.append(point_name)
                rank_list.append(header_rank)

            line = LineString([[p.x, p.y] for p in point_list])

            plt.plot(*line.xy)
            ax = plt.gca()

            for i in range(len(name_list)):
                point_name = name_list[i]
                point_rank = rank_list[i]

                if point_name != 'Way Point' and point_name not in unique_name_list and point_rank != -1:
                    unique_name_list.append(point_name)

                    coords = list(line.coords)
                    x = coords[i][0]
                    y = coords[i][1]

                    ax.text(x, y, '   ', fontsize=4, bbox=dict(boxstyle='square', fc='blue'))
                    plt.annotate(point_name, xy=(x, y), xytext=(x-30, y), fontsize=8, horizontalalignment='right', verticalalignment='center')

            for j in range(len(name_list)):
                point_name = name_list[j]
                point_rank = rank_list[j]

                if point_name != 'Way Point' and point_name not in unique_name_list and point_rank == -1:
                    unique_name_list.append(point_name)

                    coords = list(line.coords)
                    x = coords[j][0]
                    y = coords[j][1]

                    ax.text(x, y, ' ', fontsize=2, bbox=dict(boxstyle='circle', fc='blue'))
                    plt.annotate(point_name, xy=(x, y), xytext=(x-30, y), fontsize=6, horizontalalignment='right', verticalalignment='center')

            bus_url = f'https://transport.tamu.edu/BusRoutesFeed/api/route/{code}/buses/mentor?request.preventCache={now.timestamp()}'
            json_str = requests.get(bus_url).content

            busses = json.loads(json_str)

            stop_descs = []
            colors = []
            types = []
            passengers = []
            capacities = []

            bus_num = len(busses)

            for bus in busses:
                # bus_name = bus['Name']
                bus_color = bus['Static']['Color']
                bus_type = bus['Static']['Type']
                # driver = bus['Driver'] if bus['Driver'] is None else 'Unknown'
                # bus_datetime = arrow.get(bus['GPS']['Date'])
                direction = float(bus['GPS']['Dir'])
                bus_lat = float(bus['GPS']['Lat'])
                bus_lon = float(bus['GPS']['Long'])
                passenger_cap = bus['APC']['PassengerCapacity']
                passenger_total = bus['APC']['TotalPassenger']
                next_stops = bus['NextStops']

                colors.append(bus_color)
                types.append(bus_type)
                passengers.append(str(passenger_total))
                capacities.append(str(passenger_cap))

                # ax.text(bus_lon, bus_lat, ' ', fontsize=3, bbox=dict(boxstyle='circle', fc='black'))
                ax.text(bus_lon, bus_lat, 'BUS', ha='center', va='center', fontsize=6, rotation=direction+180, bbox=dict(boxstyle='rarrow,pad=0.3', fc='white'))
                # plt.annotate(bus_name, xy=(bus_lon, bus_lat), xytext=(bus_lon, bus_lat), fontsize=4, horizontalalignment='right', verticalalignment='center')

                stop_desc = ''

                for next_stop in next_stops:
                    stop_name = next_stop['Name']
                    # stop_code = next_stop['StopCode']

                    stop_desc = f'**Next Stops:** {stop_name}' if stop_desc == '' else f'{stop_desc}, {stop_name}'

                stop_descs.append(stop_desc)

            stop_descs_parts = '\n'.join(stop_descs)
            colors_parts = ', '.join(colors)
            types_parts = ', '.join(types)
            passengers_parts = ', '.join(passengers)
            capacities_parts = ', '.join(capacities)

            if bus_num == 0:
                bus_desc = '**Bus Status:** Nonoperating'
            else:
                bus_desc = f'**Bus Status:** Operating\n**Busses:** {bus_num}\n**Color:** {colors_parts}\n**Type:** {types_parts}\n**Passengers:** {passengers_parts}\n**Capacity:** {capacities_parts}\n\n{stop_descs_parts}'

            if mode.upper() == 'SCALED':
                pass
            elif mode.upper() == 'REAL':
                ax.set_aspect('equal', 'box')

            plt.title(f'Live Bus Route Visualization for {route_name} ({code})')
            plt.axis('off')
            plt.savefig(f'tmp/{file_name}')
            plt.close()

            file = discord.File(f'tmp/{file_name}', filename=file_name)
            os.remove(f'tmp/{file_name}')

            d1 = {}

            times_url = f'https://transport.tamu.edu/busroutes/Routes.aspx?r={code}'
            times_html = requests.get(times_url).content
            soup = BeautifulSoup(times_html, 'html.parser')

            headers = soup.find_all(class_=f'BGRouteColor RouteColorCompliment Route{code}')

            header_names = []

            for header in headers:
                header_name = header.text
                header_name = header_name[:8] if len(header_name) > 8 else header_name

                if header_name in header_names:
                    header_names[header_names.index(header_name)] = f'{header_names[header_names.index(header_name)]}1'
                    header_names.append(f'{header_name}2')
                else:
                    header_names.append(header_name)

            for h_name in header_names:
                d1[h_name] = []

            df1 = pd.DataFrame(d1)

            trs = soup.find_all('tr')

            for tr in trs[2:]:
                tds = tr.find_all('td')

                d2 = {}

                for i in range(len(tds)):
                    td = tds[i]
                    time = td.text

                    if time.strip() != '':
                        hours = int(time.split(':')[0])
                        new_hours = hours + 12 if time.split(':')[1][-1] == 'P' and hours >= 1 and hours <= 11 else hours
                        minutes = int(time.split(':')[1][:-1])
                        date_time = arrow.utcnow().to('US/Central')
                        exp_time = date_time.replace(hour=new_hours, minute=minutes, second=0, microsecond=0).format('h:mma')
                    else:
                        exp_time = 'None'

                    d2[df1.columns[i]] = [exp_time]

                df2 = pd.DataFrame(d2)

                df1 = pd.concat([df1, df2], ignore_index=True)

            df1_str = df1.to_string(index=False)

            title = '__Bus Route Information__'

            if not df1.empty:
                description = f'**Name:** {route_name}\n**Code:** `{code}`\n**Group:** {group_name}\n\n{bus_desc}\n\n**Estimated Stop Times:**\n```{df1_str}```'
            else:
                description = f'**Name:** {route_name}\n**Code:** `{code}`\n**Group:** {group_name}\n\n{bus_desc}\n\n'

            color = 0x500000

            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_image(url=f'attachment://{file_name}')
            embed.set_footer(text='Bus location updates every 15 seconds.')

            await ctx.send(file=file, embed=embed)
            return

bot.run(TOKEN)
