import discord
import discord.ext
import io
import nest_asyncio
import random
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from os import getenv
from typing import Any
from winston import WinstonDraft
from winston import Players

load_dotenv()
token = getenv("TOKEN")
dev_guild_id = getenv("GUILD_ID")
nest_asyncio.apply()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# region Bot Variables
bot.draft = WinstonDraft()
bot.player_one_member = None
bot.player_two_member = None
bot.current_player_member = None
bot.draft_file = getenv("CUBE_FILE_PATH")
bot.new_thread_name = "A Grand Campaign"
bot.new_thread = None
bot.game_quotes = {
    "MissingPlayerOne": 
				["Hold your horses! A battle needs two sides, unless of course one intends to outwit themselves."
				],
    "MissingPlayerTwo": 
				["A duel requires two participants! Shall we put out a call for a worthy opponent?"
				],
    "Deploy": 
				["A most excellent proposition, old bean! A battle of wits, a clash of minds, a contest of strategic brilliance.",
                "we shall see who emerges victorious from this grand duel."
				],
    "Start": 
				["The pieces are set, the stage is prepared, and the battle commences!"
				],
    "CardListInvalid": 
				["A perplexing mystery! These cards have vanished like Rommel's troops in the desert."
				],
    "CardListLoaded": 
				["Splendid! Our unconventional weaponry is in place. Let us surprise the enemy!"
				],
    "PlayerOneSet": 
				["Ah, our first contender steps into the arena! A bold spirit, I trust.",
                "A worthy challenger steps forward! Splendid!"
				],
    "PlayerTwoSet": 
				["And now, the challenger emerges! The stage is set for a battle of intellects.",
                "To our new challenger, I say this: Bring forth your finest strategies, your most cunning tactics, and your boldest maneuvers."
				],
    "PlayerOneDuplicate": 
				["My good fellow, we already have a Player One. Organization is key to victory!"
				],
    "PlayerTwoDuplicate": 
				["No need to recruit the same soldier twice! Let's maintain order in the ranks."
				],
    "NonParticipantAction": 
				["Ah, a curious observer! Fear not, you will see battle yet!"
				],
    "PlayerPullsFile": 
				["A survey of your forces - may they serve you well!"
				],
    "GameStateTitle": 
				["Theatre of War"
				],
    "TakePile": ["The spoils of strategy are claimed!",
                "A bold move! Let us see what fortune it brings.",
                "A decisive hand plucks its reward!"
                ],
    "PassPile": 
				["A shrewd assessment. Perhaps a greater prize lies ahead.",
                "A classic choice, but one that I shall meet with equal resolve.",
                "I must admit, you've piqued my curiosity. I shall tread carefully."
				],
    "GameInProgress":
                ["My dear fellow, a new challenger must wait their turn! We are in the midst of a grand battle here, a clash of intellect and strategy!"                
                ],
}

# endregion

# region Events

@bot.event
async def on_ready():
    
    print(f"User: {bot.user} (ID: {bot.user.id})")
    bot.tree.copy_global_to(guild=discord.Object(id=dev_guild_id))
    await bot.tree.sync(guild=discord.Object(id=dev_guild_id))
    print(f"Synced and ready.")


# endregion

# region Commands

@bot.tree.command(name="close")
async def shutdown(interaction: discord.Interaction):

    if bot.new_thread:
        await bot.new_thread.delete()
    
    await interaction.response.send_message(content='Stopped', ephemeral=True)
    await bot.close()

@bot.tree.command(name="clear")
async def clean_up(interaction: discord.Interaction):
    for thread in interaction.channel.threads:
        if thread.owner_id == bot.user.id:
            await thread.delete()

    await interaction.response.send_message(content="Clear", delete_after=0.5, ephemeral=True)

@bot.tree.command(name="cache")
async def view_cache(interaction: discord.Interaction):
    cache = bot.draft.card_cache  
    await interaction.response.send_message(content=cache, ephemeral=True)  

@bot.tree.command(name="deploy")
async def deploy(interaction: discord.Interaction):
    if bot.new_thread:
        await interaction.response.send_message(content=get_quote("GameInProgress"), delete_after=2)
        return

    await interaction.response.send_message(content="Deploy", delete_after=0.5, ephemeral=True)
    bot.new_thread = await interaction.channel.create_thread(name=bot.new_thread_name, type=discord.ChannelType.public_thread)

    await bot.new_thread.send(
        get_quote("Deploy"),
        view=StartButtons(ctx=bot.new_thread, timeout=None),
    )
    bot.player_one_member = None
    bot.player_two_member = None

