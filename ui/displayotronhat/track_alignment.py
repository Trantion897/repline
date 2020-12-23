from dothat import lcd, backlight
from audio_manipulation.audio_manipulation import *

class TrackAlignment():

    full_recording = None
    audio_metadata = None

    current_option = 0

    state_ready = "ready"
    state_loading = "loading"
    state_scanning = "scanning"
    state = state_loading

    menu = None

    def __init__(self, repline, controller):
        self.repline = repline
        self.controller = controller
        self.tracklayout = TrackLayout()

    def on_active(self):
        self.controller.register_animated_e()
        pass

    def load_recording(self):
        self.set_state(state = self.state_loading)
        self.tracklayout.read_file(self.repline.recorder.temporary_file)

    def set_metadata(self, metadata):
        self.tracklayout.set_metadata(metadata)

    def set_silences(self, silences):
        self.tracklayout.set_silences(silences)

    def find_tracks(self):
        # TODO: Silence settings

        # TODO: This is very slow
        # TODO: The pi 2 has 4 cores, so we could chop the track into 4 parts and multi-thread it
        # TODO: Using the main thread might be causing UI glitches too
        # TODO: Try recording rough amplitude during recording to find areas to scan for silences later

        # TODO: Could create dummy entries for now so I can continue testing
        print("Matching tracks")
        self.set_state(self.state_scanning)
        self.layout = self.tracklayout.match() # TODO: Handle exception
        self.menu = ["Track lengths"] + self.layout.get_track_listing() + [
            "Confirm",
            "Reset all"
        ]
        self.current_option = 0
        print ("Menu:")
        print(self.menu)
        self.set_state(self.state_ready)

    def generate_menu_items(self):
        menu = [{"title" : "Track lengths"}]
        # We start with a pointer at the beginning of the track listing
        # Each track has a length of 0..n non-silent sections
        # We move that number ahead, counting the time between those silences as the length of the track
        # And then advance the pointer for the next track
        trackStart = 0
        trackNumber = 1
        for trackLength in self.layout.get_track_listing():
            trackEnd = trackStart + trackLength -1
            duration = self.layout.tracks[trackEnd][1] - self.layout.tracks[trackStart][0]
            minutes, seconds = divmod(duration, 60)
            menu.append({
                "title" : "Track %d" % trackNumber, # TODO
                "duration" : "% 2d:%02d" % (minutes, seconds),
                "number" : trackNumber
            })
            trackStart = trackEnd + 1 # Next track starts after this one
            trackNumber += 1

    def set_state(self, state):
        lcd.clear()
        print("set_state(%s)" % state)
        if state == self.state_loading or state == self.state_scanning:
            lcd.set_cursor_position(0, 0)
            lcd.write("Please wait...")
            self.controller.display_repline_animation(0, 1)
            lcd.set_cursor_position(0, 2)
            if state == self.state_loading:
                lcd.write("Loading recordin")
            else:
                lcd.write("Finding tracks  ")
        self.state = state

    def redraw(self):
        if self.state == self.state_ready:
            if self.current_option > 0:
                self.display_row(0, self.menu[self.current_option-1])
            self.display_row(1, self.menu[self.current_option])
            if self.current_option < len(self.menu)-1:
                self.display_row(2, self.menu[self.current_option+1])
        else:
            lcd.update_animations()

    def display_row(self, row, menuEntry):
        lcd.set_cursor_position(1, row)
        if "number" in menuEntry:
            lcd.write("%02d. %s" % (menuEntry["number"], menuEntry["title"][:7]))
            lcd.set_cursor_position(11, row)
            lcd.write(menuEntry["duration"])
        else:
            lcd.write(menuEntry["title"])

    def handle_up(self, ch, evt):
        if self.current_option > 0:
            self.current_option -= 1
            self.redraw()

    def handle_down(self, ch, evt):
        if self.current_option < len(self.menu)-1:
            self.current_option += 1
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


