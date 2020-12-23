import tkinter as tk
from .MetadataWindow import MetadataWindow

class MainButtons(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        self.record = tk.Button(self, text="Record", command=self.master.repline.record)
        self.mark = tk.Button(self, text="Mark", command=self.doMark)
        self.stop = tk.Button(self, text="Stop", command=self.master.repline.stop)
        self.metadata = tk.Button(self, text="Metadata", command=self.doMetadata)

        self.record.pack(side="left")
        self.mark.pack(side="left")
        self.stop.pack(side="left")
        self.metadata.pack(side="left")

    def doMark(self):
        print("Mark")

    def doStop(self):
        print("Stop")

    def doMetadata(self):
        metadataWindow = MetadataWindow()
