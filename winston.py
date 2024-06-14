import random
import enum
import time
import concurrent.futures
import scrython
import scrython.cards


class Players(enum.Enum):
    PLAYER_ONE = 1
    PLAYER_TWO = 2


class DraftPile:
    def __init__(self, file_path, card_limit=90) -> None:
        self.draft_pile = (
            self.loadCube() if file_path is None else self.loadCube(file_path)
        )

        self.shuffle()
        self.enforceCardLimit(card_limit)
        
    
    def enforceCardLimit(self, max_cards = 60):
        if len(self.draft_pile) > max_cards:
            self.draft_pile = self.draft_pile[:max_cards]
            pass    

    def getNextCard(self):
        if self.isEmpty():
            print("Draft pile is empty")
            return None

        return self.draft_pile.pop()

    def isEmpty(self):
        return not self.draft_pile

    def cardsRemaining(self):
        return len(self.draft_pile)

    def loadCube(self, file_path):

        cube = []

        with open(file_path) as infile:

            for line in infile:

                if not line.strip():
                    break

                values = line.split(maxsplit=1)
                quantity = 0
                name = ""
                if not values[0].isnumeric():
                    quantity = 1
                    name = ' '.join(values).strip()
                else:
                    quantity = int(values[0])
                    name = values[1].strip()

                for i in range(quantity):
                    cube.append(name)

        return cube

    def shuffle(self):
        random.shuffle(self.draft_pile)

    def sample(self, size=5):
        return self.draft_pile[:size] if size > 0 else self.draft_pile[: size - 1 : -1]


class PickPiles:

    class Piles(enum.Enum):
        PILE_ONE = 1
        PILE_TWO = 2
        PILE_THREE = 3

    def __init__(self, draft_pile) -> None:
        self.draft_pile = draft_pile

        self.pile_one = [draft_pile.getNextCard()]
        self.pile_two = [draft_pile.getNextCard()]
        self.pile_three = [draft_pile.getNextCard()]

        self.pick_piles = {
            self.Piles.PILE_ONE: self.pile_one,
            self.Piles.PILE_TWO: self.pile_two,
            self.Piles.PILE_THREE: self.pile_three,
        }

        self.current_pile = self.Piles.PILE_ONE

    def getCurrentPile(self):

        if self.current_pile not in self.pick_piles.keys():
            raise Exception(f"Current pile is invalid: {self.current_pile}\n")

        return self.pick_piles[self.current_pile]

    def moveToNextPile(self):
        if self.current_pile == self.Piles.PILE_ONE:
            self.current_pile = self.Piles.PILE_TWO
        elif self.current_pile == self.Piles.PILE_TWO:
            self.current_pile = self.Piles.PILE_THREE
        elif self.current_pile == self.Piles.PILE_THREE:
            self.current_pile = self.Piles.PILE_ONE
        else:
            IndexError(f"Current pile is invalid: {self.current_pile}")

    def setToFirstPile(self):
        self.current_pile = self.Piles.PILE_ONE

    def addCardToCurrentPile(self):
        next_card = self.draft_pile.getNextCard()
        if next_card:
            self.getCurrentPile().append(next_card)

    def clearCurrentPile(self):
        self.getCurrentPile().clear()

    def isLastPile(self):
        return self.current_pile == self.Piles.PILE_THREE
    
    def allPilesEmpty(self):
        for pile in self.pick_piles.values():
            if pile:
                return False

        return True