async def new_game(ctx):

    if not bot.player_one_member:
        await ctx.send(get_quote("MissingPlayerOne"))
        return

    if not bot.player_two_member:
        await ctx.send(get_quote("MissingPlayerTwo"))
        return

    bot.draft.new_game(bot.draft_file)

    await update_player(ctx=ctx)
    bot.last_action_message = (
        get_quote("Start")
    )
    await ctx.send(embed=DraftStatusEmbed(), view=ActionButtons(ctx=ctx, timeout=None))


# endregion

#region Private Functions

def get_quote(decode):
    return random.choice(bot.game_quotes[decode])

async def send_dm(member: discord.Member, *, message):
    channel = await member.create_dm()
    await channel.send(message)


async def respond_with_dm(ctx, message):
    member = await ctx.guild.fetch_member(ctx.author.id)
    await send_dm(member=member, message=message)


async def send_pulls_file(interaction, file_name):

    # write to file

    if interaction.user.id == bot.player_one_member.id:
        content = await bot.draft.displayPlayerPulls(1, unformatted_list=True)
    elif interaction.user.id == bot.player_two_member.id:
        content = await bot.draft.displayPlayerPulls(2, unformatted_list=True)

    file = io.StringIO(content)

    # send file to Discord in message
    await interaction.response.send_message(
        get_quote("PlayerPullsFile"),
        file=discord.File(file, file_name),
        ephemeral=True,
    )


async def update_player(ctx):
    member = None

    if bot.draft.current_player.value == 1:
        member = bot.player_one_member
    elif bot.draft.current_player.value == 2:
        member = bot.player_two_member
    else:
        await ctx.send(
            f"Failed to determine player. Current player set to: {bot.draft.current_player}"
        )

    # update current player member
    bot.current_player_member = member


async def take_pile(ctx, interaction):
    if not bot.draft.in_progress:
        await interaction.response.send_message(
            "No draft in progress.",
            ephemeral=True,
        )
        return False

    if bot.current_player_member.id != interaction.user.id:
        await interaction.response.send_message(get_quote("NonParticipantAction"), ephemeral=True)
        return False
    bot.draft.takePile()
    await update_player(ctx=ctx)

    return True


async def pass_pile(ctx, interaction):
    if not bot.draft.in_progress:
        await interaction.response.send_message(
            "No draft in progress.",
            ephemeral=True,
        )
        return False

    if bot.current_player_member.id != interaction.user.id:
        await interaction.response.send_message(get_quote("NonParticipantAction"), ephemeral=True)
        return False
    bot.draft.passPile()
    await update_player(ctx=ctx)

    return True

#endregion

# region Modals


