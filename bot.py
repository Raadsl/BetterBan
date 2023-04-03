import os, time, datetime
import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
from utils import create_embed
from server import start

intents = discord.Intents.default()
intents.members = True
#intents.message_content = True
intents.guilds = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="bb!", intents=intents)

        self.remove_command('help')

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_command_error(self, ctx, error):
        await handle_error(ctx, error, ephemeral=True)

bot = Bot()

# Connect to SQLite database
conn = sqlite3.connect("bot_data.db")
c = conn.cursor()
def setup():
  # Create tables if they don't exist
  c.execute('''CREATE TABLE IF NOT EXISTS banned_users
               (guild_id INTEGER, user_id INTEGER, reason TEXT)''')
  
  c.execute('''CREATE TABLE IF NOT EXISTS error_logs
               (error_id INTEGER PRIMARY KEY AUTOINCREMENT, error_message TEXT)''')
  
  c.execute('''CREATE TABLE IF NOT EXISTS log_channels
               (guild_id INTEGER PRIMARY_KEY, channel_id INTEGER)''')
  
  c.execute('''CREATE TABLE IF NOT EXISTS warnings
               (warning_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, reason TEXT)''')
  
  c.execute('''CREATE TABLE IF NOT EXISTS temp_bans
               (guild_id INTEGER, user_id INTEGER, end_time INTEGER)''')
  
  c.execute('''CREATE TABLE IF NOT EXISTS sticky_roles
               (guild_id INTEGER, user_id INTEGER, role_id INTEGER)''')
  conn.commit()
setup()
start()

async def handle_error(ctx, error, ephemeral=True):
    error_id = None
    await ctx.defer(ephemeral=ephemeral)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed = await create_embed(
                description=f"Missing required argument: {error.param.name}"
        ))
    elif isinstance(error, commands.DisabledCommand):
        await ctx.reply(
            embed=await create_embed(description="This command is disabled."),
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply(  
            embed=await create_embed(description=error),
        )
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.defer(ephemeral=False)
        await ctx.send(embed = await create_embed(
          description="I am missing the required permissions to execute this command. Please fix my permissions!"
        ))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            embed=await create_embed(
                description="You're on cooldown for {:.1f}s".format(error.retry_after)
            )
        )
    elif isinstance(error, commands.NotOwner):
      await ctx.reply(
            embed=await create_embed(
                description="You're not the owner of this bot!"
            )
        )
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(embed= await create_embed(description="Command not found. Please check the command and try again."))
    elif isinstance(error, commands.CommandError):
        if isinstance(error, discord.Forbidden):
              return await ctx.send(embed= await create_embed(description=f"I am missing permissions! Please fix this.\n```{error}```"))
          
        print(f"ERROR: {error}")
        c.execute("INSERT INTO error_logs (error_message) VALUES (?)", (str(error),))
        conn.commit()
        error_id = c.lastrowid
        await ctx.send(f"An error occurred. Error ID: {error_id}. Give this ID to the developers to let them know and fix it!")
    else:
        print(f"An error occurred: {error}")

@tasks.loop(seconds=60)
async def check_temp_bans():
    c.execute("SELECT guild_id, user_id, end_time FROM temp_bans WHERE end_time <= ?", (time.time(),))
    expired_bans = c.fetchall()

    for ban in expired_bans:
        guild_id, user_id, end_time = ban
        guild = bot.get_guild(guild_id)

        if guild:
            async for ban_entry in guild.bans():
                if ban_entry.user.id == user_id:
                    await guild.unban(ban_entry.user)
                    print(f"User with ID {user_id} has been unbanned after temp ban expired in guild {guild_id}.")
                    c.execute("DELETE FROM temp_bans WHERE guild_id=? AND user_id=?", (guild_id, user_id))
                    conn.commit()
                    break

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="BBAN THOSE USERS | /help"))
    print(f"Logged in as {bot.user.name}({bot.user.id})")
    global uptime
    uptime = time.time()
    check_temp_bans.start()
  

