# Required permissions:
# - Manage Messages
# - Manage Roles
# - Moderate Members
# - Read Message History
# - View Channels
# - Use Slash Commands (required to create and register commands in guilds)
# Invite link:
# https://discord.com/oauth2/authorize?client_id=1400424137100365865&permissions=1101927621632&scope=bot+applications.commands

import discord
from discord import app_commands as discord_command
import yaml
import os
import asyncio
import dotenv
from datetime import datetime, timedelta, timezone
import re

dotenv.load_dotenv()

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

MODDELMSG_MAX_HOURS = config.get("moddelmsg", {}).get("max_hours", 24)
MODDELMSG_DEFAULT_HOURS = config.get("moddelmsg", {}).get("default_hours", 1)
MODDELMSG_DEFAULT_TIMEOUT_HOURS = config.get("moddelmsg", {}).get(
    "default_timeout_hours", 0
)
MODDELMSG_TIMEOUT_REMOVE_ROLEID = config.get("moddelmsg", {}).get(
    "timeout_remove_roleid", 0
)
MODDELMSG_NOTIFY_CHANNELID = config.get("moddelmsg", {}).get("notify_channelid", 0)
MODDELMSG_NOTIFY_USER_ID = config.get("moddelmsg", {}).get("notify_user_id", 0)
MODDELMSG_QUARANTINE_ROLEID = config.get("moddelmsg", {}).get("quarantine_roleid", 0)
MODDELMSG_QUARANTINE_CHANNELID = config.get("moddelmsg", {}).get(
    "quarantine_channelid", 0
)

