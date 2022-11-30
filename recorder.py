import audioop
import math
import queue
from pickle import UnpicklingError
import setproctitle

import sounddevice as sd
import soundfile as sf
from multiprocessing import Queue
from queue import Empty
from datetime import datetime
import os.path
from time import monotonic, sleep
from pydub import AudioSegment
from pydub.silence import *
from math import ceil

import numpy
import alsaaudio

import sys
import multiprocessing

class recorder():
    recording_start_time = None
    recording_end_time = None

    temporary_file = "tmp/repline-input-%d.wav"
    temporary_file_max_length = 1

    dispatcher = None
    # A queue for the dispatcher to send its current status to. Each entry contains:
    # (recording file index, number of active FindSilence processes, estimated completion time)
    dispatcher_status = None

    # Stores the latest entry from dispatcher_status
    dispatcher_last_status = None

    # If true, continually monitor messages from the dispatcher
    dispatcher_monitor_active = True

    # Tell the dispatcher to start or stop recording by passing this with true or false
    dispatcher_command_recording = "recording"
    # Tell the dispatcher to send the full list of silences so far
    dispatcher_command_send_silences = "send_silences"
    # Dispatcher response key containing the index of the file currently being recorded
    dispatcher_response_file_index = "file_index"
    # Dispatcher response key containing the number of find silence processes currently running
    dispatcher_response_process_count = "process_count"
    # Dispatcher response key containing the estimated time in seconds until all find silence processes finish
    dispatcher_response_time_remaining = "time_remaining"
    # Dispatcher response key containing a list of found silences
    dispatcher_response_silence_list = "silences"
    # Dispatcher response key containing sound level in decibels
    dispatcher_response_soundlevel = "sound_level"

    # List of found silences
    silences = []

    # Comes from SoundDevice
    device = None
    channels = 0

    def __init__(self, repline):
        self.sample_rate = int(repline.config.get(['recording', 'sample_rate']))
        sd.default.channels = self.channels
        sd.default.samplerate = self.sample_rate
        self.q = Queue()
        self.queues = []
        self.is_recording = False

        self.last_status = {}
        self.temporary_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.temporary_file)
        self.repline = repline

    def start_listening(self):
        # Initialise the dispatcher and listener
        print("Start_listening")
        self.dispatcher_status, dispatcher_end = multiprocessing.Pipe()
        self.dispatcher = AudioDispatcher(self, dispatcher_end, name='Audio Dispatcher')
        self.dispatcher.start()

    def open_input_device(self):
        setting = self.repline.config.get(['hardware', 'input_device'])
        if setting is None:
            return False

        try:
            input_device = sd.query_devices(setting)
            print(input_device)
            if input_device.__class__ == dict:
                # TODO: Maybe allow us to limit to stereo or even mono
                self.channels = min(input_device['max_input_channels'], int(self.repline.config.get(['recording', 'max_channels'])))
                self.device = input_device['index']
                return True
            else:
                return False

        except ValueError:
            return False



    def temporary_file_exists(self):
        return os.path.exists(self.temporary_file)

    def register_callback_queue(self, queue: Queue):
        """Register an external queue to receive playback data.
        This should be queried in a separate thread.
        """
        print ("Registering callback")
        self.dispatcher.addCallbackQueue(queue)

    def get_audio_devices(self):
        return sd.query_devices()

    def get_input_devices(self):
        devices = self.get_audio_devices()
        return [d for d in devices if d['max_input_channels'] > 0]

    def get_output_devices(self):
        devices = self.get_audio_devices()
        return [d for d in devices if d['max_output_channels'] > 0]

    def set_default_input_device(self, device):
        sd.default.device[0] = device

    def set_default_output_device(self, device):
        sd.default.device[1] = device

    def get_default_input_device(self):
        return sd.default.device[0]

    def get_default_output_device(self):
        return sd.default.device[1]

    def record(self):
        self.is_recording = True
        self.dispatcher_status.send({self.dispatcher_command_recording: True})
        self.recording_start_time = datetime.now()

    def get_recording_duration(self):
        """Get the recording duration"""
        if self.recording_start_time == None:
            return None
        elif self.is_recording:
            return (datetime.now() - self.recording_start_time)
        else:
            return (self.recording_end_time - self.recording_end_time)

    def stop(self):
        self.is_recording = False
        self.dispatcher_status.send({self.dispatcher_command_recording: False})
        self.recording_end_time = datetime.now()

        print ("Recording complete")

    def update_dispatcher_status(self):
        if self.dispatcher_status.poll():
            try:
                new_status = self.dispatcher_status.recv()
                if self.dispatcher_response_silence_list in new_status:
                    self.silences = new_status[self.dispatcher_response_silence_list]
                self.last_status.update(new_status)
            except UnpicklingError:
                print("Unpickling error")
                pass

    def get_dispatcher_status(self):
        return self.last_status

    def get_silences(self):
        """Get the latest list of silences from the AudioDispatcher"""
        self.dispatcher_monitor_active = False
        self.dispatcher_status.send({self.dispatcher_command_send_silences: True})
        if self.dispatcher_status.poll(10):
            while self.dispatcher_status.poll():
                status = self.dispatcher_status.recv()
                if self.dispatcher_response_silence_list in status:
                    self.silences = status[self.dispatcher_response_silence_list]
                    break
        # TODO: Handle what happens if we never got a silence list
        return self.silences

