# Epidemic modules
from decks import Card, Deck, DrawDeck
from stats import Stats
import utility

# Other modules
from copy import deepcopy
import yaml


CARDS_FILE = 'data/cards.yml'
# TODO add epidemic counter and identifier

class Game:
    def __init__(self):
        self.games = self.get_all_games()
        self.deck = None
        self.stats = None

    def initialise(self, game):
        """Prepare the initial state for the game. Initialise all decks.
        This is run once at the start of every game."""

        # Create a list with the Draw Deck and the 2 other empty decks
        game_decks = [self.initialise_draw_deck(game),
                      Deck('discard'),
                      Deck('exclude')]

        # Build the decks dictionary so we can get a Deck object by its name
        self.deck = {deck.name: deck for deck in game_decks}

        # Get a Stats object for calculating draw probabilities
        self.stats = Stats(self.deck)

    def initialise_draw_deck(self, game):
        d = DrawDeck('draw')
        d.add(deepcopy(self.games[game]))  # games list shouldn't mutate
        return d

    @staticmethod
    def draw_card(from_deck, to_deck, card):
        if not from_deck == to_deck:
            from_deck.move(card, to_deck)

    def epidemic(self, card):
        """Draw a card from the bottom of the Draw Deck, discard it
        and shuffle the discard pile back onto the top of the Draw Deck."""
        new_card = self.deck['draw'].get_card_by_name(card)
        self.deck['draw'].remove_from_bottom(new_card)
        self.deck['discard'].add(new_card)

        # Create new card pool
        new_cards = Deck('epidemic')
        for card in self.deck['discard'].cards.copy():
            new_cards.add(card)
        self.deck['draw'].add(new_cards)

        # Clear the discard pile
        self.deck['discard'].clear()

    def get_all_games(self):
        # Initialize the initial deck from the card list in cards.yml
        game = {}
        data = self.read_data_file()
        try:
            for game_title in data.keys():
                game[game_title] = self.create_deck(game_title, data)
        except ValueError:
            raise  # Raise the error again to stop execution

        return game

    @staticmethod
    def create_deck(game_title, data):
        deck = Deck(game_title)
        for item in data[game_title]:
            if item['color'] not in Card.valid_colors:
                raise ValueError(f"Invalid color '{item['color']}' in "
                                 f"'{game_title} : {item['name']}'")
            else:
                card = Card(item['name'], item['color'])
                for i in range(item['count']):
                    deck.add(card)
        return deck

    @staticmethod
    def read_data_file():
        file = utility.get_path(CARDS_FILE)
        try:
            with open(file, encoding='utf-8') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError as e:
            print(f'Missing or damaged cards.yml configuration file\n({e})')
        else:
            return data