class FileModal(discord.ui.Modal, title='Load Custom Cube List'):

    file_contents = discord.ui.TextInput(
        label="Card List", style=discord.TextStyle.long, required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:

        #TODO: add validation for input with draft card db
        valid_list, failed_cards = True, []

        if not valid_list:
            await interaction.response.send_message(get_quote("CardListInvalid") + f"\n\n{failed_cards}", ephemeral=True)
        else:
            with open("draft_files/test.txt", "w") as file:
                file.writelines(self.file_contents.value)

            bot.draft_file = "draft_files/test.txt"
            await interaction.response.send_message(get_quote("CardListLoaded"))


# endregion

# region Buttons
class StartButtons(discord.ui.View):
    def __init__(self, ctx, *, timeout=None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    @discord.ui.button(label='Load Custom List', style=discord.ButtonStyle.gray)
    async def send_file_load_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FileModal(timeout=None))

    @discord.ui.button(label="Player One", style=discord.ButtonStyle.gray)
    async def set_player_one(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not bot.player_one_member:
            bot.player_one_member = await self.ctx.guild.fetch_member(
                interaction.user.id
            )
            button.label = f"{interaction.user.display_name}"
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(
                content=get_quote("PlayerOneSet"), view=self
            )
        else:
            await interaction.response.send_message(
                get_quote("PlayerOneDuplicate"), ephemeral=True
            )

        if bot.player_one_member and bot.player_two_member:
            await new_game(self.ctx)

    @discord.ui.button(label="Player Two", style=discord.ButtonStyle.gray)
    async def set_player_two(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not bot.player_two_member:
            bot.player_two_member = await self.ctx.guild.fetch_member(
                interaction.user.id
            )
            button.label = f"{interaction.user.display_name}"
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(
                content=get_quote("PlayerTwoSet"), view=self
            )
        else:
            await interaction.response.send_message(
                get_quote("PlayerTwoDuplicate"), ephemeral=True
            )

        if bot.player_one_member and bot.player_two_member:
            await new_game(self.ctx)

class ActionButtons(discord.ui.View):
    def __init__(self, ctx, *, timeout=None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    @discord.ui.button(label="View Pulls", style=discord.ButtonStyle.gray)
    async def view_pulls(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not bot.draft.in_progress():
            if interaction.user.id == bot.player_one_member.id:
                # send player one pulls file
                await send_pulls_file(
                    interaction=interaction, file_name="player_one_pulls.txt"
                )
                return
            elif interaction.user.id == bot.player_two_member.id:
                # send player two pulls list
                await send_pulls_file(
                    interaction=interaction, file_name="player_two_pulls.txt"
                )
                return

        message = ""
        if interaction.user.id == bot.player_one_member.id:
            message = await bot.draft.displayPlayerPulls(1)
        elif interaction.user.id == bot.player_two_member.id:
            message = await bot.draft.displayPlayerPulls(2)
        else:
            message = get_quote("NonParticipantAction")

        if len(message) > 2000:
            temp = ""
            for line in message.splitlines():
                if len(line) + len(temp) <= 2000:
                    temp += f"{line}\n"
                else:
                    await interaction.response.send_message(
                        temp, ephemeral=True, delete_after=10
                    )
                    temp = ""
        else:
            await interaction.response.send_message(
                message, ephemeral=True, delete_after=10
            )

    @discord.ui.button(label="View Pile", style=discord.ButtonStyle.gray)
    async def view_pile_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if bot.current_player_member.id == interaction.user.id:
            message = await bot.draft.displayPickPiles()
            await interaction.response.send_message(
                message, ephemeral=True, delete_after=10
            )

    @discord.ui.button(label="Take", style=discord.ButtonStyle.gray)
    async def take_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if await take_pile(self.ctx, interaction):

            bot.last_action_message = get_quote("TakePile")
            await interaction.response.edit_message(embed=DraftStatusEmbed(), view=self)

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.gray)
    async def pass_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if await pass_pile(self.ctx, interaction):

            bot.last_action_message = get_quote("PassPile")
            await interaction.response.edit_message(embed=DraftStatusEmbed(), view=self)

# endregion Buttons

#region Embeds

class DraftStatusEmbed(discord.Embed):
    def __init__(
        self,
        *,
        colour: int | discord.Colour | None = None,
        color: int | discord.Colour | None = None,
        title: Any | None = None,
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None,
    ):
        super().__init__(
            colour=colour,
            color=discord.Colour.brand_green(),
            title=("-"*25) + get_quote("GameStateTitle") + ("-"*25),
            type="rich",
            url=url,
            description=f"{bot.last_action_message}",
            timestamp=timestamp,
        )

        current_pile = bot.draft.pick_piles.current_pile

        draft_pile_count = bot.draft.draft_pile.cardsRemaining()
        pile_one_count = len(bot.draft.pick_piles.pile_one)
        pile_two_count = len(bot.draft.pick_piles.pile_two)
        pile_three_count = len(bot.draft.pick_piles.pile_three)

        player_one_card_count = len(bot.draft.player_pulls[Players.PLAYER_ONE])
        player_two_card_count = len(bot.draft.player_pulls[Players.PLAYER_TWO])

        self.add_field(
            name="Current player: ",
            value=f"{bot.current_player_member.mention}",
            inline=False,
        )
        self.add_field(name=":books:", value=draft_pile_count, inline=False)
        self.add_field(
            name=":open_book:" if current_pile.value == 1 else ":blue_book:",
            value=pile_one_count,
            inline=True,
        )
        self.add_field(
            name=":open_book:" if current_pile.value == 2 else ":blue_book:",
            value=pile_two_count,
            inline=True,
        )
        self.add_field(
            name=":open_book:" if current_pile.value == 3 else ":blue_book:",
            value=pile_three_count,
            inline=True,
        )
        self.add_field(
            name="Player One Pulls", value=player_one_card_count, inline=False
        )
        self.add_field(
            name="Player Two Pulls", value=player_two_card_count, inline=False
        )

#endregion

bot.run(token=token)
