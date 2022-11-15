import dothat.touch as nav
from dot3k.menu import Menu

from repline import Settings
from .settings import *
from .record import *

class MainMenu():
    controller = None

    def __init__(self, repline, controller):
        self.repline = repline
        self.controller = controller

        self.menu = Menu(
            structure= {
                'Record': self.record,
                'Settings': self.generate_menu_structure(repline, Settings.options),
            },
            lcd=lcd)

    def generate_menu_structure(self, repline, menu_definition, parents=[]):
        if "class" in menu_definition:
            # This defines a single menu item
            return menu_definition['class'](repline, config_location=parents, **menu_definition)
        else:
            return {name.capitalize().replace('_', ' '): self.generate_menu_structure(repline, definition, parents=parents+[name]) for (name, definition) in menu_definition.items()}

    def on_active(self):
        pass

    def redraw(self):
        self.menu.redraw()

    def record(self):
        self.controller.open_prerecord_ui()

    def handle_up(self, ch, evt):
        print("handle_up, menu: {0}".format(self.menu.__class__))
        self.menu.up()

    def handle_down(self, ch, evt):
        print("handle_down, menu: {0}".format(self.menu.__class__))
        self.menu.down()

    def handle_left(self, ch, evt):
        print("handle_left, menu: {0}".format(self.menu.__class__))
        self.menu.left()

    def handle_right(self, ch, evt):
        print("handle_right, menu: {0}".format(self.menu.__class__))
        self.menu.right()

    def handle_select(self, ch, evt):
        print("handle_select, menu: {0}".format(self.menu.__class__))
        self.menu.select()

    def handle_cancel(self, ch, evt):
        print("handle_cancel, menu: {0}".format(self.menu.__class__))
        self.menu.cancel()

class Contrast(MenuOption):
    def __init__(self, lcd):
        self.lcd = lcd
        self._icons_setup = False
        MenuOption.__init__(self)

    def setup_icons(self, menu):
        menu.lcd.create_char(0, MenuIcon.arrow_left_right)
        self._icons_setup = True

    def cleanup(self):
        self._icons_setup = False

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

def open_ui(repline):
    menu = MainMenu(repline)