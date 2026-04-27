import discord
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1496551245186338886

guild = discord.Object(id=GUILD_ID)

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.add_command(message, guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Commande /message synchronisée")

client = MyClient()

@app_commands.command(name="message", description="Fait parler le bot")
@app_commands.describe(texte="Message à envoyer")
async def message(interaction: discord.Interaction, texte: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(texte)
    await interaction.followup.send("✅ Message envoyé", ephemeral=True)

@client.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {client.user}")

client.run(TOKEN)
