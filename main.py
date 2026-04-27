import discord
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1496551245186338886

ROLES_IDS = [
    1496551245186338890,
    1496551245186338891,
    1498459697018306670,
    1496551245207572572,
    1496551245186338892,
    1496551245186338893,
    1496551245186338895,
    1496551245207572571,
    1496551245186338894,
    1496551245207572577
]

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN introuvable. Vérifie ton fichier .env ou Railway > Variables.")

guild = discord.Object(id=GUILD_ID)

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.add_command(message, guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Commande /message synchronisée")

client = MyClient()

@app_commands.command(name="message", description="Fait parler le bot")
@app_commands.describe(texte="Le message à envoyer")
async def message(interaction: discord.Interaction, texte: str):
    if not any(role.id in ROLES_IDS for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Tu n'as pas la permission d'utiliser cette commande.",
            ephemeral=True
        )
        return

    await interaction.response.send_message("✅ Message envoyé", ephemeral=True)
    await interaction.channel.send(texte)

@client.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {client.user}")

client.run(TOKEN)
