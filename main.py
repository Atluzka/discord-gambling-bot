import discord, json, os, random, math, sqlite3
from discord.ext import commands

bot = commands.Bot(intents=discord.Intents.all())
bot.remove_command('help')
curdir = os.getcwd() # current directory the python file is in.

jsonconfig = open(curdir + '/config.json')
config = json.load(jsonconfig)
datab = sqlite3.connect('data.db')
cursor = datab.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(userid, balance)")

@bot.event
async def on_ready():
    print("{0.user}".format(bot))

def normal_cooldown(ctx): 
    if not config['command-cooldown']:
        return None
    else:
        return commands.Cooldown(1, config['cmd-cooldown-duration'])

@bot.slash_command(name="coinflip", description="Flip a coin. Heads or tails.")
@commands.dynamic_cooldown(normal_cooldown, type=commands.BucketType.user)
async def coinflip(interaction: discord.Interaction, guess: str, bet_amount: int):
    if bet_amount < config["minimum-coinflip-bet"]:
        await interaction.response.send_message("Sorry but the minimum bet amount is {0}".format(config["minimum-coinflip-bet"]))
        return
    cursor.execute("SELECT * FROM users WHERE userid = ?", (interaction.user.id,))
    userdataresult = cursor.fetchone()
    if not userdataresult:
        cursor.execute("INSERT INTO users (userid, balance) VALUES (?, ?)", (interaction.user.id, 0))
        await interaction.response.send_message("Sorry, but you do not have enough money to bet.")
        datab.commit()
        return
    if userdataresult[1] < bet_amount:
        await interaction.response.send_message("Sorry, but you do not have enough money to bet.")
        return
    cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (int(userdataresult[1]) - int(bet_amount), interaction.user.id))
    if guess.lower() not in ['heads', 'tails']:
        await interaction.response.send_message("Invalid guess. You can only guess HEADS or TAILS")
        return
    result = random.choice(['heads', 'tails'])
    if guess.lower() == result: #guess.lower() == result -- FOR TESTING ONLY
        win_amount = math.ceil(config['win-multiplier']*bet_amount)
        cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (int(userdataresult[1]) + int(win_amount), interaction.user.id))
        datab.commit()
        embed=discord.Embed(title='Congratulations you won!',
                            description="Your guess was **{0}**, you've won **{1}** {2}.".format(guess.upper(), win_amount, config["currency-name"]),
                            color=0x3fff7c)
        #cursor.execute("UPDATE users (userid, balance) VALUES (?, ?)", (interaction.user.id, 1200))
        embed.set_footer(text="Balance: {0}".format(str(int(userdataresult[1]) + int(win_amount))))
        await interaction.response.send_message(embed=embed)
    else:
        embed=discord.Embed(title='You lost!',
                            description="Your guess was **{0}**.".format(guess.upper()),
                            color=0xff3f3f)
        embed.set_footer(text="Balance: {0}".format(str(int(userdataresult[1]) - int(bet_amount))))
        await interaction.response.send_message(embed=embed)
        datab.commit()
    
@coinflip.error
async def gencmd_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f'Cooldown. Try again in {error.retry_after:.2f} seconds.')

@bot.slash_command(name="money", description="command to get free money yay!")
async def freemoney(interaction: discord.Interaction, amount: int, userid: str = None):
    if interaction.user.id in config["admins"]:
        if userid == None:
            cursor.execute("SELECT * FROM users WHERE userid = ?", (interaction.user.id,))
            userdataresult = cursor.fetchone()
            if not userdataresult:
                cursor.execute("INSERT INTO users (userid, balance) VALUES (?, ?)", (interaction.user.id, 0))
                #await interaction.response.send_message("Sorry, but you do not have enough money to bet.")
            cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (amount, interaction.user.id))
            await interaction.response.send_message("Done.")
            datab.commit()
        elif userid.isnumeric():
            userid = int(userid, 10)
            cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
            userdataresult = cursor.fetchone()
            if not userdataresult:
                cursor.execute("INSERT INTO users (userid, balance) VALUES (?, ?)", (userid, 0))
            cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (amount, userid))
            datab.commit()
            await interaction.response.send_message("Done.")
        else:
            await interaction.response.send_message("Error.")
    else:
        await interaction.response.send_message("You don't have enough permissions to run this command.")

@bot.slash_command(name="balance", description="Check your or someone elses balance.")
async def balance(interaction: discord.Interaction, userid: str = None):
    if not userid == None and not userid.isnumeric():
        await interaction.response.send_message("Invalid userid.")
        return
    
    if userid == None or not userid.isnumeric():
        cursor.execute("SELECT * FROM users WHERE userid = ?", (interaction.user.id,))
        userdataresult = cursor.fetchone()
        userid = interaction.user.id
    else:
        userid = int(userid, 10)
        cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
        userdataresult = cursor.fetchone()
    if not userdataresult:
        if userid == interaction.user.id:
            cursor.execute("INSERT INTO users (userid, balance) VALUES (?, ?)", (interaction.user.id, 0))
            datab.commit()

            cursor.execute("SELECT * FROM users WHERE userid = ?", (interaction.user.id,))
            userdataresult = cursor.fetchone()
        else:
            await interaction.response.send_message("This user doesn't exist.")
            return

    embed=discord.Embed()
    embed.color=0xffaf58
    if userid == interaction.user.id:
        embed.title="Your balance!"
        embed.description="You have **{0}** {1}".format(userdataresult[1], config["currency-name"])
    else:
        embed.title='Balance!'
        embed.description="They have **{0}** {1}".format(userdataresult[1], config["currency-name"])
    await interaction.response.send_message(embed=embed)

bot.run(config['token'])