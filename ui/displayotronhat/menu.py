from .settings import *
from .record import *

class MainMenu():
    controller = None

    def __init__(self, repline, controller):
        self.repline = repline
        self.controller = controller

        self.menu = Menu(
            structure={
                'Record': self.record,
                'Settings': {
                    'Recording': {
                        'Normalisation': Normalisation(repline)
                    },
                    'Track detection': {
                        SilenceThreshold.title: SilenceThreshold(repline),
                        MinSilenceLength.title: MinSilenceLength(repline)
                    },
                    'Encoding': {
                        OutputFormat.title: OutputFormat(repline),
                        get_quality_setting(repline).title: get_quality_setting(repline)
                    },
                    # 'Saving': {
                    # },
                    'Hardware': {
                        SetInputDevice.title: SetInputDevice(repline),
                        SetOutputDevice.title: SetOutputDevice(repline),
                    }
                }
            },
            lcd=lcd)
        nav.bind_defaults(self.menu)

    def on_active(self):
        pass

    def redraw(self):
        self.menu.redraw()

    def record(self):
        self.controller.open_record_ui()

    def handle_up(self, ch, evt):
        self.menu.up()

    def handle_down(self, ch, evt):
        self.menu.down()

    def handle_left(self, ch, evt):
        self.menu.left()

    def handle_right(self, ch, evt):
        self.menu.right()

    def handle_select(self, ch, evt):
        self.menu.select()

    def handle_cancel(self, ch, evt):
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