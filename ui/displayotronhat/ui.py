import dothat.touch as nav
from .record import *
from .menu import MainMenu
from .track_alignment import *

class UI:
    # Currently displayed UI
    active_ui = None

    # UI behind the current one, if applicable
    previous_ui = None

    menu = None
    record_ui = None
    alignment_ui = None

    auto_redraw = True
    redraw_rate = 1

    repline_animated_e = [
        [0, 0, 14, 17, 31, 16, 14, 0], # Normal
        [0, 0, 12, 21, 21, 21, 14, 0], # 90° left
        [0, 0, 14, 1, 31, 17, 14, 0], # Upside down
        [0, 0, 14, 21, 21, 21, 6, 0] # 90° right
    ]

    def __init__(self, repline):
        self.menu = MainMenu(repline, self)
        self.record_ui = Record(repline, self)
        self.alignment_ui = TrackAlignment(repline, self)
        self.open_menu()

        bind_buttons(self)
        self.set_redraw_rate(1)

    def set_redraw_rate(self, rate):
        self.auto_redraw = True
        self.redraw_rate = rate
        while True:
            if self.auto_redraw:
                self.redraw()
            time.sleep(self.redraw_rate)

    def stop_redrawing(self):
        self.auto_redraw = False

    def open_record_ui(self):
        self.active_ui = self.record_ui
        self.record_ui.on_active()

    def open_menu(self):
        self.active_ui = self.menu
        self.menu.on_active()

    def open_alignment(self):
        print("open_alignment")
        self.active_ui = self.alignment_ui
        self.alignment_ui.on_active()

    def redraw(self):
        # print("Redrawing UI from process %d" % os.getpid())
        self.active_ui.redraw()

    def handle_up(self, ch, evt):
        self.active_ui.handle_up(ch, evt)
        self.redraw()

    def handle_down(self, ch, evt):
        self.active_ui.handle_down(ch, evt)
        self.redraw()

    def handle_left(self, ch, evt):
        print ("handle_left: active UI is %s" % self.active_ui.__class__)
        self.active_ui.handle_left(ch, evt)
        self.redraw()

    def handle_right(self, ch, evt):
        print ("handle_right: active UI is %s" % self.active_ui.__class__)
        self.active_ui.handle_right(ch, evt)
        self.redraw()

    def handle_select(self, ch, evt):
        print("handle_select: active UI is {0}".format(self.active_ui.__class__))
        self.active_ui.handle_select(ch, evt)
        self.redraw()

    def handle_cancel(self, ch, evt):
        print ("handle_cancel: active UI is %s" % self.active_ui.__class__)
        self.active_ui.handle_cancel(ch, evt)
        self.redraw()
        return False

    def register_animated_e(self):
        # TODO: Variable char_pos
        lcd.create_animation(7, self.repline_animated_e, 2)

    def display_repline_animation(self, col, row):
        # TODO: Currently occupies the whole row, might want to allow it to be in a corner
        lcd.set_cursor_position(col+4, row)
        # lcd.write("    Repline     ")
        lcd.write("R"+chr(7)+"plin"+chr(7))

    def are_you_sure(self, message="", on_yes=None, on_no=None):
        """Displays an "Are you sure?" message with yes/no options
        :param message string 16 characters to display to the user
        :param on_yes  Function to call if the user answers 'yes'
        :param on_no   Function to call if the user answers 'no'
        """
        AreYouSure(self, message, on_yes, on_no)

def bind_buttons(ui):
    @nav.on(nav.UP)
    def handle_up(ch, evt):
        ui.handle_up(ch, evt)

    @nav.on(nav.DOWN)
    def handle_down(ch, evt):
        ui.handle_down(ch, evt)

    @nav.on(nav.LEFT)
    def handle_left(ch, evt):
        ui.handle_left(ch, evt)

    @nav.on(nav.RIGHT)
    def handle_right(ch, evt):
        ui.handle_right(ch, evt)

    @nav.on(nav.BUTTON)
    def handle_select(ch, evt):
        ui.handle_select(ch, evt)

    @nav.on(nav.CANCEL)
    def handle_cancel(ch, evt):
        ui.handle_cancel(ch, evt)
        return True

def open_ui(repline):
    ui = UI(repline)

class AreYouSure():
    def __init__(self, ui, message="", on_yes=None, on_no=None):
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no
        self.ui = ui
        self.ui_was_auto_redraw = ui.auto_redraw
        ui.auto_redraw = False
        self.ui.previous_ui = self.ui.active_ui
        self.ui.active_ui = self

    def redraw(self):
        lcd.clear()
        lcd.set_cursor_position(0, 0)
        lcd.write(" Are you sure?")
        lcd.set_cursor_position(0, 1)
        lcd.write(self.message)
        lcd.set_cursor_position(2, 2)
        lcd.write("NO")
        lcd.set_cursor_position(12, 2)
        lcd.write("YES")

    def handle_up(self, ch, evt):
        pass

    def handle_down(self, ch, evt):
        pass

    def handle_left(self, ch, evt):
        self.no()

    def handle_right(self, ch, evt):
        self.yes()

    def handle_select(self, ch, evt):
        pass

    def handle_cancel(self, ch, evt):
        self.no()

    def no(self):
        print("Are you sure? NO! Got function? %s" % callable(self.on_no))
        self.ui.active_ui = self.ui.previous_ui
        if callable(self.on_no):
            self.on_no()
        self.clean_up()

    def yes(self):
        print("Are you sure? YES! Got function? %s" % callable(self.on_yes))
        self.ui.active_ui = self.ui.previous_ui
        if callable(self.on_yes):
            self.on_yes()
        self.clean_up()

    def clean_up(self):
        self.ui.auto_redraw = self.ui_was_auto_redraw
        self.ui.redraw()