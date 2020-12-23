import tkinter as tk
from .MainButtons import MainButtons
from .Visualisation import Visualisation

class Application(tk.Toplevel):
    def __init__(self, repline, master=None):
        """
        Initialise the application window
        :param repline: Master repline application class
        :param master:
        """
        super().__init__(master)
        self.repline = repline
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        self.infoDisplay = tk.Text(self)
        self.infoDisplay.pack(side="top")
        self.visualisation = Visualisation(self)
        self.visualisation.pack(side="top")
        self.buttons = MainButtons(self)
        self.buttons.pack(side="top")

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.pack(side="bottom")

def open_ui(repline):
    root = tk.Tk()
    app = Application(repline, root)
    app.mainloop()
    app.destroy()