FORBIDDEN_REGEXES = [
    re.compile(pattern, flags=re.IGNORECASE | re.MULTILINE)
    for pattern in config.get("moddelmsg", {}).get("forbidden_regexes", [])
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
client = discord.Client(intents=intents)
tree = discord_command.CommandTree(client)


async def setup_guild(guild: discord.Guild):
    tree.copy_global_to(guild=guild)
    commands = await tree.sync(guild=guild)
    print(f"Synced {len(commands)} commands: {', '.join([c.name for c in commands])}")


async def quarantine_user(user: discord.Member, *, reason: str | None = None):
    try:
        role_to_remove = user.guild.get_role(MODDELMSG_TIMEOUT_REMOVE_ROLEID)
        if role_to_remove and role_to_remove in user.roles:
            await user.remove_roles(role_to_remove, reason="User was quarantined")
    except discord.Forbidden:
        print("Error: Failed to remove a role during quarantine: Missing permissions")
    except Exception as e:
        print(f"Error: Failed to remove a role during quarantine: {e}")
    try:
        role_to_give = user.guild.get_role(MODDELMSG_QUARANTINE_ROLEID)
        if role_to_give and role_to_give not in user.roles:
            await user.add_roles(
                role_to_give, reason="User was quarantined" if not reason else reason
            )
    except discord.Forbidden:
        print("Error: Failed to add quarantine role: Missing permissions")
    except Exception as e:
        print(f"Error: Failed to add quarantine role: {e}")


async def unquarantine_user(
    user: discord.Member, *, reason: str | None = None
) -> tuple[bool, bool]:
    success_count = 0
    had_role = False
    try:
        role_to_remove = user.guild.get_role(MODDELMSG_QUARANTINE_ROLEID)
        if role_to_remove and role_to_remove in user.roles:
            had_role = True
            await user.remove_roles(
                role_to_remove,
                reason="User was unquarantined" if not reason else reason,
            )
            success_count += 1
    except discord.Forbidden:
        print("Error: Failed to remove quarantine role: Missing permissions")
    except Exception as e:
        print(f"Error: Failed to remove quarantine role: {e}")
    try:
        role_to_give = user.guild.get_role(MODDELMSG_TIMEOUT_REMOVE_ROLEID)
        if role_to_give and role_to_give not in user.roles:
            await user.add_roles(role_to_give, reason="User was unquarantined")
            success_count += 1
    except discord.Forbidden:
        print("Error: Failed to add a role during unquarantine: Missing permissions")
    except Exception as e:
        print(f"Error: Failed to add a role during unquarantine: {e}")
    return had_role, success_count == 2


@client.event
async def on_ready():
    for guild in client.guilds:
        await setup_guild(guild)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Bypass if > or = bot's role (for mods)
    if isinstance(message.author, discord.Member):
        bot_member = message.guild.me
        if message.author.top_role >= bot_member.top_role:
            return

    for pattern in FORBIDDEN_REGEXES:
        if pattern.search(message.content):
            # Delete the message
            try:
                await message.delete()
                print("[AUTOMOD] Message deleted.")
            except Exception as e:
                print(f"[AUTOMOD] Failed to delete message: {e}")

            # Notify in the log channel
            try:
                notify_channel = message.guild.get_channel(MODDELMSG_NOTIFY_CHANNELID)
                if notify_channel:
                    embed = discord.Embed(
                        title="🚨 AUTOMOD: Forbidden Content Deleted",
                        description=(
                            f"**Author :** {message.author.mention}\n"
                            f"**Channel :** {message.channel.mention}\n"
                            f"```{message.content}```"
                        ),
                        color=discord.Color.orange(),
                        timestamp=datetime.now(timezone.utc),
                    )
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await notify_channel.send(embed=embed)
                    print("[AUTOMOD] Log embed sent to notify channel.")
                else:
                    print("[AUTOMOD] Notify channel not found.")
            except Exception as e:
                print(f"[AUTOMOD] Failed to send log embed: {e}")

            # Add Quarantined role to the user
            try:
                quarantine_role = message.guild.get_role(MODDELMSG_QUARANTINE_ROLEID)
                if quarantine_role and quarantine_role not in message.author.roles:
                    await message.author.add_roles(
                        quarantine_role, reason="Automod: Forbidden content detected"
                    )
                    print("[AUTOMOD] Quarantined role added.")
                else:
                    print("[AUTOMOD] Quarantine role missing or already present.")
            except Exception as e:
                print(f"[AUTOMOD] Failed to add Quarantined role: {e}")

            await quarantine_user(
                message.author, reason="Automod: Forbidden content detected"
            )

            # DM the quarantined user
            try:
                dm_embed = discord.Embed(
                    title="🚨 You have been sanctioned",
                    description=(
                        "You have been given the **Quarantined** role because of the following message:\n"
                        f"```{message.content}```\n"
                        f"If you believe this is a mistake, you can appeal by contacting the staff in the **https://discord.com/channels/{bot_member.guild.id}/{MODDELMSG_QUARANTINE_CHANNELID}** channel."
                    ),
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc),
                )
                dm_embed.set_footer(text="Music Presence Automod")
                dm_embed.set_author(
                    name=message.guild.name,
                    icon_url=message.guild.icon.url if message.guild.icon else None,
                )
                await message.author.send(embed=dm_embed)
                print("[AUTOMOD] DM sent to user.")
            except Exception as e:
                print(f"[AUTOMOD] Could not send DM to user: {e}")

            break