class WinstonDraft:
    def __init__(self) -> None:

        self.thread_pool = concurrent.futures.ThreadPoolExecutor()   
        self.card_thread = {}     
        self.card_cache = {}

    def in_progress(self):
        return not (self.draft_pile.isEmpty() and self.pick_piles.allPilesEmpty())

    def new_game(self, card_list_file_path):
        self.chooseStartingPlayer()
        self.draft_pile = DraftPile(card_list_file_path)
        self.pick_piles = PickPiles(self.draft_pile)
        self.player_pulls = {Players.PLAYER_ONE: [], Players.PLAYER_TWO: []}

    def chooseStartingPlayer(self):
        self.starting_player = random.choice([Players.PLAYER_ONE, Players.PLAYER_TWO])
        self.current_player = self.starting_player

    def switchPlayer(self):
        if self.current_player == Players.PLAYER_ONE:
            self.current_player = Players.PLAYER_TWO

        elif self.current_player == Players.PLAYER_TWO:
            self.current_player = Players.PLAYER_ONE
        else:
            raise Exception(f"Current player is invalid: {self.current_player.name}\n")

        self.pick_piles.setToFirstPile()

    def takePile(self):

        print(f"{self.current_player} takes {self.pick_piles.current_pile}.")

        selected_pile = self.pick_piles.getCurrentPile().copy()

        if not self.pick_piles.getCurrentPile():
            if self.pick_piles.isLastPile():
                print(f"End of draft.")
                self.switchPlayer()
                return
            else:
                self.pick_piles.moveToNextPile()
                self.takePile()

        self.pick_piles.clearCurrentPile()
        next_card = self.getNextCard()
        if next_card:
            self.pick_piles.getCurrentPile().append(next_card)

        self.player_pulls[self.current_player] += selected_pile
        self.switchPlayer()

    def passPile(self):

        next_card = self.getNextCard()
        if next_card:
            self.pick_piles.getCurrentPile().append(next_card)

        if self.pick_piles.isLastPile():
            self.pick_piles.setToFirstPile()
            if self.draft_pile.isEmpty():                
                return
            else:
                next_card = self.getNextCard()
            if next_card:
                self.player_pulls[self.current_player].append(next_card)            

            self.switchPlayer()
        else:
            self.pick_piles.moveToNextPile()

    def getNextCard(self):
        next_card = self.draft_pile.getNextCard()
        
        #Cache card in background for quicker access later
        self.card_thread[next_card] = self.thread_pool.submit(self.getScryfallCard, next_card)
        
        return next_card

    async def displayPickPiles(self, incl_all_piles=False):

        results = "\n"
        if incl_all_piles or self.pick_piles.current_pile == PickPiles.Piles.PILE_ONE:
            results += f"\n# Pile 1: {await self.getPileInfo(self.pick_piles.pile_one)}"

        if incl_all_piles or self.pick_piles.current_pile == PickPiles.Piles.PILE_TWO:
            results += f"\n# Pile 2: {await self.getPileInfo(self.pick_piles.pile_two)}"

        if incl_all_piles or self.pick_piles.current_pile == PickPiles.Piles.PILE_THREE:
            results += f"\n# Pile 3: {await self.getPileInfo(self.pick_piles.pile_three)}"

        return results

    async def displayPlayerPulls(self, player_number=None, incl_both_players=False, unformatted_list=False):
        results = "\n# Current Pulls:"
        player_one_card_count = len(self.player_pulls[Players.PLAYER_ONE])
        player_two_card_count = len(self.player_pulls[Players.PLAYER_TWO])

        if not player_number:
            player_number = self.current_player
        elif player_number == 1:
            player_number = Players.PLAYER_ONE
        elif player_number == 2:
            player_number = Players.PLAYER_TWO

        if incl_both_players and not unformatted_list:
            results += f"\n## PLAYER_ONE (x{player_one_card_count}): \n\t{self.player_pulls[Players.PLAYER_ONE]}\n"
            results += f"\n## PLAYER_TWO (x{player_two_card_count}): \n\t{self.player_pulls[Players.PLAYER_TWO]}\n"
        elif not unformatted_list:
            results += await self.getPileInfo(self.player_pulls[player_number])
        elif incl_both_players:
            # Unimplmenented
            pass
        else:
            results = ''
            counts = {}
            for card in self.player_pulls[player_number]:
                counts[card] = counts.get(card, 0) + 1

            results = '\n'.join(f'{count} {card_name}' for card_name, count in counts.items())

        return results

    def displayDraftPile(self, sample_size=5):
        results = ""
        results += f"Cube size: {len(self.draft_pile.draft_pile)}\n"

        if sample_size > 0:
            results += f"Top {sample_size} cards of draft pile: \n\t{self.draft_pile.sample(sample_size)}\n"
        else:
            results += f"{self.draft_pile.draft_pile}\n"

        return results

    def printInfo(
        self, 
        incl_cube_info=False, 
        incl_all_piles=False, 
        incl_both_players=False
    ):
        results = ""
        sample_size = 5

        results += f"Current player: {self.current_player.name}\n"

        if incl_cube_info:
            results += self.displayDraftPile(sample_size=sample_size)

        self.displayPickPiles(incl_all_piles=incl_all_piles)

        self.displayPlayerPulls(incl_both_players=incl_both_players)

        print(results)

    async def getCardInfo(self, card_name):        
        if card_name not in self.card_cache:

            if card_name in self.card_thread:
                self.card_cache[card_name] = self.card_thread[card_name].result()
            else:
                self.card_cache[card_name] = self.getScryfallCard(card_name)
            
        card_info = self.card_cache[card_name].scryfallJson if self.card_cache[card_name] else None

        if card_info:
            return f"[{card_name}](<{card_info['scryfall_uri']}>)"
        
        return f"[{card_name}]<URL Not Found>"

    def getScryfallCard(self, card_name):
        try:
            card = scrython.cards.Named(exact=card_name)
        except:
            card =  None
        finally:
            time.sleep(0.1)
            return card


    async def getPileInfo(self, card_pile):
        results = ""
        for card in card_pile:
            if card is not None:
                results += "\n- " + await self.getCardInfo(card)
        return results


async def main():

    draft = WinstonDraft()
    draft.new_game("draft_files/cube.txt")

    # Play Random Game
    while (
        any(draft.pick_piles.pile_one)
        or any(draft.pick_piles.pile_two)
        or any(draft.pick_piles.pile_three)
    ):

        player_action = random.choice([draft.passPile, draft.takePile])
        player_action()
        draft.printInfo(incl_all_piles=True, incl_both_players=True)

    # End Random Game

    message = await draft.displayPickPiles(incl_all_piles=True)
    message += await draft.displayPlayerPulls(incl_both_players=True)
    print(message)

    print(await draft.displayPlayerPulls(unformatted_list=True))


if __name__ == "__main__":
    main()