@bot.event
async def on_member_join(member):
    guild = member.guild
    user_id = member.id

    # Check if the user has a sticky role
    c.execute("SELECT role_id FROM sticky_roles WHERE guild_id=? AND user_id=?", (guild.id, user_id))
    role_id = c.fetchone()

    if role_id:
        role = guild.get_role(role_id[0])
        if role:
            await member.add_roles(role)
            await send_log_message(guild, f"User {member.display_name} rejoined and was given their sticky role '{role.name}'.")
          
async def moderation_log(guild, action: str, target: discord.Member, moderator: discord.Member, reason: str = "No reason provided"):

    embed = discord.Embed(title=f"{action} | {target}", description=f"Reason: {reason}\nModerator: {moderator}", color=discord.Color.red())
    await send_log_message(guild, embed=embed)


@bot.hybrid_command(
    with_app_command=True,
    name="help",
    description="Shows a list of available commands and their descriptions.",
)
async def help(ctx, command_name: str = None):
    if command_name:
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(title=f"Help - {command.name}", description=command.description, color=discord.Color.blue())
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Command '{command_name}' not found.")
    else:
        embed = discord.Embed(title="Help - Available Commands", color=discord.Color.blue())

        for command in bot.commands:
            embed.add_field(name=command.name, value=command.description, inline=True)
        embed.set_footer(text='Help menu | This message will self destruct in 2 minutes')
        await ctx.send(embed=embed, delete_after=120)
  
