import audioop
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
        self.dispatcher_status, dispatcher_end = multiprocessing.Pipe()
        self.dispatcher = AudioDispatcher(self, dispatcher_end, name='Audio Dispatcher')
        self.last_status = {}
        self.temporary_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.temporary_file)
        self.repline = repline

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
        self.dispatcher.start()

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
        while self.dispatcher_status.poll():
            print("getting status")
            try:
                new_status = self.dispatcher_status.recv()
                if self.dispatcher_response_silence_list in new_status:
                    self.silences = new_status[self.dispatcher_response_silence_list]
                self.last_status.update(new_status)
            except UnpicklingError:
                print("Unpickling error")
                pass

    def get_dispatcher_status(self):
        print("Returning status:")
        print(self.last_status)
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
    # Queue from AudioDispatcher -> FindSilences (send audio for scanning)
    processingQueue = None
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

    is_recording = True

    max_processes = 1
    queued_processes = None

    def __init__(self, recorder, recorder_status, **kwargs):
        setproctitle.setproctitle("Repline - AudioDispatcher")
        self.recorder = recorder
        self.recorder_status = recorder_status
        self.inputQueue = Queue()
        self.processingQueue = Queue()
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

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.inputQueue.put_nowait((indata.copy(), status))

    def run(self):
        print("Recorder running")
        # TODO: Lots of these AILs are spawning. We should only ever have one. Maybe because we have multiple main processes?
        if self.listener is None:
            print("Spawning AIL")
            self.listener = AudioInputListener(self, self.inputQueue, name="AudioInputListener")
            self.listener.start()
        file_number = 0
        last_check = monotonic()

        self.recorder_status.send({
            recorder.dispatcher_response_file_index: file_number,
            recorder.dispatcher_response_process_count: 0,
            recorder.dispatcher_response_time_remaining: None
        })

        while self.is_recording:
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
                while self.is_recording and monotonic() < current_file_start_time + (self.recorder.temporary_file_max_length * 60):
                    (indata, status) = self.inputQueue.get()
                    tempFile.write(indata)
                    self.processingQueue.put(indata)

                    for queue in self.callbackQueues:
                        queue.put((indata, status))
                    self.receive_messages()
                    # Once a second, check if any FindSilences jobs have finished and update the status for the recorder
                    if last_check + 1 < monotonic():
                        last_check = monotonic()
                        self.read_from_find_silence_queue()
                        self.start_find_silence_process()
                        print("There are %d running FindSilence processes, %d silences found by completed processes." % (self.find_silence_process_count, len(self.silences)))
                        print("Sending status: index: %s (%s), processes: %s (%s), time remaining: %s (%s)" % (
                            file_number,
                            type(file_number),
                            self.find_silence_process_count,
                            type(self.find_silence_process_count),
                            self.get_estimated_finish_time(),
                            type(self.get_estimated_finish_time())
                        ))
                        self.recorder_status.send({
                            recorder.dispatcher_response_file_index: file_number,
                            recorder.dispatcher_response_process_count: self.find_silence_process_count,
                            recorder.dispatcher_response_time_remaining: self.get_estimated_finish_time()
                        })
                        print("Sent update to recorder")
            # Spawn a FindSilences process to handle this latest file
            # TODO: Only allow cpu_count - 2 to run at once (min. 1)
            self.queued_processes.put(file_number)
            print(">>> Added file %d to the queue, there are now %d queued processes" % (file_number, self.queued_processes.qsize()))
            file_number += 1

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

        print("AudioDispatcher: Finished track finder")
        self.recorder_status.send({
            recorder.dispatcher_response_file_index: file_number,
            recorder.dispatcher_response_process_count: 0,
            recorder.dispatcher_response_time_remaining: 0
        })

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
        while self.recorder_status.poll():
            msg = self.recorder_status.recv()
            if recorder.dispatcher_command_recording in msg:
                self.is_recording = msg[recorder.dispatcher_command_recording]
            if recorder.dispatcher_command_send_silences in msg:
                self.recorder_status.send({
                    recorder.dispatcher_response_silence_list: self.silences
                })


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
        print("Hello, I'm an AIL")
        setproctitle.setproctitle("Repline - {0}".format(kwargs['name']))
        self.dispatcher = dispatcher
        self.queue = queue
        super().__init__(**kwargs)

    def run(self):
        print("AIL: Started recording")
        with sd.InputStream(
                samplerate=self.dispatcher.recorder.sample_rate,
                device=self.dispatcher.recorder.device,
                channels=self.dispatcher.recorder.channels,
                callback=self.callback
        ):
            while self.dispatcher.recorder.is_recording:
                sd.sleep(100)

        print("AudioInputListener: Stopped recording")

    def callback(self, indata, frames, time, status):
        rms = numpy.sqrt(numpy.mean(numpy.square(indata)))
        # print("RMS: %d " % rms)
        self.queue.put((indata.copy(), status))
        if status:
            print(status)

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