import textwrap
import typing

from dothat import lcd, backlight
from dot3k.menu import MenuIcon
import time
from queue import Queue, Empty
from ui.http.metadata.MetadataHandler import *
from .abstract_ui import AbstractUI

class Record(AbstractUI):
    icon_record = [0, 14, 31, 31, 31, 14, 0, 0]
    icon_stop = [0, 31, 31, 31, 31, 31, 0, 0]
    icon_tick = [0, 0, 0, 17, 26, 12, 0, 0]

    # The temporary file(s) already exist, so we're asking the user if they want to keep them
    state_file_exists = "file_exists"

    # Waiting to start recording
    state_idle = "idle"

    # Recording
    state_recording = "recording"

    # The user is entering metadata. Can return to idle, recording or complete
    state_metadata = "metadata"

    # Recording is complete, we are still processing for silences before continuing to set track boundaries
    state_complete = "complete"

    # An error that means we can't continue. OK or back take us out to the menu, all other buttons ignored.
    state_error = "error"

    queue = None
    is_running = False

    ui = None
    updateTime = 0.1

    metadata_server = None
    metadata_state_none = ""
    metadata_state_ready = "ready"
    metadata_state_open = "open"
    metadata_state_complete = "complete"
    metadata_state = metadata_state_none
    metadata_return_state = None

    audio_metadata = None

    def __init__(self, repline, ui):
        self.ui = ui
        self.repline = repline
        self.recorder = repline.recorder
        self._icons_setup = False
        self.state = self.state_idle
        self.queue = Queue()

    def on_active(self):
        self.recorder.start_listening()
        self.recorder.register_callback_queue(self.queue)

    def setup_icons(self):
        lcd.create_char(0, self.icon_record)
        lcd.create_char(1, MenuIcon.pause)
        lcd.create_char(2, self.icon_stop)

    def handle_left(self, ch, evt):
        print("We want to record; current state is %s. We want it to be %s. " % (self.state, self.state_recording))
        if self.state == self.state_idle:
            self.state = self.state_recording
            print("Set state to %s" % self.state)
            self.recorder.record()
        else:
            print("Bad state, doing nothing")

    def handle_select(self, ch, evt):
        if not self.state == self.state_metadata:
            self.metadata_return_state = self.state
            print ("Let's get metadata")
            if self.metadata_server is None:
                self.metadata_server = MetadataServer()
            print ("Got a server")
            self.metadata_server.add_callback(self.handle_metadata_callback)
            self.metadata_server.open()
            self.metadata_state = self.metadata_state_ready
            print("...")
            print ("Server is open at %s" % self.metadata_server.get_address())
            self.state = self.state_metadata
            print("Complete")

    def handle_metadata_callback(self, method, params=[]):
        if (method == "GET"):
            self.metadata_state = self.metadata_state_open
        elif (method == "POST"):
            self.metadata_state = self.metadata_state_complete
            self.state = self.metadata_return_state
            self.audio_metadata = params

    def handle_right(self, ch, evt):
        if self.state == self.state_recording:
            def on_yes():
                self.recorder.stop()
                self.state = self.state_complete
                print("Set state to %s" % self.state)

            self.ui.are_you_sure("Finish recording", on_yes = on_yes)

    def go_to_track_alignment(self):
        print("go_to_track_alignment")
        # Make sure we have updated silences
        silences = self.recorder.get_silences()

        # Pass the data on to the alignment UI
        self.ui.alignment_ui.set_silences(silences)
        self.ui.alignment_ui.set_metadata(self.audio_metadata)
        self.ui.open_alignment()
        self.ui.alignment_ui.find_tracks()

    def handle_cancel(self, ch, evt):
        # if self.state == self.state_idle:
        def do_cancel():
            self.recorder.stop()
            self.ui.open_menu()
        self.ui.are_you_sure("Cancel recording", on_yes=do_cancel)

    def redraw(self):
        if not self._icons_setup:
            self.setup_icons()

        self.recorder.update_dispatcher_status()
        lcd.clear()

        if self.state == self.state_idle:
            self.redraw_idle()
        elif self.state == self.state_recording:
            self.redraw_recording()
        elif self.state == self.state_metadata:
            self.redraw_metadata()
        elif self.state == self.state_error:
            self.display_message(self.current_error())
        elif self.state == self.state_complete:
            self.redraw_complete()

    def current_error(self):
        # TODO
        return [
            'Error'
        ]



    def redraw_idle(self):
        lcd.set_cursor_position(0, 0)
        lcd.write("Record")
        status = self.recorder.get_dispatcher_status()
        # print(status)

        if self.recorder.dispatcher_response_soundlevel in status:
            sound_level = status[self.recorder.dispatcher_response_soundlevel]
            if sound_level is not None:
                lcd.set_cursor_position(10, 0)
                lcd.write("{0:>4}dB".format(sound_level))

        if self.audio_metadata is not None:
            # TODO: Alternate/scroll artist and title
            lcd.set_cursor_position(0, 1)
            lcd.write(self.audio_metadata["title"][:16])

        # Line up labels with buttons on bottom row
        lcd.set_cursor_position(3, 2)
        lcd.write(chr(0))
        lcd.set_cursor_position(6, 2)
        lcd.write("META")
        lcd.set_cursor_position(13, 2)
        lcd.write(chr(2))

    def redraw_recording(self):
        lcd.set_cursor_position(0, 0)
        duration = self.recorder.get_recording_duration()
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            lcd.write('{:02}:{:02}'.format(int(hours), int(minutes)))
        else:
            lcd.write('{:02}:{:02}'.format(int(minutes), int(seconds)))

        if self.audio_metadata is not None:
            # TODO: Alternate/scroll artist and title
            lcd.set_cursor_position(0, 1)
            lcd.write(self.audio_metadata["title"][:16])

        # Line up labels with buttons on bottom row
        lcd.set_cursor_position(3, 2)
        lcd.write(chr(0))
        lcd.set_cursor_position(6, 2)
        lcd.write("META")
        lcd.set_cursor_position(13, 2)
        lcd.write(chr(2))

    def redraw_metadata(self):
        msg = []
        if self.metadata_state == self.metadata_state_ready:
            msg[0] = "Open browser at:"
        elif self.metadata_state == self.metadata_state_open:
            msg[0] = "Enter metadata"
        url = textwrap.wrap(self.metadata_server.get_address(), width=16, break_long_words=True, max_lines=2)
        msg[1] = url[0]
        if len(url) > 1:
            msg[2] = lcd.write(url[1])

        self.display_message(msg)

    def redraw_stopped(self):
        lcd.set_cursor_position(0, 0)
        duration = self.recorder.get_recording_duration()
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            lcd.write('{:02}:{:02}'.format(int(hours), int(minutes)))
        else:
            lcd.write('{:02}:{:02}'.format(int(minutes), int(seconds)))

        # Line up labels with buttons on bottom row
        lcd.set_cursor_position(3, 2)
        lcd.write(chr(0))
        lcd.set_cursor_position(6, 2)
        lcd.write(lcd.write("META"))
        lcd.set_cursor_position(13, 2)
        lcd.write(chr(2))

    def redraw_complete(self):
        lcd.set_cursor_position(0, 0)
        status = self.recorder.get_dispatcher_status()
        index = status[self.recorder.dispatcher_response_file_index]
        processes_remaining = status[self.recorder.dispatcher_response_process_count]
        time_remaining = status[self.recorder.dispatcher_response_time_remaining]
        print("Dispatcher status: index: %s (%s) processes: %s (%s) time remaining: %s (%s)" % (
            index,
            type(index),
            processes_remaining,
            type(processes_remaining),
            time_remaining,
            type(time_remaining)
        ))
        if processes_remaining == 0:
            print("Done")
            self.go_to_track_alignment()
        else:
            msg = [
                "Finding tracks",
                "Time remaining:"
            ]
            lcd.set_cursor_position(0, 1)
            lcd.write("Time remaining:")
            lcd.set_cursor_position(0, 2)
            if time_remaining is None:
                msg.push("Unknown")
            elif time_remaining > 0:
                minutes, seconds = divmod(time_remaining, 60)
                msg.push('{:02}:{:02}'.format(int(minutes), int(seconds)))
            else:
                msg.push('Just a moment...')
            return msg

    def connect(self):
        """Empty the queue and connect to the recorder, with a separate thread monitoring for updates"""
        self.queue.empty()
        self.is_running = True
        self.repline.register_callback_queue("recorder", self.queue)

    def visualisation(self):
        while True:
            got_data = False
            try:
                (indata, status) = self.queue.get_nowait()
                got_data = True
            except Empty:
                pass
            if got_data:
                mean = indata.mean()
                # print("Vis: %f (min %f, max %f, count %f)" % (mean, indata.min(), indata.max(), len(indata)))
                backlight.set_graph(mean*3)
            time.sleep(self.updateTime)
