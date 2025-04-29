from dothat import lcd, backlight
from dot3k.menu import MenuIcon
import time
from queue import Queue, Empty
from ui.http.metadata.MetadataHandler import *
from .abstract_ui import AbstractUI


class RecordStart(AbstractUI):
    """Checks that everything is ready, and if so advances to Record"""
    state = None

    def delete_temporary_file(self):
        print("DELETE TEMPORARY FILE")

    def split_tracks(self):
        print("SPLIT TRACKS")

    def exit(self):
        self.recorder.stop()
        self.ui.open_menu()

    states = {
        'file_exists': {
            'message': [
                'Prev. file found',
                'Split or delete?',
                'DELETE     SPLIT'
            ],
            'options': {
                'left': delete_temporary_file,
                'right': split_tracks
            }
        },
        'bad_input_device': {
            'message': [
                'Bad input device',
                'Go to settings',
                '      BACK      '
            ],
            'options': {
                'select':
                    exit
            }
        }
    }

    def __init__(self, repline, ui):
        self.ui = ui
        self.repline = repline
        self.recorder = repline.recorder

    def on_active(self):
        print("Pre record started")
        if self.recorder.temporary_file_exists():
            self.state = "file_exists"
            return

        print("No temporary files")

        if not self.recorder.open_input_device():
            print("Input device failed")
            self.state = "bad_input_device"
            return

        print("Input device OK")

        self.ui.open_record_ui()

    def redraw(self):
        print("Redraw record_start, state {0}".format(self.state))
        if self.state is not None:
            state_definition = self.states[self.state]
            self.display_message(state_definition['message'])

    def handle_left(self, ch, evt):
        if self.state is not None:
            state_definition = self.states[self.state]
            if 'left' in state_definition['options']:
                state_definition['options']['left'](self)

    def handle_right(self, ch, evt):
        if self.state is not None:
            state_definition = self.states[self.state]
            if 'right' in state_definition['options']:
                state_definition['options']['right'](self)

    def handle_select(self, ch, evt):
        if self.state is not None:
            state_definition = self.states[self.state]
            if 'select' in state_definition['options']:
                state_definition['options']['select'](self)