class AlsaMixerControl:
    capture_mixers = []

    def __init__(self, repline):
        self.repline = repline
        self.alsa_device_name = self.get_alsa_device_name()

        # Find useful mixers and controls
        mixers = alsaaudio.mixers(device=self.alsa_device_name)
        sources = [m for m in mixers if m.lower().find('source') != -1]
        line = [m for m in mixers if m.lower().find('line') != -1]
        mic = [m for m in mixers if m.lower().find('mic') != -1]

        # 1. Any channel with 'source' in the name should have an enum set to Line, Mic as fallback
        for mixer_name in sources:
            mixer = alsaaudio.Mixer(control=mixer_name, device=self.alsa_device_name)
            enum = mixer.getenum()
            if len(enum) == 2:
                value, options = enum
                options = [x.lower() for x in options]
                if 'line' in options:
                    mixer.setenum(options.index('line'))

        # 2. Any channel with 'line' in the name should have recording enabled and the volume set
        if len(line) > 0:
            self.capture_mixers = [alsaaudio.Mixer(control=mixer_name, device=self.alsa_device_name) for mixer_name in line]
        # 2a. If no 'line' channel, do the same to 'mic'
        elif len(mic) > 0:
            self.capture_mixers = [alsaaudio.Mixer(control=mixer_name, device=self.alsa_device_name) for mixer_name in mic]

        self.set_capture_volume(int(self.repline.config.get(['recording', 'volume'])))

    def set_capture_volume(self, volume):
        print("set_capture_volume({0}) on {1}".format(volume, ", ".join(m.mixer() for m in self.capture_mixers)))
        for mixer in self.capture_mixers:
            mixer.setrec(1)
            mixer.setvolume(volume, pcmtype=alsaaudio.PCM_CAPTURE)

    def get_alsa_device_name(self):
        fullname = self.repline.config.get(['hardware', 'input_device'])
        alsa_name_index = fullname.index('hw:')  # TODO: Capture exception on failure
        alsa_name_end = fullname.index(':', alsa_name_index)+2
        alsa_name = fullname[alsa_name_index: alsa_name_end]

        return alsa_name

