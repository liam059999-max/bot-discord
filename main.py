import discord
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1496551245186338886  # ID de ton serveur

if TOKEN is None:
    raise ValueError("Token introuvable. Vérifie ton fichier .env")

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Commandes slash synchronisées")

client = MyClient()

@client.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {client.user}")

@client.tree.command(
    name="message",
    description="Fait parler le bot",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(texte="Le message à envoyer")
async def message(interaction: discord.Interaction, texte: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(texte)
    await interaction.followup.send("✅ Message envoyé", ephemeral=True)

client.run(TOKEN)