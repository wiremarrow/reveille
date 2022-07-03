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
SQL_DB_NAME = config['SQL_DB_NAME']


bot = commands.Bot(command_prefix=PREFIX, help_command=None)

# Sends embed w/ list of commands (command arguments + description)
@bot.command()
async def help(ctx):
    title = '**Command Help Menu**'
    description = (f'`{PREFIX}help` - Produces this menu for command help.\n'
                   f'`{PREFIX}register <net_id>` - Register your NetID with the bot to verify yourself.')
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

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

        subject = 'Reveille Bot - Identity Verification'
        body = f'Your verification code is {verif_code}.\n\nIn order to finish verifying, go back to Discord and DM the bot, Reveille, with the following command:\n\n{PREFIX}verify {verif_code}'
        msg = f'Subject: {subject}\n\n{body}'

        try:
            db = mysql.connector.connect(host='localhost', user=SQL_USER, passwd=SQL_PASS, database=SQL_DB_NAME)
            cur = db.cursor()
            cur.execute(f'INSERT INTO users (discord_user_id, net_id, verif_code, is_verif) '
                        f'VALUES ({discord_user_id}, \'{net_id}\', {verif_code}, 0)')

            db.commit()
        except Exception as e:
            await ctx.send(f'Something went wrong. {e}')
            return

        try:
            smtp.sendmail(sender_email, receiver_email, msg)
            await ctx.send(f'An email with a verification code has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration and verify, please DM me, Reveille, your verification code in the form of the command `{PREFIX}verify <verif_code>`.\n\nMake sure to check your spam if you\'re having trouble!')
        except Exception as e:
            await ctx.send(f'Something went wrong. {e}')
            return

# Verifies users and adds profile to assisting MySQL database
@bot.command()
async def verify(ctx, verif_code):
    # to do
    await ctx.send('You\'re successfully verified! You now have full server/bot functionality.')

bot.run(TOKEN)
