import discord
from discord.ext import commands
import json
import random
import smtplib
import mysql.connector


# Initialize config/secret vars
c = open('config.json')
s = open('secret.json')

config = json.load(c)
secret = json.load(s)

c.close()
s.close()

PREFIX = config['BOT_COMMAND_PREFIX']
TOKEN = secret['BOT_TOKEN']
EMAIL = config['BOT_EMAIL']
EMAIL_PASS = secret['BOT_EMAIL_PASS']
SQL_USER = config['SQL_USER']
SQL_PASS = secret['SQL_PASS']
DB_NAME = config['SQL_DB_NAME']
USER_TBL_NAME = config['SQL_USER_TBL_NAME']


bot = commands.Bot(command_prefix=PREFIX, help_command=None)

# Sends embed w/ list of commands (command syntax, arguments, + description)
@bot.command()
async def help(ctx):
    title = '**Command Help Menu**'
    description = (f'`{PREFIX}help` - Produces this menu for command help.\n'
                   f'`{PREFIX}register <net_id>` - Register your NetID with the bot to verify yourself.')
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

# Needs a check  if already verified



# Initiates registration process w/ email verification (paired w/ verify command for verif completion)
@bot.command()
async def register(ctx, net_id):
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
        discord_user_id = ctx.message.author.id

        # Checks for past registration w/ DB discord_user_id val lookup - flags if non-zero matches found
        is_registered = False

        try:
            db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=DB_NAME)
            cur = db.cursor()
            cur.execute('SELECT COUNT(1) '
                        f'FROM {USER_TBL_NAME} '
                        f'WHERE discord_user_id = {discord_user_id}')
            
            match_num = int(cur.fetchone()[0])

            if match_num != 0:
                is_registered = True
        except Exception as e:
            await ctx.send(f'Something went wrong while checking for past user registration. {e}')
            return
        
        # Updates user DB records w/ new verif_code and net_id if is_registered, adds new user record to DB if not
        if (is_registered):
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
            if (is_registered):
                await ctx.send(f'You\'ve already a registered user in the database. An email with a new verification code has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration and verify, please DM me, Reveille, your verification code in the form of the command `{PREFIX}verify <verif_code>`.\n\nMake sure to check your spam if you\'re having trouble!')
            else:
                await ctx.send(f'An email with a verification code has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration and verify, please DM me, Reveille, your verification code in the form of the command `{PREFIX}verify <verif_code>`.\n\nMake sure to check your spam if you\'re having trouble!')
        except Exception as e:
            await ctx.send(f'Something went wrong while sending verification email. {e}')
            return

# Verifies users w/ DB verif_code val lookup comparison, updates is_verif val to 1 if code match
@bot.command()
async def verify(ctx, verif_code):
    # to do
    await ctx.send('You\'re successfully verified! You now have full server/bot functionality.')

bot.run(TOKEN)
