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
FONDATEUR_ROLE_ID = 1496551245186338891
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
        return {
            "log_channel_id": None,
            "warnings": {},
            "invites": {}
        }

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    data.setdefault("log_channel_id", None)
    data.setdefault("warnings", {})
    data.setdefault("invites", {})

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def has_joueur_role(member: discord.Member):
    return has_role(member, JOUEUR_ROLE_ID)


def has_fondateur_role(member: discord.Member):
    return has_role(member, FONDATEUR_ROLE_ID)


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
    except Exception:
        return None


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
            invites_cache[guild.id] = {
                invite.code: invite.uses for invite in invites
            }
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

    if inviter:
        data = load_data()
        inviter_id = str(inviter.id)

        data["invites"].setdefault(inviter_id, 0)
        data["invites"][inviter_id] += 1

        save_data(data)

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if channel:
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

    if DISCORD_INVITE_REGEX.search(message.content) and not has_fondateur_role(member):
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

    spam_cache.setdefault(user_id, [])
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
    name="classement",
    description="Affiche le classement des invitations",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.checks.has_role(FONDATEUR_ROLE_ID)
async def classement(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    data = load_data()
    invites_data = data.get("invites", {})

    try:
        guild_invites = await interaction.guild.invites()

        for invite in guild_invites:
            if invite.inviter:
                inviter_id = str(invite.inviter.id)
                invites_data[inviter_id] = max(
                    invites_data.get(inviter_id, 0),
                    invite.uses or 0
                )

        data["invites"] = invites_data
        save_data(data)

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Je n'ai pas la permission `Gérer le serveur` pour lire les invitations.",
            ephemeral=True
        )
        return

    if not invites_data:
        await interaction.followup.send(
            "❌ Aucun classement disponible.",
            ephemeral=False
        )
        return

    sorted_invites = sorted(
        invites_data.items(),
        key=lambda x: x[1],
        reverse=True
    )

    description = ""
    medals = ["🥇", "🥈", "🥉"]

    for index, (user_id, count) in enumerate(sorted_invites[:10], start=1):
        member = interaction.guild.get_member(int(user_id))
        name = member.mention if member else f"<@{user_id}>"
        rank = medals[index - 1] if index <= 3 else f"**#{index}**"

        description += f"{rank} {name} — **{count} invitation(s)**\n"

    embed = discord.Embed(
        title="🏆 Classement des invitations",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Nebulix — Invitations")

    await interaction.followup.send(embed=embed, ephemeral=False)


@client.tree.command(
    name="message",
    description="Fait parler le bot avec un embed",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(texte="Le message à envoyer dans l'embed")
async def message(interaction: discord.Interaction, texte: str):
    await interaction.response.defer(ephemeral=True)

    if not has_message_permission(interaction.user):
        await interaction.followup.send(
            "❌ Tu n'as pas la permission d'utiliser cette commande.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        description=texte,
        color=discord.Color.purple()
    )

    if MESSAGE_LOGO_URL.startswith("https://"):
        embed.set_thumbnail(url=MESSAGE_LOGO_URL)

    if MESSAGE_IMAGE_URL.startswith("https://"):
        embed.set_image(url=MESSAGE_IMAGE_URL)

    embed.set_footer(text="Nebulix FA 💜")

    await interaction.channel.send(embed=embed)

    await interaction.followup.send(
        "✅ Message envoyé.",
        ephemeral=True
    )


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


@client.tree.command(
    name="clear",
    description="Supprime un nombre de messages",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(nombre="Nombre de messages à supprimer")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)

    if nombre < 1 or nombre > 100:
        await interaction.followup.send(
            "❌ Choisis un nombre entre 1 et 100.",
            ephemeral=True
        )
        return

    deleted = await interaction.channel.purge(limit=nombre)

    await interaction.followup.send(
        f"✅ {len(deleted)} message(s) supprimé(s).",
        ephemeral=True
    )


@client.tree.command(
    name="kick",
    description="Expulse un membre du serveur",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à expulser", raison="Raison du kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison donnée"):
    await interaction.response.defer(ephemeral=True)

    if membre == interaction.user:
        await interaction.followup.send("❌ Tu ne peux pas te kick toi-même.", ephemeral=True)
        return

    if membre.top_role >= interaction.guild.me.top_role:
        await interaction.followup.send("❌ Mon rôle est trop bas pour kick ce membre.", ephemeral=True)
        return

    await membre.kick(reason=raison)

    await interaction.followup.send(
        f"✅ {membre.mention} a été kick.\n📄 Raison : {raison}",
        ephemeral=True
    )


@client.tree.command(
    name="ban",
    description="Bannit un membre du serveur",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à bannir", raison="Raison du ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison donnée"):
    await interaction.response.defer(ephemeral=True)

    if membre == interaction.user:
        await interaction.followup.send("❌ Tu ne peux pas te ban toi-même.", ephemeral=True)
        return

    if membre.top_role >= interaction.guild.me.top_role:
        await interaction.followup.send("❌ Mon rôle est trop bas pour ban ce membre.", ephemeral=True)
        return

    await membre.ban(reason=raison)

    await interaction.followup.send(
        f"✅ {membre.mention} a été banni.\n📄 Raison : {raison}",
        ephemeral=True
    )


@client.tree.command(
    name="mute",
    description="Met un membre en timeout",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à mute", minutes="Durée en minutes", raison="Raison du mute")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Aucune raison donnée"):
    await interaction.response.defer(ephemeral=True)

    if minutes < 1 or minutes > 40320:
        await interaction.followup.send(
            "❌ Durée invalide. Maximum : 40320 minutes.",
            ephemeral=True
        )
        return

    if membre.top_role >= interaction.guild.me.top_role:
        await interaction.followup.send(
            "❌ Mon rôle est trop bas pour mute ce membre.",
            ephemeral=True
        )
        return

    await membre.timeout(timedelta(minutes=minutes), reason=raison)

    await interaction.followup.send(
        f"✅ {membre.mention} a été mute pendant {minutes} minute(s).\n📄 Raison : {raison}",
        ephemeral=True
    )


@client.tree.command(
    name="unmute",
    description="Retire le timeout d'un membre",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à unmute", raison="Raison du unmute")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison donnée"):
    await interaction.response.defer(ephemeral=True)

    await membre.timeout(None, reason=raison)

    await interaction.followup.send(
        f"✅ {membre.mention} a été unmute.\n📄 Raison : {raison}",
        ephemeral=True
    )


@client.tree.command(
    name="warn",
    description="Avertit un membre",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à avertir", raison="Raison du warn")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    data = load_data()
    user_id = str(membre.id)

    data["warnings"].setdefault(user_id, [])

    data["warnings"][user_id].append({
        "moderateur": interaction.user.id,
        "raison": raison
    })

    save_data(data)

    await interaction.response.send_message(
        f"⚠️ {membre.mention} a reçu un avertissement.\n📄 Raison : {raison}",
        ephemeral=True
    )


@client.tree.command(
    name="warnings",
    description="Affiche les avertissements d'un membre",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre à vérifier")
@app_commands.checks.has_permissions(manage_messages=True)
async def warnings(interaction: discord.Interaction, membre: discord.Member):
    data = load_data()
    warns = data["warnings"].get(str(membre.id), [])

    if not warns:
        await interaction.response.send_message(
            f"✅ {membre.mention} n'a aucun avertissement.",
            ephemeral=True
        )
        return

    description = ""

    for index, warn_data in enumerate(warns, start=1):
        mod_id = warn_data["moderateur"]
        raison = warn_data["raison"]
        description += f"**{index}.** Modérateur : <@{mod_id}>\nRaison : {raison}\n\n"

    embed = discord.Embed(
        title=f"⚠️ Avertissements de {membre}",
        description=description,
        color=discord.Color.yellow()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(
    name="clear-warns",
    description="Supprime tous les avertissements d'un membre",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(membre="Membre dont les warns doivent être supprimés")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_warns(interaction: discord.Interaction, membre: discord.Member):
    data = load_data()
    user_id = str(membre.id)

    if user_id in data["warnings"]:
        del data["warnings"][user_id]
        save_data(data)

    await interaction.response.send_message(
        f"✅ Tous les avertissements de {membre.mention} ont été supprimés.",
        ephemeral=True
    )


@client.tree.command(
    name="giveaway-start",
    description="Lance un giveaway",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    salon="Salon où envoyer le giveaway",
    durée="Durée : 10m, 1h, 1d",
    gagnants="Nombre de gagnants",
    récompense="Récompense"
)
@app_commands.checks.has_role(GIVEAWAY_ROLE_ID)
async def giveaway_start(
    interaction: discord.Interaction,
    salon: discord.TextChannel,
    durée: str,
    gagnants: int,
    récompense: str
):
    await interaction.response.defer(ephemeral=True)

    seconds = parse_duration(durée)

    if seconds is None:
        await interaction.followup.send(
            "❌ Durée invalide. Exemple : `10m`, `1h`, `1d`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"🎁 **Récompense :** {récompense}\n"
            f"🏆 **Gagnant(s) :** {gagnants}\n"
            f"⏱️ **Durée :** {durée}\n\n"
            f"Réagis avec 🎉 pour participer !"
        ),
        color=discord.Color.gold()
    )

    giveaway_message = await salon.send(embed=embed)
    await giveaway_message.add_reaction("🎉")

    await interaction.followup.send(
        f"✅ Giveaway lancé dans {salon.mention}.",
        ephemeral=True
    )

    await asyncio.sleep(seconds)

    giveaway_message = await salon.fetch_message(giveaway_message.id)
    reaction = discord.utils.get(giveaway_message.reactions, emoji="🎉")

    if not reaction:
        await salon.send("❌ Giveaway terminé, aucun participant.")
        return

    participants = []

    async for user in reaction.users():
        if not user.bot:
            participants.append(user)

    if not participants:
        await salon.send("❌ Giveaway terminé, aucun participant valide.")
        return

    winners = random.sample(participants, min(gagnants, len(participants)))
    winners_mentions = ", ".join(winner.mention for winner in winners)

    await salon.send(
        f"🎉 Félicitations {winners_mentions} ! Vous avez gagné **{récompense}** !"
    )


@client.tree.command(
    name="giveaway-reroll",
    description="Relance un tirage sur un giveaway",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(message_id="ID du message giveaway", gagnants="Nombre de nouveaux gagnants")
@app_commands.checks.has_role(GIVEAWAY_ROLE_ID)
async def giveaway_reroll(interaction: discord.Interaction, message_id: str, gagnants: int = 1):
    await interaction.response.defer(ephemeral=True)

    try:
        giveaway_message = await interaction.channel.fetch_message(int(message_id))
    except Exception:
        await interaction.followup.send(
            "❌ Message introuvable dans ce salon.",
            ephemeral=True
        )
        return

    reaction = discord.utils.get(giveaway_message.reactions, emoji="🎉")

    if not reaction:
        await interaction.followup.send(
            "❌ Aucun participant trouvé.",
            ephemeral=True
        )
        return

    participants = []

    async for user in reaction.users():
        if not user.bot:
            participants.append(user)

    if not participants:
        await interaction.followup.send(
            "❌ Aucun participant valide.",
            ephemeral=True
        )
        return

    winners = random.sample(participants, min(gagnants, len(participants)))
    winners_mentions = ", ".join(winner.mention for winner in winners)

    await interaction.followup.send(
        f"🎉 Nouveau gagnant : {winners_mentions}",
        ephemeral=False
    )


@client.tree.command(
    name="giveaway-end",
    description="Termine un giveaway immédiatement",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    message_id="ID du message giveaway",
    récompense="Récompense du giveaway",
    gagnants="Nombre de gagnants"
)
@app_commands.checks.has_role(GIVEAWAY_ROLE_ID)
async def giveaway_end(
    interaction: discord.Interaction,
    message_id: str,
    récompense: str,
    gagnants: int = 1
):
    await interaction.response.defer(ephemeral=True)

    try:
        giveaway_message = await interaction.channel.fetch_message(int(message_id))
    except Exception:
        await interaction.followup.send(
            "❌ Message introuvable dans ce salon.",
            ephemeral=True
        )
        return

    reaction = discord.utils.get(giveaway_message.reactions, emoji="🎉")

    if not reaction:
        await interaction.followup.send(
            "❌ Aucun participant trouvé.",
            ephemeral=True
        )
        return

    participants = []

    async for user in reaction.users():
        if not user.bot:
            participants.append(user)

    if not participants:
        await interaction.followup.send(
            "❌ Aucun participant valide.",
            ephemeral=True
        )
        return

    winners = random.sample(participants, min(gagnants, len(participants)))
    winners_mentions = ", ".join(winner.mention for winner in winners)

    await interaction.followup.send(
        f"✅ Giveaway terminé. Gagnant(s) : {winners_mentions}",
        ephemeral=False
    )


@logs_channel.error
@clear.error
@kick.error
@ban.error
@mute.error
@unmute.error
@warn.error
@warnings.error
@clear_warns.error
@giveaway_start.error
@giveaway_reroll.error
@giveaway_end.error
@classement.error
async def command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingRole):
        message_text = "❌ Tu n'as pas le rôle requis pour utiliser cette commande."
    elif isinstance(error, app_commands.MissingPermissions):
        message_text = "❌ Tu n'as pas la permission d'utiliser cette commande."
    else:
        message_text = "❌ Une erreur est survenue."

    if interaction.response.is_done():
        await interaction.followup.send(message_text, ephemeral=True)
    else:
        await interaction.response.send_message(message_text, ephemeral=True)


if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN manquant dans le .env")

client.run(TOKEN)
