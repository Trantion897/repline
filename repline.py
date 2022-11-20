import recorder
from queue import Queue
from encoding import encode
import configparser
import os
import setproctitle

from ui.displayotronhat import settings


class repline():
    def __init__(self):
        self.config = Settings()
        self.recorder = recorder.recorder(self)
        setproctitle.setproctitle("Repline - main")

    def open_ui(self):
        #from ui.tk import Application
        #Application.open_ui(self)
        from ui.displayotronhat import ui
        ui.open_ui(self)
        # from ui.displayotronhat import record
        # record.open_ui(self)

    def record(self):
        """Start recording"""
        self.recorder.record()

    def stop(self):
        """Stop recording"""
        self.recorder.stop()

    def register_callback_queue(self, moduleName, queue: Queue):
        print("module in self: {}".format(hasattr(self, moduleName)))
        if (hasattr(self, moduleName)):
            module = getattr(self, moduleName)
            print("register_callback: {}".format(hasattr(module, "register_callback")))
            if (hasattr(module, "register_callback_queue")):
                module.register_callback_queue(queue)

class Settings():
    config = configparser.ConfigParser()
    options = {
        "recording": {
            "sample_rate": {
                "class": settings.DictionarySetting,
                "options": {
                    22050: "22050Hz",
                    44100: "44100Hz",
                    48000: "48000Hz",
                    88200: "88200Hz",
                    96000: "96000Hz",
                },
                "help": {
                    22050: "Half CD quality",
                    44100: "CD quality",
                    48000: "Also common",
                    88200: "Hi-res standard",
                    96000: "Studio quality",
                },
                "default": 44100,
            },
            "max_channels": {
                "class": settings.DictionarySetting,
                "options": {
                    1: "Mono",
                    2: "Stereo",
                    99: "Device maximum"
                },
                "default": 99
            },
            "normalisation": {
                "class": settings.DictionarySetting,
                "options": {"none": "None", "album": "Per album", "track": "Per track"},
                "default": "none",
            },
        },
        "track_detection": {
            "silence_threshold": {
                "class": settings.NumericSetting,
                "min": -100,
                "max": 0,
                "default": -16,
                "suffix": "dB"
            },
            "min_silence_length": {
                "class": settings.NumericSetting,
                "min": 100,
                "max": 10000,
                "step": 100,
                "default": 1000,
                "suffix": "ms"
            }
        },
        "encoding": {
            "output_format": {
                "class": settings.DictionarySetting,
                "options": {
                    encode.format_WAV: "WAV",
                    encode.format_FLAC: "FLAC",
                    encode.format_MP3: "MP3",
                    encode.format_VORBIS: "Ogg Vorbis",
                    encode.format_AAC: "AAC"
                },
                "help": {
                    encode.format_WAV: "Uncompressed",
                    encode.format_FLAC: "Lossless",
                    encode.format_MP3: "Lossy, v. common",
                    encode.format_VORBIS: "Lossy, free",
                    encode.format_AAC: "Lossy, modern"
                },
                "loop": True,
                "default": encode.format_WAV
            },
            "mp3_quality": {
                "class": settings.DictionarySetting,
                "options": {
                    "q:a 9": "Worst",
                    "q:a 8": "-4",
                    "q:a 7": "-3",
                    "q:a 6": "-2",
                    "q:a 5": "+2",
                    "q:a 4": "-1",
                    "q:a 3": "Medium",
                    "q:a 2": "+1",
                    "q:a 1": "+3",
                    "q:a 0": "+4",
                    "b:a 320k": "Best",
                },
                "default": "q:a 3"
            },
            "vorbis_quality": {
                "class": settings.DictionarySetting,
                "options": {
                    "q:a 9": "Worst",
                    "q:a 8": "-4",
                    "q:a 7": "-3",
                    "q:a 6": "-2",
                    "q:a 5": "+2",
                    "q:a 4": "-1",
                    "q:a 3": "Medium",
                    "q:a 2": "+1",
                    "q:a 1": "+3",
                    "q:a 0": "+4",
                    "b:a 320k": "Best",
                },
                "default": "q:a 3"
            },
            "aac_quality": {
                "class": settings.DictionarySetting,
                # TODO: Fix bitrates
                "options": {
                    "b:a 320k": "Best",
                    "b:a 0": "+4",
                    "b:a 1": "+3",
                    "b:a 2": "+2",
                    "b:a 3": "+1",
                    "b:a 4": "Medium",
                    "b:a 5": "-1",
                    "b:a 6": "-2",
                    "b:a 7": "-3",
                    "b:a 8": "-4",
                    "b:a 9": "Worst",
                }
            },
        },
        "hardware": {
            "input_device": {
                "class": settings.SetInputDevice
            },
            "output_device": {
                "class": settings.SetOutputDevice
            }
        }
    }

    config_file = 'repline.ini'

    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.config_file)
        self.read()


    # TODO: Setting location is now passed as a list
    def get(self, setting):
        print("Getting current value of {0}".format(".".join(setting)))

        if not setting[0] in self.config:
            self.config[setting[0]] = {}

        if not setting[1] in self.config[setting[0]]:
            self.set_default(setting)

        return self.config[setting[0]][setting[1]]

    def set_default(self, setting):
        value = self.get_default(setting)
        self.config[setting[0]][setting[1]] = str(value)
        return value

    def get_default(self, setting):
        print("Getting default for {0}".format(".".join(setting)))
        if setting[0] not in self.options or setting[1] not in self.options[setting[0]]:
            raise KeyError("No definition for {0} found".format(".".join(setting)))
        elif "default" in self.options[setting[0]][setting[1]]:
            default = self.options[setting[0]][setting[1]]['default']
            print("Default is {0}".format(default))
            return default
        else:
            return None

    def set(self, setting, value):
        print("Setting current value of {0} to {1}".format(".".join(setting), value))

        if not setting[0] in self.config:
            self.config[setting[0]] = {}

        if not setting[1] in self.config[setting[0]]:
            self.set_default(setting)

        self.config[setting[0]][setting[1]] = str(value)

    def save(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def read(self):
        if os.path.isfile(self.config_file):
            print("Reading config file {0}".format(self.config_file))
            self.config.read(self.config_file)
            print(self.config.sections())
        else:
            print("Config file {0} does not exist".format(self.config_file))

if __name__ == "__main__":
    repline = repline()
    repline.open_ui()