@bot.hybrid_command(
    with_app_command=True,
    name="viewwarns",
    description="View all the warns of a user",
)
@commands.has_permissions(kick_members=True)
async def viewwarns(ctx, member: discord.Member):
    c.execute("SELECT warning_id, reason FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    warnings = c.fetchall()

    if warnings:
        embed = discord.Embed(title=f"Warnings for {member.name}", color=discord.Color.red())
        for warning in warnings:
            embed.add_field(name=f"Warning ID: {warning[0]}", value=f"Reason: {warning[1]}", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"{member.name} has no warnings.")

@bot.hybrid_command(
    with_app_command=True,
    name="removewarn",
    description="Remove a warn of a user",
)
@commands.has_permissions(kick_members=True)
async def removewarn(ctx, warning_id: int):
    c.execute("SELECT user_id FROM warnings WHERE guild_id=? AND warning_id=?", (ctx.guild.id, warning_id))
    user_id = c.fetchone()

    if user_id:
        c.execute("DELETE FROM warnings WHERE guild_id=? AND warning_id=?", (ctx.guild.id, warning_id))
        conn.commit()
        await ctx.send(f"Warning with ID {warning_id} has been removed for user with ID {user_id[0]}.")
    else:
        await ctx.send(f"Warning with ID {warning_id} not found.")

@bot.hybrid_command(
    with_app_command=True,
    name="set_sticky_role",
    description="Set a sticky role for a user that persists even after they leave and rejoin the server.",
)
@commands.has_permissions(manage_roles=True)
async def set_sticky_role(ctx, member: discord.Member, role: discord.Role):
    guild = ctx.guild
    c.execute("INSERT OR REPLACE INTO sticky_roles VALUES (?, ?, ?)", (guild.id, member.id, role.id))
    conn.commit()
    await member.add_roles(role)
    await ctx.send(f"Sticky role '{role.name}' has been set for {member.display_name}.")

@bot.hybrid_command(
    with_app_command=True,
    name="invite",
    description="Get the invite link for the bot.",
)
async def invite(ctx):
    invite_url = discord.utils.oauth_url(client_id=bot.user.id, permissions=discord.Permissions(1101927573574), redirect_uri="https://bban.raadsel.tech/invited")
    embed = discord.Embed(title="Invite Link", description=f"[Click here to invite the bot]({invite_url})", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.hybrid_command(
    with_app_command=True,
    name="leave",
    description="[Bot owner only] Leaves the guild",
)
@commands.is_owner()
async def leave(ctx):
    invite_url = discord.utils.oauth_url(client_id=bot.user.id, permissions=discord.Permissions(1101927573574), redirect_uri="https://bban.raadsel.tech/invited")
    await ctx.reply(f"Cya, [Click here]({invite_url}) to invite me again")
    await ctx.guild.leave()

@bot.hybrid_command(
    with_app_command=True,
    name="warn",
    description="Warn a user",
)
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    c.execute("INSERT INTO warnings (guild_id, user_id, reason) VALUES (?, ?, ?)", (ctx.guild.id, member.id, reason))
    conn.commit()
    await ctx.send(f"Warned {member.mention} for reason: {reason}")

@bot.hybrid_command(
    with_app_command=True,
    name="info",
    description="Get some info about the bot.",
)
async def info(ctx):
    await ctx.defer(ephemeral=True)
    
    embed = discord.Embed(title=f"{bot.user.name} Information", color=discord.Color.blue())
    embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
    embed.add_field(name="Bot ID", value=bot.user.id, inline=True)
    embed.add_field(name="Uptime", value=str(datetime.timedelta(seconds=round(time.time() - uptime))), inline=True)
    embed.add_field(name="Website", value="[bban.raadsel.tech](https://bban.raadsel.tech)", inline=True)  
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Command Prefix", value="`/`", inline=True)
    embed.add_field(name="Owner", value="<@790232461052608554>", inline=True)  
    embed.set_thumbnail(url=bot.user.avatar.url)

    await ctx.send(embed=embed)

async def send_log_message(guild, content):
    c.execute("SELECT channel_id FROM log_channels WHERE guild_id=?", (guild.id,))
    result = c.fetchone()
    if result:
        channel_id = result[0]
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(content)
        else:
            print("Log channel not found.")
    else:
        # Send message to the first text channel in the server
        channel = None
        for ch in guild.channels:
            if isinstance(ch, discord.TextChannel):
                channel = ch
                break
        if channel:
            await channel.send(content)
        else:
            print("No text channel found to send the log message.")


async def send_instructions(guild):
    instructions = ("Hey, I'm the BetterBan bot. I was made to ban users that aren't in your server.\n"
                    "To configure me, use the `!set_log_channel` command followed "
                    "by the channel mention where you want to log events.\n"
                    "For example: `!set_log_channel #bot-log`\n\n"
                    "To see all the commands of the bot, run </help:1091695455303389314>"
                   )

    bot_channel = None
    for channel in guild.text_channels:
        if "bot" in channel.name.lower():
            bot_channel = channel
            break

    if bot_channel is None:
        bot_channel = guild.text_channels[0]

    await bot_channel.send(instructions)

@bot.event
async def on_guild_join(guild):
    await send_instructions(guild)

@bot.hybrid_command(
    with_app_command=True,
    name="tempbban",
    description="[Béta] Tempbbans a user",
)
@commands.has_permissions(ban_members=True)
async def tempbban(ctx, user_id, duration: int, *, reason: str = "No reason provided"):
    if not user_id.isnumeric() or not len(user_id) <= 17:
      return ctx.send("Please enter a valid user ID")
    guild = ctx.guild
    user = guild.get_member(int(user_id))
    if user:
        await guild.ban(user, reason=f"Temporarily banned using tempbban command: {reason}")
        await ctx.send(f"User with ID {user_id} has been temporarily banned for {duration} seconds.")
    else:
        c.execute("INSERT INTO banned_users VALUES (?, ?, ?)", (guild.id, user_id, reason))
        conn.commit()
        await ctx.send(f"User with ID {user_id} has been added to tempbban list.")

    c.execute("INSERT INTO temp_bans (guild_id, user_id, end_time) VALUES (?, ?, ?)", (guild.id, user_id, time.time() + duration))
    conn.commit()

@bot.hybrid_command(
    with_app_command=True,
    name="view_error",
    description="[Bot owner only] Get the error message via an ID",
)
@commands.is_owner()
async def view_error(ctx, error_id: int):
    c.execute("SELECT error_message FROM error_logs WHERE error_id=?", (error_id,))
    error_message = c.fetchone()
    await ctx.defer(ephemeral=True)
    if error_message:
        await ctx.reply(f"Error ID {error_id}: ```\npy\n{error_message[0]}```")
    else:
        await ctx.reply(f"Error ID {error_id} not found.")

@bot.hybrid_command(
    with_app_command=True,
    name="set_log_channel",
    description="Set the channel to log messages of the bot.",
)
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    guild = ctx.guild
    c.execute("INSERT OR REPLACE INTO log_channels VALUES (?, ?)", (guild.id, channel.id))
    conn.commit()
    await ctx.send(f"Log channel set to {channel.mention}.")

@bot.event
async def on_member_join(member):
    guild = member.guild
    user_id = member.id

    c.execute("SELECT user_id, reason FROM banned_users WHERE guild_id=? AND user_id=?", (guild.id, user_id))
    banned_user = c.fetchone()

    if banned_user:
        await guild.ban(member, reason=f"Banned using bban command: {banned_user[1]}")
        print(f"User with ID {user_id} joined and was banned.")
        # Send message to the log channel
        await send_log_message(guild, f"User with ID {user_id} joined and was banned for reason: {banned_user[1]}")
    else:
        c.execute("SELECT end_time FROM temp_bans WHERE guild_id=? AND user_id=?", (guild.id, user_id))
        temp_ban = c.fetchone()
        if temp_ban and temp_ban[0] > time.time():
            await guild.ban(member, reason=f"Temporarily banned using tempbban command")
            print(f"User with ID {user_id} joined while tempbbanned and was banned.")
            await send_log_message(guild, f"User with ID {user_id} joined while tempbanned and was banned.")

@bot.hybrid_command(
    with_app_command=True,
    name="bban",
    description="Bans a user from your guild, even if they aren't in your server!",
)
@commands.has_permissions(ban_members=True)
async def bban(ctx, user_id, *, reason: str = "No reason provided"):
    if not user_id.isnumeric() or not len(user_id) >= 16:
      return await ctx.send("Please enter a valid user ID")
    guild = ctx.guild
    user = guild.get_member(int(user_id))
    moderator = ctx.author
    if user:
        await guild.ban(user, reason=f"Banned using bban command: {reason}")
        await ctx.send(f"User with ID {user_id} has been banned.")
        await moderation_log(guild, "Ban", user, moderator, reason)
    else:
        c.execute("INSERT INTO banned_users VALUES (?, ?, ?)", (guild.id, user_id, reason))
        conn.commit()
        await ctx.send(f"User with ID {user_id} has been added to bban list.")

@bot.hybrid_command(
    with_app_command=True,
    name="unbban",
    description="Unbbans a user if they were Bbanned",
)
@commands.has_permissions(ban_members=True)
async def unbban(ctx, user_id):
    if not user_id.isnumeric() or not len(user_id) <= 17:
      return ctx.send("Please enter a valid user ID")
    guild = ctx.guild
    c.execute("DELETE FROM banned_users WHERE guild_id=? AND user_id=?", (guild.id, user_id))
    conn.commit()
    await ctx.send(f"User with ID {user_id} has been removed from bban list.")

@bot.hybrid_command(
    with_app_command=True,
    name="listbban",
    description="Gets a list of all the bbanned user.",
)
@commands.has_permissions(ban_members=True)
async def listbban(ctx):
    guild = ctx.guild
    c.execute("SELECT user_id, reason FROM banned_users WHERE guild_id=?", (guild.id,))
    bban_users = c.fetchall()
    if bban_users:
        embed = discord.Embed(title="Banned Users", color=discord.Color.red())
        for user in bban_users:
            embed.add_field(name=f"User ID: {user[0]}", value=f"Reason: {user[1]}", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("No users in the bban list.")

@bot.hybrid_command(
    with_app_command=True,
    name="remove_all_bban",
    description="Removes all BBanned users.",
)
@commands.has_permissions(ban_members=True)
async def remove_all_bban(ctx):
    guild = ctx.guild
    c.execute("DELETE FROM banned_users WHERE guild_id=?", (guild.id,))
    conn.commit()
    await ctx.send("All BBanned users have been removed.")


@bot.hybrid_command(
    with_app_command=True,
    name="clear_errors",
    description="[Bot owner only] Clears all errors that have an asigned ID",
)
@commands.is_owner()
async def clear_errors(ctx):
    c.execute("DELETE FROM error_logs")
    conn.commit()
    await ctx.defer(ephemeral=True)
    await ctx.send("All errors cleared.")

@bot.hybrid_command(
    with_app_command=True,
    name="test",
    description="Just sum error testing",
)
async def test(ctx):
    raise Exception("Test error")

bot.run(os.environ["TOKEN"])