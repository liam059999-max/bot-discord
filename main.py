import discord
from discord import app_commands
import os
from dotenv import load_dotenv

# Charger le .env (pour local)
load_dotenv()

# Récupérer le token (Railway + local)
TOKEN = os.getenv("DISCORD_TOKEN")

# ⚠️ Remplace par l'ID de TON serveur
GUILD_ID = 1496551245186338886

if TOKEN is None:
    raise ValueError("❌ Token introuvable. Vérifie Railway ou ton .env")

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
    print(f"✅ Connecté en tant que {client.user}")

# ✅ COMMANDE /message
@client.tree.command(
    name="message",
    description="Fait parler le bot",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(texte="Le message à envoyer")
async def message(interaction: discord.Interaction, texte: str):
    
    # IMPORTANT → évite "application ne répond pas"
    await interaction.response.defer(ephemeral=True)

    await interaction.channel.send(texte)

    await interaction.followup.send("✅ Message envoyé", ephemeral=True)

# Lancer le bot
client.run(TOKEN)
