#!/usr/bin/env python

"""
EPIDEMIC is designed to assist in evaluating card draw probabilities
in the board games Pandemic and Pandemic Legacy.

This is my first attempt at a working project
using the Qt framework and PySide2.

The code attempts to follow a simplified MVC pattern:
Model : Game (in game.py)
View : MainWindow (in qt.py)
Controller : App (in this file)
"""

__author__ = "Tal Zana"
__copyright__ = "Copyright 2020"
__license__ = "GPL"
__version__ = "1.0"

# TODO undo
# TODO fr, en
# TODO parse YML import for empty file or wrong colors
# TODO disable textboxes on game launch
# TODO allow cancel on app start

from PySide2.QtWidgets import QApplication
from webbrowser import open as webopen
from qt import MainWindow
from qtdialogs import DialogHelp, DialogNewGame
from game import Game

import logging
logging.basicConfig(level=logging.DEBUG)

STATS_MAX = 10
CARDPOOL_MAX = 35
TOP_CARDS = 16


class App:
    def __init__(self, view, game):
        self.game = game
        self.view = view

        self._cardpool_index = 0

        self.bind_sidebar_buttons()
        self.cb_new_game_dialog()
        pass

    @property
    def cardpool_index(self):
        return self._cardpool_index

    @cardpool_index.setter
    def cardpool_index(self, index):
        self.view.drawdeck.button[self._cardpool_index].set_active(False)
        self._cardpool_index = index
        self.view.drawdeck.button[index].set_active(True)
        self.update_cardpool()

    def bind_sidebar_buttons(self):
        new_game_button = self.view.app_buttons.button_new_game
        new_game_button.clicked.connect(self.cb_new_game_dialog)
        help_button = self.view.app_buttons.button_help
        help_button.clicked.connect(self.cb_help_dialog)
        epidemic = self.view.epidemic_menu.button
        epidemic.clicked.connect(self.cb_epidemic)

    def populate_draw(self):
        logging.debug(f'APP: populate_draw')
        self.view.deck['draw'].clear()
        deck = self.game.deck['draw']
        cards = deck.sorted()
        for card in cards:
            button = self.view.deck['draw'].add_card_button(card)
            button.clicked.connect(lambda b=button, d=deck: self.cb_draw_card(b, d))

    @staticmethod
    def last_card(deck):
        return True if deck.name == 'draw' and len(deck.top()) == 1 else False

    def cb_draw_card(self, button, from_deck):
        # Get the deck we're drawing to
        to_deck = self.get_destination()
        card = button.card

        # Ignore drawing from a deck onto itself
        if not from_deck == to_deck and not from_deck == to_deck.parent:
            logging.debug(f'Drawing {button.card.name} from {from_deck.name} to {to_deck.name}')

            is_last_card = self.last_card(from_deck)

            # Move the card and update the game state
            self.game.draw_card(from_deck, to_deck, card)

            # Remove the card from the source deck in GUI
            if from_deck.name == 'draw':
                self.cardpool_index = min(self.cardpool_index, len(self.game.deck['draw'].cards) - 1)
                if card not in from_deck.top():
                    self.remove_button_from_deck(button, from_deck)
                if is_last_card:
                    self.populate_draw()
            else:
                self.remove_button_from_deck(button, from_deck)

            # Add the card to the destination deck in GUI
            if to_deck.has_parent():  # Deck is part of the Draw Deck
                # Add the button only if it's not already displayed
                if card.name not in self.view.deck['draw'].cards:
                    self.add_button_to_deck(button, self.game.deck['draw'])
            else:
                self.add_button_to_deck(button, to_deck)
            self.update_cardpool()
            self.update_drawdeck()
            self.update_stats()
            self.update_epidemic_menu()

    def add_button_to_deck(self, button, deck):
        button = self.view.deck[deck.name].add_card_button(button.card)
        button.clicked.connect(lambda b=button, d=deck: self.cb_draw_card(b, d))

    def remove_button_from_deck(self, button, deck):
        self.view.deck[deck.name].remove_card_button(button)

    def get_destination(self):
        if self.view.destination['exclude'].isChecked():
            return self.game.deck['exclude']
        if self.view.destination['discard'].isChecked():
            return self.game.deck['discard']
        if self.view.destination['draw_top'].isChecked():
            return self.game.deck['draw']
        if self.view.destination['draw_pool'].isChecked():
            if not self.game.deck['draw'].is_empty():
                return self.game.deck['draw'].cards[-1 - self.cardpool_index]
            else:
                return self.game.deck['draw']

    def update_cardpool(self):
        text = f'Deck position: {self.cardpool_index+1}\n\n'
        if not self.game.deck['draw'].is_empty():
            d = self.game.deck['draw'].cards[-1-self.cardpool_index]
            if len(set(d)) < CARDPOOL_MAX:
                for card in sorted(set(d.cards), key=lambda x: x.name):
                    text += f'{card.name} ({d.cards.count(card)})\n'
            else:
                text += f'{CARDPOOL_MAX}+ cards'
            text += f'\n[{d.name}]'
        self.view.cardpool.set_text(text)

    def update_drawdeck(self):
        logging.debug(f'APP: update_drawdeck')
        for i in range(TOP_CARDS):
            if i < len(self.game.deck['draw']):
                c = self.game.deck['draw'].cards[-1-i]
                text = f'{len(c)}' if len(c) > 1 else c.cards[0].name
                btn = self.view.drawdeck.button[i]
                btn.setEnabled(True)
                btn.set_text(text)
                print(f'enabling {i} : {text}')
                btn.clicked.connect(lambda index=i: self.cb_select_cardpool(index))
            else:
                text = ''
                btn = self.view.drawdeck.button[i]
                btn.set_text(text)
                print(f'disabling {i}')
                btn.setEnabled(False)

    def update_epidemic_menu(self):
        """Update the epidemic dropdown list
        based on the available cards in the Draw Deck."""
        deck = self.game.deck['draw']
        if not deck.is_empty():
            items = sorted([c.name for c in list(set(deck.bottom().cards))])
            self.view.epidemic_menu.combo_box.setDisabled(False)
            self.view.epidemic_menu.button.setDisabled(False)
        else:
            items = ['(Draw Deck Empty)']
            self.view.epidemic_menu.combo_box.setDisabled(True)
            self.view.epidemic_menu.button.setDisabled(True)

        self.view.epidemic_menu.combo_box.clear()
        self.view.epidemic_menu.combo_box.addItems(items)

    def update_stats(self):
        stats = self.game.stats
        text = f'Total cards: {stats.total}\n'
        text += f'In discard pile: {stats.in_discard}\n'
        if not stats.deck['draw'].is_empty():
            text += f'\nTop card frequency:\n'
            text += f'{stats.top_freq} '
            text += f'({stats.percentage:.2%})'
            text += '\n\n'
            if len(stats.top_cards) < STATS_MAX:
                for card in stats.top_cards:
                    text += f'\u2022 {card.name}\n'
            else:
                text += f'({STATS_MAX}+ cards)'
        else:
            text += '\n(Draw Deck is empty)'
        self.view.stats.text.setText(text)

    def cb_select_cardpool(self, index):
        logging.debug('APP: cb_select_cardpool')
        self.cardpool_index = index

    def cb_new_game_dialog(self):
        logging.debug('APP: cb_new_game')
        games = list(self.game.games.keys())
        dialog = DialogNewGame(games)
        if dialog.exec_():
            self.game.initialise(dialog.combo.currentText())
            self.view.initialise()
            # self.view.deck['draw'].clear()
            self.populate_draw()
            self.cb_select_cardpool(0)
            self.update_drawdeck()
            self.update_epidemic_menu()
            self.update_stats()

    def cb_epidemic(self):
        """Shuffle epidemic card based on the selected card in the combobox."""
        logging.debug('APP: cb_epidemic')
        new_card_name = self.view.epidemic_menu.combo_box.currentText()
        self.game.epidemic(new_card_name)
        self.view.deck['discard'].clear()
        self.view.deck['draw'].clear()
        self.populate_draw()
        self.update_drawdeck()
        self.update_epidemic_menu()
        self.update_cardpool()
        self.cb_select_cardpool(0)

    @staticmethod
    def cb_help_dialog():
        logging.debug('APP: cb_help')
        """Callback from the Help button.
        Displays a dialog with the option to view Help in browser."""
        dialog = DialogHelp()
        if dialog.exec_():
            webopen('https://github.com/Merkwurdichliebe/Epidemic/wiki')


def main():
    application = QApplication()
    view = MainWindow()
    model = Game()
    App(view, model)
    view.show()
    application.exec_()


if __name__ == '__main__':
    main()
