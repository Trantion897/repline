import datetime

from dothat import lcd

import ui.displayotronhat.ui
from audio_manipulation.audio_manipulation import *
from dot3k.menu import MenuIcon, Menu

class TrackListing():

    def __init__(self, repline, controller):
        self.repline = repline
        self.controller = controller
        self.tracklayout = TrackLayout()
        self.pointer = 0

    def on_active(self):
        lcd.create_char(0, MenuIcon.arrow_up_down)
        lcd.create_char(1, MenuIcon.play)
        lcd.create_char(2, ui.displayotronhat.ui.icon_hamburger)
        lcd.create_char(3, MenuIcon.arrow_left_right)
        lcd.clear()

    def redraw(self):
        # Top row
        lcd.set_cursor_position(0, 0)
        if self.pointer == 0:
            lcd.write("  Edit tracks   ")
        else:
            lcd.write(" "+self.display_track(self.pointer))
        # Middle row
        lcd.set_cursor_position(0, 1)
        lcd.write(chr(0)+self.display_track(self.pointer+1))
        # Bottom row
        lcd.set_cursor_position(0, 2)
        lcd.write("  {p}    {o}    {e}   ".format(
            p=chr(1),
            o=chr(2),
            e=chr(3)
        ))

        lcd.set_cursor_position(0, 1)

    def display_track(self, track_number):
        """
        Get a track's data as a string
        :param track_number:
        :return: String
        """
        return "Track {t: 3}:{len}".format(
            t=track_number,
            len=self.display_time(self.repline.track_data.tracks[track_number-1].get_duration())
        )

    def display_time(self, seconds):
        """
        Format a time in seconds for display

        Output is always 5 characters (__:__)
        If under 1 minute, prefix with space  " 0:12"
        If under 10 minutes, prefix with zero "01:23"
        If under 1 hour, display min:sec      "12:34"
        If over 1 hour, display hours/min     "01h23"
        If over 99 hours, display hours only  "9999h"
        If over 9999 hours, add + sign        "9999+"
        :param seconds: Number of seconds
        :return: String
        """
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours <= 0:
            return "{m: >2}:{s:0>2}".format(m=minutes, s=seconds)
        elif hours <= 99:
            return "{h: >2}h{m:0>2}".format(h=hours, m=minutes)
        elif hours <= 9999:
            return "{h: >4}h".format(h=hours)
        else:
            return "9999+"

    def handle_up(self, ch, evt):
        if self.pointer > 0:
            self.pointer -= 1
            self.redraw()

    def handle_down(self, ch, evt):
        if self.pointer < len(self.repline.track_data.tracks)-1:
            self.pointer += 1
            self.redraw()

    def handle_left(self, ch, evt):
        # TODO: Check for off-by-one errors
        self.layout.shorten_track(self.current_option)
        self.generate_menu_items()
        self.redraw()

    def handle_right(self, ch, evt):
        self.layout.lengthen_track(self.current_option)
        self.generate_menu_items()
        self.redraw()

    def handle_select(self, ch, evt):
        # TODO: Play start & end of current track
        print("Will play music")

    def handle_cancel(self, ch, evt):
        pass

class TrackOptions:
    def redraw(self):
        # Top row
        lcd.set_cursor_position(0, 0)
        if self.pointer == 0:
            lcd.write("Edit track {0}".format())
        else:
            lcd.write(" "+self.display_track(self.pointer))
        # Middle row
        lcd.set_cursor_position(0, 1)
        lcd.write(chr(0)+self.display_track(self.pointer+1))
        # Bottom row
        lcd.set_cursor_position(0, 2)
        lcd.write("  {p}    {o}    {e}   ".format(
            p=chr(1),
            o=chr(2),
            e=chr(3)
        ))

        lcd.set_cursor_position(0, 1)
