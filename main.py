import datetime
import json
import os
from time import time

import discord
from discord import Reaction, User
from discord.ext import tasks, commands
from dotenv import load_dotenv

from aternos_api import Account

load_dotenv()

USERNAME = os.getenv('USR')
PASSWORD = os.getenv('PASS')
TOKEN = os.getenv('DISCORD_TOKEN')
n = '\n'
print("|--------------------------------------------------\n| Getting Account :", end="")
start = time()
a = Account(USERNAME, PASSWORD)
end = time()
print(str((end - start)/60)[:4] + "s")
print("|--------------------------------------------------")
servers_to_get = ["XS97wsJVTQpx9kb8","Tlok9VtWOlZu0inn","PBFElolI6WTcNIU9"]
minecraft_servers = []

for server in a.servers:
	if server.id in servers_to_get:
		minecraft_servers.append(server)

for minecraft_server in minecraft_servers:
	print(f"| fetch {minecraft_server.name} :", end="")
	start = time()
	minecraft_server.fetch()
	end = time()
	print(f"{ str((end -start)/60)[:4]}s")


if os.path.exists("save.json"):
	with open("save.json", "r")as f:
		servers = json.load(f)
else:
	servers = {}
bot = commands.Bot(command_prefix="!aternos")


@bot.event
async def on_ready():
	print(f"""|--------------------------------------------------
|  Logged in as {bot.user.name}#{bot.user.id}
|  Discord.py {discord.__version__}
|--------------------------------------------------
|  bot connected to :\n{n.join(["|     "+server.name + str(server.id) for server in bot.guilds])}
|--------------------------------------------------""")


async def send_embed(text_channel, minecraft_server_to_send):
	global servers_to_get
	try:
		color = {
			"offline": 0xff0000,
			"online": 0x00ff00,
			"crashed": 0xff00ff,
		}[minecraft_server_to_send.status]
	except KeyError:
		color = 0xffff00
	embed = discord.Embed(
		title=minecraft_server_to_send.name,
		colour=discord.Colour(color),
		description=minecraft_server_to_send.motd,
		timestamp=datetime.datetime.utcfromtimestamp(time())
	)

	embed.set_thumbnail(
		url=f"https://api.minetools.eu/favicon/{minecraft_server_to_send.ip}/"
	)
	i = await bot.application_info()
	embed.set_footer(
		text=f"{ bot.user.name } stat by { i.owner.name }",
		icon_url=i.owner.avatar_url
	)
	try:
		emoji = {
			"offline": ":red_circle:",
			"online": ":green_circle:",
			"crashed": ":purple_circle:",
		}[minecraft_server_to_send.status]
	except KeyError:
		emoji = ":yellow_circle:"

	embed.add_field(name="Current state", value=f"{emoji} **{minecraft_server_to_send.status}**")
	if minecraft_server_to_send.countdown:
		embed.add_field(name="remaining time", value=str(minecraft_server_to_send.countdown / 60)[:3])
	embed.add_field(name="static IP", value=minecraft_server_to_send.ip)
	if minecraft_server_to_send.connect_ip:
		embed.add_field(name="dynamic IP", value=minecraft_server_to_send.connect_ip)

	embed.add_field(
		name="Connected Players",
		inline=False,
		value=f"""**{len(minecraft_server_to_send.players)}/{minecraft_server_to_send.max_players}**
	```
{n.join(['- ' + player.name for player in minecraft_server_to_send.players]) if len(minecraft_server_to_send.players) > 0 else
		'no players connected'}```"""
	)
	#
	if minecraft_server_to_send.name in servers[str(text_channel.guild.id)].keys():
		if minecraft_server_to_send.id in servers_to_get:
			servers[str(text_channel.guild.id)][minecraft_server_to_send.name] = 0
			servers_to_get.remove(minecraft_server_to_send.id)
		try:
			msg = await text_channel.fetch_message(servers[str(text_channel.guild.id)][minecraft_server_to_send.name])

			await msg.edit(embed=embed)
		except discord.errors.NotFound:
			msg = await text_channel.send(embed=embed, )
			servers[str(text_channel.guild.id)][minecraft_server_to_send.name] = msg.id
			with open("save.json", "w") as f:
				json.dump(servers, f, indent=2)
		await msg.clear_reactions()
		if minecraft_server_to_send.status in ("offline", "crashed"):
			await msg.add_reaction('🟢')
		await msg.add_reaction("🔄")
	else:
		print(f"\n| setting-up {minecraft_server_to_send.name}")
		servers[str(text_channel.guild.id)][minecraft_server_to_send.name] = 0


class CheckServers(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.check_servers.start()

	def cog_unload(self):
		self.check_servers.cancel()

	@commands.Cog.listener()
	async def on_reaction_add(self, reaction: Reaction, user: User):
		if user.id != bot.user.id:
			for minecraft_server in minecraft_servers:
				if reaction.message.id == servers[str(reaction.message.guild.id)][minecraft_server.name]:
					if reaction.emoji == "🟢":
						if minecraft_server.status == ("offline", "crashed"):
							minecraft_server.start()
					if reaction.emoji == "🔄":
						for text_channel in reaction.message.guild.text_channels:
							if text_channel.id == servers[str(reaction.message.guild.id)]["channel_id"]:
								await send_embed(text_channel, minecraft_server)

	@tasks.loop(seconds=5.0)
	async def check_servers(self):
		for server in bot.guilds:
			if str(server.id) in servers.keys():
				for text_channel in server.text_channels:
					if text_channel.id == servers[str(server.id)]["channel_id"]:
						for minecraft_server in minecraft_servers:
							start = time()
							print(f"| actualising {minecraft_server.name} :", end="")
							minecraft_server.fetch()
							await send_embed(text_channel, minecraft_server)
							end = time()
							print(str((end - start) / 60)[:4] + "s")
						print("|--------------------------------------------------")



	@check_servers.before_loop
	async def before_check_servers(self):
		await self.bot.wait_until_ready()


@bot.event
async def on_message(message: discord.message.Message):
	if message.content.__contains__("!aternos here"):
		for minecraft_server in minecraft_servers:
			if message.guild.id in servers.keys():
				servers[message.guild.id]["channel_id"] = message.channel.id
				servers[message.guild.id][minecraft_server.name] = 0
			else:
				servers[message.guild.id] = {"channel_id": message.channel.id, minecraft_server.name: 0}
			with open("save.json", "w") as f:
				json.dump(servers, f, indent=2)


bot.add_cog(CheckServers(bot))

try:
	bot.run(TOKEN)
except Exception as e:
	a.close()
	raise e

# a.close()