@tree.command(
    name="moddelmsg",
    description="Delete recent messages by a user and optionally time them out.",
)
@discord_command.describe(
    user="User to delete messages from",
    hours="How far back to look",
    timeout_hours="How long to time out the user",
)
async def moddelmsg(
    interaction: discord.Interaction,
    user: discord.Member,
    hours: int = MODDELMSG_DEFAULT_HOURS,
    timeout_hours: int = MODDELMSG_DEFAULT_TIMEOUT_HOURS,
):
    await interaction.response.defer(ephemeral=True)

    command_user: discord.Member = interaction.user

    # Role hierarchy check
    if user.top_role >= command_user.top_role:
        return await interaction.followup.send(
            f"You do not have permission to delete messages from {user}.",
            ephemeral=True,
        )

    # Check that the user is not a bot
    if user.bot:
        return await interaction.followup.send(
            f"Cannot delete messages from a bot.", ephemeral=True
        )

    # Cap hours to MODDELMSG_MAX_HOURS
    hours_to_use = min(max(0, hours), MODDELMSG_MAX_HOURS)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_to_use)

    # Cap timeout hours
    timeout_hours = min(max(0, timeout_hours), 48)

    # Timeout the user (if requested)
    if timeout_hours > 0:
        try:
            await user.timeout(
                datetime.now(timezone.utc) + timedelta(hours=timeout_hours),
                reason=f"Timed out by {command_user.name}",
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "Failed to timeout user. Missing permissions.", ephemeral=True
            )
        await quarantine_user(user)

    deleted_messages = []
    notify_channel = interaction.guild.get_channel(MODDELMSG_NOTIFY_CHANNELID)

    # Delete specified messages in all of the guild's channels
    try:
        for channel in interaction.guild.text_channels:
            try:
                async for message in channel.history(limit=100, after=cutoff_time):
                    if message.author.id != user.id:
                        continue
                    if message.type == discord.MessageType.new_member:
                        continue  # do not delete welcome messages

                    content = message.content.strip()
                    attachment_text = ""
                    for attachment in [a.url for a in message.attachments]:
                        if attachment_text:
                            attachment_text += " "
                        attachment_text += f"[attachment: {attachment}]"
                    log_content = content[:200] or "*empty*"
                    if attachment_text:
                        if log_content:
                            log_content += " "
                        log_content += attachment_text

                    deleted_messages.append((channel.name, log_content))

                    await message.delete()
                    print(
                        f"Deleted message from {user} ({user.id}) in #{channel.name}: {content} {attachment_text}"
                    )
                    await asyncio.sleep(0.2)  # avoid rate limits
            except discord.Forbidden:
                continue  # skip channels the bot can't access
    except Exception as e:
        return await interaction.followup.send(
            f"Error deleting messages: {e}", ephemeral=True
        )

    log_text = (
        f"Deleted {len(deleted_messages)} message{"s" if len(deleted_messages) != 1 else ""} from {user.mention} that were sent within the last {hours_to_use} hour{"s" if hours_to_use != 1 else ""}. "
        + (
            "They have not been timed out."
            if timeout_hours == 0
            else f"They were timed out for {timeout_hours} hour{"s" if timeout_hours != 1 else ""}."
        )
    )

    await interaction.followup.send(log_text, ephemeral=True)

    if len(deleted_messages) == 0 and timeout_hours == 0:
        return

    if notify_channel:
        await notify_channel.send(
            log_text + f" Performed by {command_user.mention}.",
            allowed_mentions=discord.AllowedMentions(users=[]),
        )

    if notify_channel and deleted_messages:
        try:
            message_lines = [
                f"`#{channel}` {re.sub(r'\s+', ' ', content)}"
                for channel, content in deleted_messages
            ]
            max_chars = 4000  # limit for embed fields

            message_text = "\n".join(message_lines)
            if len(message_text) > max_chars:
                message_text = message_text[: max_chars - 20] + "... (truncated)"

            embed = discord.Embed(
                title=f"Log of deleted messages",
                description=message_text,
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"User ID: {user.id}")
            await notify_channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to send log embed: {e}")

    # Ping the user that wants to get notified
    notify_user = interaction.guild.get_member(MODDELMSG_NOTIFY_USER_ID)
    if notify_user and notify_channel:
        await notify_channel.send(f"{notify_user.mention} New moderation events.")


@tree.command(
    name="modunquarantine",
    description="Unquarantine a quarantined user.",
)
@discord_command.describe(
    user="User to unquarantine",
)
async def modunquarantine(interaction: discord.Interaction, user: discord.Member):
    if interaction.user == user:
        return await interaction.response.send_message(
            f"It's not that simple.", ephemeral=True
        )
    await interaction.response.defer(ephemeral=True)
    had_role, success = await unquarantine_user(user)
    if not had_role:
        return await interaction.followup.send(
            f"User does not have the configured quarantine role", ephemeral=True
        )
    if not success:
        return await interaction.followup.send(
            f"Something went wrong while attempting to unquarantine the user",
            ephemeral=True,
        )
    return await interaction.followup.send(
        f"Successfully unquarantined {user.mention}",
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions(users=[]),
    )


client.run(os.getenv("BOT_TOKEN"))
