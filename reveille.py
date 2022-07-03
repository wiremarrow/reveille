import discord
from discord.ext import commands
import json
import random
import smtplib

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

bot = commands.Bot(command_prefix=PREFIX, help_command=None)

# Sends embed w/ list of commands (command arguments + description)
@bot.command()
async def help(ctx):
    title = ':wrench: **Command Help Menu**'
    description = f'''`{PREFIX}help` - Produces this menu for command help.
    `{PREFIX}register <net_id>` - Register your NetID with the bot to verify yourself.'''
    color = 0x500000

    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

# Initiates registration process w/ email verification (paired w/ verify command for completion)
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

        subject = 'Reveille Bot - Identity Verification'
        body = f'Your verification code is {verif_code}.\n\nIn order to finish verifying, go back to Discord and DM the bot, Reveille, with the following command:\n\n&verify {verif_code}'
        msg = f'Subject: {subject}\n\n{body}'

        smtp.sendmail(sender_email, receiver_email, msg)
    await ctx.send(f'An email has been sent to your TAMU email address ({net_id}@tamu.edu). To confirm your registration through verification, please DM `&verify <code>` to me, Reveille, with the code you were emailed.')

bot.run(TOKEN)
