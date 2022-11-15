import tkinter as tk
import math
import numpy
import random
from queue import Queue, Empty
from time import sleep
import threading

class Visualisation(tk.Canvas):
    width = 300
    height = 100
    minFreq = 100
    maxFreq = 4000
    updateTime = 0.02

    def __init__(self, master):
        super().__init__(master, width=self.width, height=self.height)
        self.master = master
        self.updateThread = threading.Thread(target=self.update, daemon=True)
        self.queue = Queue()
        self.is_running = False
        self.delta_f = (self.maxFreq - self.minFreq) / (self.width)
        self.fftsize = math.ceil(self.sampleRate / self.delta_f)
        self.gradient = []
        self.low_bin = math.floor(self.minFreq / self.delta_f)
        self.create_rectangle(0, 0, self.width, self.height, fill="black")
        self.lines = [self.create_line(i, 0, random.randint(0, self.height), 0, fill="white") for i in range(self.width)]
        self.sample_rate = self.master.repline.config.get(['recording', 'sample_rate'])
        colors = 30, 34, 35, 91, 93, 97
        chars = ' :%#\t#%:'
        for bg, fg in zip(colors, colors[1:]):
            for char in chars:
                if char == '\t':
                    bg, fg = fg, bg
                else:
                    self.gradient.append('\x1b[{};{}m{}'.format(fg, bg + 10, char))
        self.connect()

    def connect(self):
        """Empty the queue and connect to the recorder, with a separate thread monitoring for updates"""
        self.queue.empty()
        self.is_running = True
        self.master.repline.register_callback_queue("recorder", self.queue)
        self.updateThread.start()

    def stop(self):
        (self.coords(self.lines[i], i, self.height/2, i, self.height/2) for i in range(self.width))

    def update(self):
        while True:
            got_data = False
            try:
                (indata, status) = self.queue.get_nowait()
                got_data = True
            except Empty:
                pass
            if got_data and self.is_running:
                if status:
                    print (status)
                else:
                    magnitude = numpy.abs(numpy.fft.rfft(indata[:, 0], n=self.fftsize))
                    magnitude *= 200/self.fftsize
                    centre = self.height/2
                    amplitude = [int(numpy.clip(x, 0, 1) * centre - 1) for x in magnitude[self.low_bin : self.low_bin + self.width]]
                    for i in range(self.width):
                        self.coords(self.lines[i], i, centre+amplitude[i], i, centre-amplitude[i])
            sleep(self.updateTime)