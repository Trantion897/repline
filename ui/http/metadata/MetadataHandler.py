import http, http.server
import os
import shutil
import socket
import socketserver
import string
import threading
import urllib.parse

from metadata.musicbrainz import MusicBrainz
import json

class MetadataServer():
    BASE_PORT = 8000
    port = None
    httpd = None
    active = False
    server_thread = None

    callbacks = []

    def __init__(self):
        self.server_thread = threading.Thread(target=self.start_server)

    def open(self):
        if not self.active:
            self.port = self.BASE_PORT
            while not self.active:
                try:
                    print("Opening HTTPD")
                    MetadataHandler.callback_handler = self
                    self.httpd = socketserver.TCPServer(("", self.port), MetadataHandler)
                    print("Got socket")
                    # TODO: Separate thread?
                    self.server_thread.start()
                    print("Serving")
                    self.active = True
                    print("Active")
                except OSError:
                    self.port += 1

    def start_server(self):
        self.httpd.serve_forever()

    def close(self):
        if self.server_thread.is_alive():
            self.server_thread.join()
            self.httpd.shutdown()
            self.active = False

    def get_address(self):
        return socket.gethostbyname(socket.gethostname())+":"+str(self.port)

    def add_callback(self, method):
        self.callbacks.append(method)

    def on_callback(self, method, params=None):
        if params == None:
            params = []
        for callback in self.callbacks:
            callback(method, params=params)

class MetadataHandler (http.server.BaseHTTPRequestHandler):
    callback_handler = None

    def do_GET(self):
        path = self.path.split("?")

        if path[0] == "/search":
            self.do_search(path[1])
        elif path[0] == "/metadata.js":
            self.send_file("metadata.js")
        elif path[0] == "/metadata.css":
            self.send_file("metadata.css")
        else:
            self.display_page()

        if self.callback_handler is not None:
            self.callback_handler.on_callback("GET")

    def display_page(self):
        # TODO: Serve the page or media
        page = self.format_html()
        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-type", 'text/html; charset=utf-8')
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Last-Modified", self.date_time_string())
        self.end_headers()
        self.wfile.write(page.encode(encoding='utf_8'))

    def send_file(self, filename):
        source_path = os.path.join("ui/http/metadata/", filename)
        source_file = open(source_path, "rb")
        fs = os.fstat(source_file.fileno())
        self.send_response(http.HTTPStatus.OK)
        (root, ext) = os.path.splitext(source_path)
        if ext == '.js':
            ctype = "text/javascript; charset=utf-8"
        elif ext == '.css':
            ctype = "text/css; charset=utf-8"
        elif ext == '.png':
            ctype = "image/png"
        elif ext == '.jpg' or ext == '.jpeg':
            ctype = "image/jpeg"
        else:
            ctype = "text/plain; charset=utf-8"
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified",
                         self.date_time_string(fs.st_mtime))
        self.end_headers()
        shutil.copyfileobj(source_file, self.wfile)

    def do_search(self, params):
        search = {}
        for param in params.split("&"):
            (key, value) = param.split("=")
            if value == "":
                continue
            if key == "artist":
                search["artist"] = urllib.parse.unquote(value)
            elif key == "release":
                search["release"] = urllib.parse.unquote(value)
            elif key == "date":
                search["date"] = urllib.parse.unquote(value)

        print ("Preparing search: ")
        print(search)
        mb = MusicBrainz()
        result = mb.search(search)
        output = json.dumps(result)
        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-type", 'text/html')
        self.send_header("Content-Length", str(len(output)))
        self.send_header("Last-Modified", self.date_time_string())
        self.end_headers()
        self.wfile.write(output.encode(encoding='utf_8'))

    def format_html(self, albumdata=None, trackdata=None):
        # Load the two template files
        if trackdata is None:
            trackdata = []
        if albumdata is None:
            albumdata = {
                "artist": "",
                "title": "",
                "year": ""
            }
        outer_file = open("ui/http/metadata/metadata.html", "r")
        row_file = open("ui/http/metadata/table_row.html", "r")
        outer_template = string.Template(outer_file.read())
        row_template = string.Template(row_file.read())

        # Generate a row for each track
        tablebody = ""
        tracknumber = 1
        for track in trackdata:
            row = row_template.substitute({
                "tracknumber": tracknumber,
                "trackartist": track['artist'],
                "tracktitle": track['title'],
                "tracklength": track['length']
            })
            tracknumber += 1
            tablebody += row
        # And a blank row for the next track
        row = row_template.substitute({
                "tracknumber": tracknumber,
                "trackartist": "",
                "tracktitle": "",
                "tracklength": ""
            })
        tablebody += row

        # Now the outer template
        html = outer_template.substitute({
            "albumartist": albumdata['artist'],
            "albumtitle": albumdata['title'],
            "albumyear": albumdata['year'],
            "tablebody": tablebody
        })
        return html


    def do_POST(self):
        print("Received POST:")
        content_length = int(self.headers['Content-Length'])
        post = self.rfile.read(content_length).decode("utf-8")
        print (post)

        # TODO: Handle musicbrainz data differently?
        # Handle manual entry
        fields = {urllib.parse.unquote(field[:field.find("=")]) : urllib.parse.unquote(field[field.find("=")+1:]).replace("+", " ") for field in post.split("&")}
        tracks = int(fields["numberOfTracks"])

        audio_metadata = {
            "title": fields["albumtitle"] or "",
            "artist": fields["albumartist"] or "",
            "tracks": [{"number": trackNumber+1} for trackNumber in list(range(tracks))]
        }

        trackFields = [
            "length", "number", "title", "artist"
        ]

        print (audio_metadata)

        for k, v in fields.items():
            # Find the track this field refers to
            if k.find("_") != -1:
                fieldType = k[:k.find("_")]
                trackNumber = int(k[k.find("_")+1])
                print("Field type: %s track number: %s" % (fieldType, trackNumber))
                if fieldType in trackFields:
                    audio_metadata["tracks"][trackNumber-1][fieldType] = v

        print (audio_metadata)

        if self.callback_handler is not None:
            self.callback_handler.on_callback("POST", params=audio_metadata)