class AudioDispatcher(multiprocessing.Process):
    """Manages the AudioInputListener, writing captured audio to the temporary files, spawning processes to find tracks & silences in those temporary files"""
    # Reference to the recording controller
    recorder = None
    # Pipe used for communication with the recorder
    recorder_status = None

    # AudioInputListener - listens to incoming audio and writes to the input queue
    listener = None
    # Queue from AudioInputListener -> AudioDispatcher (receives incoming audio)
    inputQueue = None

    # FindSilences
    silenceProcessor = None
    # List of queues to copy incoming audio to
    callbackQueues = []

    # Dictionary of FindSilence processes {index: process}
    find_silence_processes = {}
    # Queue for FindSilence processes to report back to, as a tuple of (process index, [list, of, silences], time taken)
    find_silence_queue = None
    # Number of FindSilence processes currently running
    find_silence_process_count = 0
    # List of detected silences, each one is a list of [start, end]
    silences = None
    # Time taken to complete each completed process (used to calculate a mean)
    find_silence_process_complete_time = None
    # Start time of each currently running process
    find_silence_running_process_start_time = None

    state = 'idle'

    max_processes = 1
    queued_processes = None

    status = {}

    def __init__(self, recorder, recorder_status, **kwargs):
        self.recorder = recorder
        self.recorder_status = recorder_status
        self.inputQueue = Queue()
        self.callbackQueues = []

        self.silences = []
        self.find_silence_queue = Queue()
        self.find_silence_process_complete_time = []
        self.find_silence_running_process_start_time = {}

        self.max_processes = max(1, multiprocessing.cpu_count() - 2)
        self.queued_processes = queue.Queue()
        super().__init__(**kwargs)

    def addCallbackQueue(self, queue):
        """Add a queue that receives a copy of all live audio data"""
        self.callbackQueues.append(queue)

    def start(self):
        setproctitle.setproctitle("Repline - AudioDispatcher")
        print("AudioDispatcher starting")
        self.status = {
            recorder.dispatcher_response_soundlevel: None,
            recorder.dispatcher_response_time_remaining: None,
            recorder.dispatcher_response_process_count: 0,
            recorder.dispatcher_response_file_index: 0,
            recorder.dispatcher_response_silence_list: [],
        }
        super().start()

    def run(self):
        # First run, start up the listener
        self.listener = AudioInputListener(self, self.inputQueue, name="AudioInputListener")
        self.listener.start()

        # setproctitle.setproctitle("Repline - {0}".format(self.name))
        while True:

            if self.state == 'idle':
                self.run_idle()
            elif self.state == 'recording':
                self.run_recording()
            elif self.state == 'after_recording':
                self.run_after_recording()

    def run_idle(self):
        # pass
        while self.state == 'idle':
            # (indata, status, log_rms) = self.get_incoming_data()
            (indata, status) = self.inputQueue.get()
            # self.status[recorder.dispatcher_response_soundlevel] = log_rms
            self.recorder_status.send(self.status)
            self.receive_messages()

    def run_recording(self):
        file_number = 0
        last_check = monotonic()

        while self.state == 'recording':
            current_file = self.recorder.temporary_file % file_number
            current_file_start_time = monotonic()
            with sf.SoundFile(
                    current_file,
                    mode='w',
                    samplerate=self.recorder.sample_rate,
                    channels=self.recorder.channels,
                    format='WAV'
            ) as tempFile:
                print("Writing to temporary file: %s" % current_file)
                while self.state == 'recording' and monotonic() < current_file_start_time + (self.recorder.temporary_file_max_length * 60):
                    #(indata, status, log_rms) = self.get_incoming_data()
                    (indata, status) = self.inputQueue.get()
                    if indata is not None:
                        tempFile.write(indata)

                    #     for cb_queue in self.callbackQueues:
                    #         cb_queue.put((indata, status))
                    #     # Once a second, check if any FindSilences jobs have finished and update the status for the recorder
                    #     if last_check + 1 < monotonic():
                    #         last_check = monotonic()
                    #         self.read_from_find_silence_queue()
                    #         self.start_find_silence_process()
                    #         print("There are %d running FindSilence processes, %d silences found by completed processes." % (self.find_silence_process_count, len(self.silences)))
                    #         print("Sending status: index: %s (%s), processes: %s (%s), time remaining: %s (%s)" % (
                    #             file_number,
                    #             type(file_number),
                    #             self.find_silence_process_count,
                    #             type(self.find_silence_process_count),
                    #             self.get_estimated_finish_time(),
                    #             type(self.get_estimated_finish_time())
                    #         ))
                    #         self.recorder_status.send({
                    #             recorder.dispatcher_response_file_index: file_number,
                    #             recorder.dispatcher_response_process_count: self.find_silence_process_count,
                    #             recorder.dispatcher_response_time_remaining: self.get_estimated_finish_time()
                    #         })
                    #         print("Sent update to recorder")
                    #
                    # self.receive_messages()


                # Spawn a FindSilences process to handle this latest file
                # TODO: Only allow cpu_count - 2 to run at once (min. 1)
                self.queued_processes.put(file_number)
                print(">>> Added file %d to the queue, there are now %d queued processes" % (file_number, self.queued_processes.qsize()))
                file_number += 1
                self.receive_messages()

    def run_after_recording(self):
        print("AudioDispatcher: Stopped recording")
        # Now keep updating until all processes have completed
        while self.find_silence_process_count > 0:
            self.start_find_silence_process()
            self.read_from_find_silence_queue()
            print("2 There are %d running FindSilence processes, %d silences found by completed processes." % (self.find_silence_process_count, len(self.silences)))
            print("---")
            print("Sending status: index: %s (%s), processes: %s (%s), time remaining: %s (%s)" % (
                file_number,
                type(file_number),
                self.find_silence_process_count,
                type(self.find_silence_process_count),
                self.get_estimated_finish_time(),
                type(self.get_estimated_finish_time())
            ))
            print("...")
            self.recorder_status.send({
                recorder.dispatcher_response_file_index: file_number,
                recorder.dispatcher_response_process_count: self.find_silence_process_count,
                recorder.dispatcher_response_time_remaining: self.get_estimated_finish_time()
            })
            print("Sent update 2 to recorder, sleeping for 1 second")
            sleep(1)
            self.receive_messages()

        print("AudioDispatcher: Finished track finder")
        self.recorder_status.send({
            recorder.dispatcher_response_file_index: file_number,
            recorder.dispatcher_response_process_count: 0,
            recorder.dispatcher_response_time_remaining: 0
        })

    def get_incoming_data(self):
        log_rms = None
        if not self.inputQueue.empty():
            (indata, status) = self.inputQueue.get()
            # print("AudioDispatcher got data: ", indata)
            if indata is not None and len(indata) > 0:
                linear_rms = numpy.sqrt(numpy.mean(indata**2))
                if linear_rms != 0:
                    log_rms = 20 * math.log10(linear_rms)  # Decibel value, 0dB -> -inf dB
                else:
                    log_rms = -999  # TODO
                # print("RMS: ", log_rms)
        else:
            indata = None
            status = None

        return indata, status, log_rms

    def flush_incoming_data(self):
        while not self.inputQueue.empty():
            self.inputQueue.get_nowait()

    def start_find_silence_process(self):
        """Start queued find silence processes until the maximum number of processes are running"""
        # TODO: Could run an extra process if we've stopped recording
        print("Maybe starting find silence; currently running %d/%d processes, %d queued" % (self.find_silence_process_count, self.max_processes, self.queued_processes.qsize()))
        while not self.queued_processes.empty() and self.find_silence_process_count < self.max_processes:
            file_number = self.queued_processes.get()
            proc = FindSilences(
                file_number,
                self.recorder.temporary_file,
                self.find_silence_queue,
                name="Find Silences #{0}".format(file_number)
            )
            self.find_silence_processes[file_number] = proc
            self.find_silence_process_count += 1
            self.find_silence_running_process_start_time[file_number] = monotonic()
            print("Started process %d from pid %d, start times known:" % (file_number, os.getpid()))
            proc.start()
            print(self.find_silence_running_process_start_time)
            file_number += 1


    def receive_messages(self):
        """Receive incoming messages from the controller pipe"""
        # print("AudioDispatcher - checking for messages")
        if self.recorder_status.poll():
            msg = self.recorder_status.recv()
            print("Recorder received message:", msg)
            if recorder.dispatcher_command_recording in msg:
                if msg[recorder.dispatcher_command_recording]:
                    self.flush_incoming_data()
                    self.state = 'recording'
                else:
                    self.state = 'after_recording'
            if recorder.dispatcher_command_send_silences in msg:
                self.recorder_status.send({
                    recorder.dispatcher_response_silence_list: self.silences
                })

    def check_test_message(self):
        print("Waiting for test message, PID {0}".format(os.getpid()))
        msg = self.recorder_status.recv()
        print("Test message: ", msg)


    def get_processes_started(self):
        return self.find_silence_process_count

    def read_from_find_silence_queue(self):
        """
        Read the next piece of data from the queue and write it to the silences list

        :return: True if data was returned, false if not
        """
        try:
            print("Reading from find silence queue")
            (index, silence_ranges, time) = self.find_silence_queue.get_nowait()
            print("Done")
            self.find_silence_process_complete_time.append(time)
            print("Reading result of process %d from process %d, start times known:" % (index, os.getpid()))
            print(self.find_silence_running_process_start_time)
            del self.find_silence_running_process_start_time[index]

            start_point = index * recorder.temporary_file_max_length * 60 * 1000
            normalised_ranges = [[this_range[0] + start_point, this_range[1] + start_point] for this_range in silence_ranges]
            self.silences.extend(normalised_ranges)

            # Now terminate the process we just read data from
            self.find_silence_processes[index].join()
            del self.find_silence_processes[index]
            self.find_silence_process_count -= 1

        except Empty:
            print ("Nothing to see")
            return False

    def get_estimated_finish_time(self):
        """Get the estimated number of seconds until all running processes complete

        Answer will be 0 if nothing is running, or None if we don't have enough data to estimate.
        This does not consider more queues being added in future, so is only useful after recording stops.

        :return int
        """
        print("get_estimated_finish_time")
        if len(self.find_silence_process_complete_time) == 0:
            print("Nothing to estimate")
            return None

        if len(self.find_silence_running_process_start_time) == 0:
            print("No processes running")
            return 0

        print("OK, let's calculate")
        mean_time = sum(self.find_silence_process_complete_time)/len(self.find_silence_process_complete_time)
        print("Mean time to run: %s" % mean_time)
        now = monotonic()
        print("current time: %s" % now)
        running_time_remaining = max([mean_time - (now - start) for start in self.find_silence_running_process_start_time.values()])
        queued_time_remaining = ceil(self.queued_processes.qsize()/2) * mean_time
        return running_time_remaining + queued_time_remaining

