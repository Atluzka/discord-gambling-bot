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

def getUserData(userid):
    cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
    userdataresult = cursor.fetchone()
    return userdataresult

def updateMoney(userid, amount):
    cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
    userdataresult = cursor.fetchone()
    if userdataresult:
        cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (userdataresult[1] + amount,userid))
        datab.commit()
        return True
    else:
        return False

def setMoney(userid, amount):
    cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
    userdataresult = cursor.fetchone()
    if userdataresult:
        cursor.execute("UPDATE users SET balance = (?) WHERE userid = (?)", (amount,userid))
        datab.commit()
        return True
    else:
        return False

def saveData(userid):
    cursor.execute("SELECT * FROM users WHERE userid = ?", (userid,))
    userdataresult = cursor.fetchone()
    if not userdataresult:
        cursor.execute("INSERT INTO users (userid, balance) VALUES (?, ?)", (userid, config["starting_balance"]))
        datab.commit()
        return True
    else:
        return False

def cooldown_event(ctx): 
    if not config['command-cooldown']:
        return None
    else:
        return commands.Cooldown(1, config['cmd-cooldown-duration'])

@bot.slash_command(name="coinflip", description="Flip a coin and bet money.")
@commands.dynamic_cooldown(cooldown_event, commands.BucketType.user)
async def coinflip(interaction: discord.Interaction, bet_amount: int, guess: str):
    if bet_amount < config["minimum-coinflip-bet"]:
        await interaction.response.send_message("You have to bet at least ${0}.".format(config["minimum-coinflip-bet"]) , ephemeral=True)
        return
    if saveData(interaction.user.id):
        if config["starting_balance"] < config["minimum-coinflip-bet"]:
            await interaction.response.send_message(f"You don't have enough money to bet.", ephemeral=True)
            return
    if guess.lower() not in ['heads', 'tails']:
        await interaction.response.send_message(f"Invalid guess. You can only guess HEADS or TAILS", ephemeral=True)
        return
    userData = getUserData(interaction.user.id)
    if userData[1] < bet_amount:
        await interaction.response.send_message(f"You don't have enough money to bet.", ephemeral=True)
        return
    
    result = random.choice(['heads', 'tails'])
    if guess.lower() == result:
        win_amount = math.ceil(config['win-multiplier']*bet_amount)
        payout = win_amount - bet_amount
        updateMoney(interaction.user.id, payout)
        embed=discord.Embed()
        embed.description="Congratulations, you won!"
        embed.set_footer(text="Balance: $" + str(userData[1] + payout) + ".")
        embed.color=0x3fff7c
        await interaction.response.send_message(embed=embed)
    else:
        updateMoney(interaction.user.id, -bet_amount)
        embed=discord.Embed()
        embed.description=f"Sorry, the coin landed on {result}."
        embed.set_footer(text="Balance: $" + str(userData[1] + -bet_amount) + ".")
        embed.color=0xff3f3f
        await interaction.response.send_message(embed=embed)

@coinflip.error
async def gencmd_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f'You can flip a coin again in {error.retry_after:.2f} seconds.', ephemeral=True)

def work_cooldown(ctx): 
    if not config['command-cooldown']:
        return None
    else:
        return commands.Cooldown(1, config['work-cooldown'])

@bot.slash_command(text="work", description="Work to get money.. and then gamble it away.")
@commands.dynamic_cooldown(work_cooldown, commands.BucketType.user)
async def work(interaction: discord.Interaction):
    saveData(interaction.user.id)
    userData = getUserData(interaction.user.id)
    payout = random.randint(config["work-min-payment"], config["work-max-payment"])
    updateMoney(interaction.user.id, payout)
    embed=discord.Embed()
    embed.description=str(random.choice(config["work-messages"])) + '$' + str(payout)
    embed.set_footer(text="Balance: $" + str(int(userData[1]) + payout) + ".")
    embed.color=0x2B2D31
    await interaction.response.send_message(embed=embed)

@work.error
async def gencmd_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f'You can work again in {error.retry_after:.2f} seconds.', ephemeral=True)

@bot.slash_command(text="balance", description="See how much money you have.")
async def balance(interaction: discord.Interaction, user: str = None):
    if user == None or user.isnumeric() and int(user,10) == interaction.user.id:
        saveData(interaction.user.id)
        userData = getUserData(interaction.user.id)
        embed=discord.Embed()
        embed.title=f"{interaction.user.name}'s Balance"
        embed.description=f'You have ${userData[1]}'
        embed.color=0xffaf58
        await interaction.response.send_message(embed=embed)
    elif user.isnumeric():
        user = int(user, 10)
        userData = getUserData(user)
        if not userData:
            await interaction.response.send_message(f"This user doesn't exist", ephemeral=True)
            return
        theuser = await bot.fetch_user(user)
        embed=discord.Embed()
        embed.title=f"{theuser.name}'s Balance"
        embed.description=f'They have ${userData[1]}'
        embed.color=0xffaf58
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Invalid userid.", ephemeral=True)

@bot.slash_command(text="setbalance", description="Change the amount of money someone has. (ADMIN ONLY)")
async def setbalance(interaction: discord.Interaction, amount: int, user: str = None):
    if interaction.user.id in config["admins"]:
        if user == None:
            saveData(interaction.user.id)
            setMoney(interaction.user.id, amount)
            await interaction.response.send_message(f"Successfully set {interaction.user.name}'s balance to {amount}", ephemeral=True)
        elif user.isnumeric():
            user = int(user, 10)
            saveData(user)
            setMoney(user, amount)
            theuser = await bot.fetch_user(user)
            await interaction.response.send_message(f"Successfully set {theuser.name}'s balance to {amount}", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid userid.", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have permissions to use this command", ephemeral=True)

bot.run(config['token'])
