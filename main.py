import discord
from discord import app_commands
import os
import json
import time
import re
import asyncio
import random
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1496551245186338886

JOUEUR_ROLE_ID = 1496570449830871191
WELCOME_CHANNEL_ID = 1497575977222668388
GIVEAWAY_ROLE_ID = 1496551245186338891

MESSAGE_IMAGE_URL = "TON_LIEN_IMAGE_ICI"
MESSAGE_LOGO_URL = "https://i.ibb.co/5gLvzLcD/n-bulix.png"

ROLES_MESSAGE_IDS = [
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

DATA_FILE = "moderation.json"

SPAM_LIMIT = 5
SPAM_SECONDS = 6
SPAM_MUTE_MINUTES = 10

spam_cache = {}
invites_cache = {}

DISCORD_INVITE_REGEX = re.compile(
    r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)",
    re.IGNORECASE
)


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"log_channel_id": None, "warnings": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


async def send_log(guild: discord.Guild, title: str, description: str, color=discord.Color.blurple()):
    data = load_data()
    channel_id = data.get("log_channel_id")

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Nebulix — Modération")
    await channel.send(embed=embed)


def has_joueur_role(member: discord.Member):
    role = member.guild.get_role(JOUEUR_ROLE_ID)
    return role in member.roles if role else False


def has_message_permission(member: discord.Member):
    return any(role.id in ROLES_MESSAGE_IDS for role in member.roles)


def parse_duration(duration: str):
    try:
        unit = duration[-1].lower()
        value = int(duration[:-1])

        if unit == "s":
            return value
        if unit == "m":
            return value * 60
        if unit == "h":
            return value * 3600
        if unit == "d":
            return value * 86400

        return None
    except:
        return None


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Commandes synchronisées")


client = MyClient()


@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")

    for guild in client.guilds:
        try:
            invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in invites}
        except discord.Forbidden:
            invites_cache[guild.id] = {}


@client.event
async def on_member_join(member: discord.Member):
    role = member.guild.get_role(JOUEUR_ROLE_ID)

    if role:
        try:
            await member.add_roles(role, reason="Rôle Joueur automatique")
        except discord.Forbidden:
            pass

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        inviter = None
        total_uses = 0

        try:
            invites_before = invites_cache.get(member.guild.id, {})
            invites_after = await member.guild.invites()

            new_cache = {}

            for invite in invites_after:
                new_cache[invite.code] = invite.uses

                if invite.code in invites_before and invite.uses > invites_before[invite.code]:
                    inviter = invite.inviter
                    total_uses = invite.uses

            invites_cache[member.guild.id] = new_cache
        except discord.Forbidden:
            pass

        inviter_text = inviter.mention if inviter else "Inconnu"

        await channel.send(
            f"👋 Bienvenue à {member.mention}\n"
            f"📩 Il a été invité par {inviter_text}\n"
            f"👑 Il a désormais **{total_uses} invitations**\n"
            f"⭐ Nous sommes désormais **{member.guild.member_count}** sur le discord !"
        )


@client.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    member = message.author

    if not isinstance(member, discord.Member):
        return

    if not has_joueur_role(member):
        return

    if DISCORD_INVITE_REGEX.search(message.content):
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        try:
            await member.kick(reason="Lien Discord interdit")
        except discord.Forbidden:
            await send_log(
                message.guild,
                "❌ Kick impossible",
                f"**Membre :** {member.mention}\n**Raison :** Permission insuffisante.",
                discord.Color.red()
            )
            return

        await send_log(
            message.guild,
            "🚫 Kick automatique",
            (
                f"**Membre :** {member.mention}\n"
                f"**Raison :** Lien Discord interdit\n"
                f"**Salon :** {message.channel.mention}"
            ),
            discord.Color.red()
        )
        return

    now = time.time()
    user_id = member.id

    if user_id not in spam_cache:
        spam_cache[user_id] = []

    spam_cache[user_id].append(now)

    spam_cache[user_id] = [
        timestamp for timestamp in spam_cache[user_id]
        if now - timestamp <= SPAM_SECONDS
    ]

    if len(spam_cache[user_id]) >= SPAM_LIMIT:
        spam_cache[user_id] = []

        try:
            await member.timeout(
                timedelta(minutes=SPAM_MUTE_MINUTES),
                reason="Spam automatique"
            )
        except discord.Forbidden:
            await send_log(
                message.guild,
                "❌ Mute impossible",
                f"**Membre :** {member.mention}\n**Raison :** Permission insuffisante.",
                discord.Color.red()
            )
            return

        await send_log(
            message.guild,
            "🔇 Mute automatique",
            (
                f"**Membre :** {member.mention}\n"
                f"**Raison :** Spam\n"
                f"**Durée :** {SPAM_MUTE_MINUTES} minutes\n"
                f"**Salon :** {message.channel.mention}"
            ),
            discord.Color.orange()
        )


@client.tree.command(
    name="message",
    description="Fait parler le bot avec un embed",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(texte="Le message à envoyer dans l'embed")
async def message(interaction: discord.Interaction, texte: str):
    if not has_message_permission(interaction.user):
        await interaction.response.send_message(
            "❌ Tu n'as pas la permission d'utiliser cette commande.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        description=texte,
        color=discord.Color.purple()
    )

    embed.set_thumbnail(url=MESSAGE_LOGO_URL)
    embed.set_image(url=MESSAGE_IMAGE_URL)
    embed.set_footer(text="Nebulix FA 💜")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Message envoyé.", ephemeral=True)


@client.tree.command(
    name="logs-channel",
    description="Définit le salon des logs de modération",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(salon="Salon où envoyer les logs")
@app_commands.checks.has_permissions(administrator=True)
async def logs_channel(interaction: discord.Interaction, salon: discord.TextChannel):
    data = load_data()
    data["log_channel_id"] = salon.id
    save_data(data)

    await interaction.response.send_message(
        f"✅ Salon logs défini sur {salon.mention}.",
        ephemeral=True
    )


# Garde ici toutes tes autres commandes modération/giveaway
# clear, kick, ban, unban, mute, unmute, warn, warnings, clear-warns,
# giveaway-start, giveaway-reroll, giveaway-end


client.run(TOKEN)
