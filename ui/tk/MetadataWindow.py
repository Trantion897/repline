import tkinter as tk
import metadata.musicbrainz

class MetadataWindow(tk.Toplevel):
    currentSearchResults = []

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.create_widgets()
        self.musicBrainz = metadata.musicbrainz.MusicBrainz()

    def create_widgets(self):
        self.listBox = tk.Listbox(self, selectmode=tk.SINGLE, width=100)

        self.barcodeRow = tk.Frame(self)
        self.barcodeLabel = tk.Label(self.barcodeRow, text="Barcode")
        self.barcodeField = tk.Entry(self.barcodeRow)
        self.barcodeButton = tk.Button(self.barcodeRow, text="Search", command=self.doBarcodeSearch)
        self.barcodeLabel.pack(side="left")
        self.barcodeField.pack(side="left")
        self.barcodeButton.pack(side="right")

        self.searchGroup = tk.LabelFrame(self, text="Manual search")

        self.artistRow = tk.Frame(self.searchGroup)
        self.artistLabel = tk.Label(self.artistRow, text="Artist")
        self.artistField = tk.Entry(self.artistRow)
        self.artistLabel.pack(side="left")
        self.artistField.pack(side="left")

        self.titleRow = tk.Frame(self.searchGroup)
        self.titleLabel = tk.Label(self.titleRow, text="Album title")
        self.titleField = tk.Entry(self.titleRow)
        self.titleLabel.pack(side="left")
        self.titleField.pack(side="left")

        self.yearRow = tk.Frame(self.searchGroup)
        self.yearLabel = tk.Label(self.yearRow, text="Release year")
        self.yearField = tk.Entry(self.yearRow)
        self.yearLabel.pack(side="left")
        self.yearField.pack(side="left")

        self.searchButtonRow = tk.Frame(self.searchGroup)
        self.searchButton = tk.Button(self.searchButtonRow, text="Search", command=self.doManualSearch)
        self.searchButton.pack(side="right")

        self.artistRow.pack(side="top")
        self.titleRow.pack(side="top")
        self.yearRow.pack(side="top")
        self.searchButtonRow.pack(side="bottom")

        self.buttonRow = tk.Frame(self)
        self.cancelButton = tk.Button(self.buttonRow, text="Cancel")
        self.saveButton = tk.Button(self.buttonRow, text="Save", command=self.doSave)
        self.cancelButton.pack(side="left")
        self.saveButton.pack(side="right")

        self.listBox.pack(side="top")
        self.barcodeRow.pack(side="top")
        self.searchGroup.pack(side="top")
        self.buttonRow.pack(side="bottom")

    def doBarcodeSearch(self):
        self.showRecordingSelection(self.musicBrainz.searchByBarcode(self.barcodeField.get()))

    def doManualSearch(self):
        print("Do manual search: "+ self.artistField.get()+" - "+ self.titleField.get() + " ("+self.yearField.get()+")")

    def showRecordingSelection(self, result):
        self.listBox.delete(0, tk.END)
        if (result["release-count"] == 0):
            self.listBox.insert(0, "-- No results found --")
            self.currentSearchResults = []
        else:
            self.currentSearchResults = result["release-list"]
            for release in result["release-list"]:
                self.listBox.insert(tk.END, "{artist} - {album} ({year}, {country})".format(
                    artist=release["artist-credit-phrase"],
                    album=release["title"],
                    year=release["date"],
                    country=release["country"]
                ))

    def doSave(self):
        if (len(self.currentSearchResults) > 0 and len(self.listBox.curselection()) > 0):
            selectionIndex = self.listBox.curselection()[0]
            release = self.currentSearchResults[selectionIndex]
            print("Selected album: {artist} - {album} ({year}, {country})".format(
                artist=release["artist-credit-phrase"],
                album=release["title"],
                year=release["date"],
                country=release["country"]
            ))
        else:
            print ("Nothing selected")
        self.master.destroy()