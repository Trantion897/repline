import musicbrainzngs as mb

class MusicBrainz():
    selectedRecording = {}
    
    def __init__(self):
        mb.set_useragent("repline", "dev", "https://github.com/PeterCopeland/repline")

    def searchByBarcode(self, barcode):
        return mb.search_releases(barcode=barcode)

    def search(self, params):
        print("Searching Musicbrainz with: ")
        print(params)
        result = mb.search_releases(params)
        print("Result: ")
        print (result)
        return result