class AudioInputListener(multiprocessing.Process):
    """A thread/process that constantly listens to incoming audio and passes anything it sees to a queue
    This is a small process to keep it as simple as possible because this is the critical point where we can't lose anything"""
    # TODO: Can I get the RMS of each incoming sample? If so I could write an inline silence detection
    dispatcher = None
    queue = None

    def __init__(self, dispatcher, queue, **kwargs):
        print("Hello, I'm an AudioInputListener")
        self.dispatcher = dispatcher
        self.queue = queue
        super().__init__(**kwargs)

    def run(self):
        setproctitle.setproctitle("Repline - {0}".format(self.name))
        print("AudioInputListener: Started recording. Sample rate: {0}, device: {1}, channels: {2}".format(
            self.dispatcher.recorder.sample_rate,
            self.dispatcher.recorder.device,
            self.dispatcher.recorder.channels
        ))
        with sd.InputStream(
            samplerate=self.dispatcher.recorder.sample_rate,
            device=self.dispatcher.recorder.device,
            channels=self.dispatcher.recorder.channels,
            callback=self.callback,
            # TODO: We need to set a blocksize, and a buffer between input & output
            # TODO: See https://python-sounddevice.readthedocs.io/en/0.4.1/examples.html#input-to-output-pass-through
        ):
            while True:
                sleep(1)
                # pass  # TODO: Need IPC to stop recording

        print("AudioInputListener: Stopped recording")

    def callback(self, indata, frames, time, status):
        # print("AudioInputListener got data!")
        # print("RMS: %d " % rms)
        self.queue.put((indata, status))
        if status:
            print(">>", status, os.getpid())

class FindSilences(multiprocessing.Process):
    """Finds all silences in a single temporary file and writes them to a queue

    Queue format: Each temporary file gets a single entry on the queue, in this format:
    (file index, [list, of, silences], time taken in seconds)
    """
    index = None
    audio_segment = None
    queue = None

    def __init__(self, index, temporary_file_path, queue, **kwargs):
        os.setpriority(os.PRIO_PROCESS, 0, 10)
        setproctitle.setproctitle("Repline - {0}".format(kwargs['name']))
        self.index = index
        file = temporary_file_path % index
        print("Created new process looking for silences in %s" % file)
        # Load this segment in mono to speed up silence detection
        self.audio_segment = AudioSegment.from_wav(file).set_channels(1)
        self.queue = queue
        super().__init__(**kwargs)

    def run(self):
        os.nice(1)
        print("Running detect_silence on index %d" % self.index)
        start_time = monotonic()
        silences = detect_silence(self.audio_segment) # TODO: Configurable settings
        end_time = monotonic()
        print("Found %d silences in file %d in %f seconds" % (len(silences), self.index, end_time - start_time))
        self.queue.put((self.index, silences, end_time - start_time))