from dot3k.menu import Menu, MenuOption, MenuIcon
from encoding import encode

# TODO: None of these are being saved?

class NumericSetting(MenuOption):
    title = "Numeric setting"
    prefix = ""
    suffix = ""
    max = 0
    min = 0
    default = 0
    step = 1
    config_group = ""
    config_item = ""
    loop = False

    def __init__(self, repline):
        self.repline = repline
        self._icons_setup = False
        MenuOption.__init__(self)

    def right(self):
        self.value += self.step
        if self.value > self.max:
            if self.loop:
                self.value = self.min
            else:
                self.value = self.max
        self.save()
        return True

    def left(self):
        self.value -= self.step
        if self.value < self.min:
            if self.loop:
                self.value = self.max
            else:
                self.value = self.min
        self.save()
        return True

    def select(self):
        self.reset()
        return False

    def reset(self):
        print ("Resetting %s" % self.__class__)
        self.repline.config.set_default(self.config_group, self.config_item)
        self.value = int(self.repline.config.get(self.config_group, self.config_item))

    def setup_icons(self, menu):
        menu.lcd.create_char(0, MenuIcon.arrow_left_right)
        menu.lcd.create_char(1, MenuIcon.arrow_up_down)
        menu.lcd.create_char(2, MenuIcon.arrow_left)
        self._icons_setup = True

    def cleanup(self):
        self._icons_setup = False

    def setup(self, config):
        self.config = config
        self.reset()

    def save(self):
        self.repline.config.set(self.config_group, self.config_item, self.value)
        self.repline.config.save()

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        menu.write_row(0, self.title)
        menu.write_row(1, "%s%s%s%s" % (chr(0), self.prefix, self.value, self.suffix))
        menu.clear_row(2)

class LabelledNumericSetting(NumericSetting):
    options = []
    def __init__(self, repline):
        NumericSetting.__init__(self, repline)
        self.min = 0
        self.max = len(self.options)-1
        self.reset()

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        menu.write_row(0, self.title)
        menu.write_row(1, "%s%s%s%s" % (chr(0), self.prefix, self.options[self.value], self.suffix))
        menu.clear_row(2)

class SelectSetting(LabelledNumericSetting):
    title = "Select setting"
    prefix = ""
    suffix = ""
    options = []
    labels = {}
    config_group = ""
    config_item = ""

    def __init__(self, repline):
        NumericSetting.__init__(self, repline)
        self.min = 0
        self.max = len(self.options)-1

    def setup(self, config):
        self.config = config
        self.reset()

    def select(self):
        self.repline.config.set_default(self.config_group, self.config_item)
        self.reset()
        return False

    def reset(self):
        self.value = self.options.index(self.repline.config.get(self.config_group, self.config_item))

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        menu.write_row(0, self.title)
        menu.write_row(1, "%s%s%s%s" % (chr(0), self.prefix, self.labels[self.options[self.value]], self.suffix))
        menu.clear_row(2)

class DummySetting(MenuOption):
    title = "Dummy setting"
    value = ""

    def redraw(self, menu):
        menu.write_row(0, self.title)
        menu.write_row(1, "%s" % (self.value))
        menu.clear_row(2)

class Normalisation(LabelledNumericSetting):
    options = ["None", "Per album", "Per track"]
    title = 'Normalisation'
    config_group = "recording"
    config_item = "normalisation"
    loop = True

class SilenceThreshold(NumericSetting):
    title = "Silence level"
    min = -100
    default = -16
    max = 0
    suffix = "dB"
    config_group = "trackDetection"
    config_item = "silenceThreshold"

class MinSilenceLength(NumericSetting):
    title = "Minimum silence"
    min = 100
    max = 10000
    default = 1000
    step = 100
    suffix = "ms"
    config_group = "trackDetection"
    config_item = "minSilenceLength"

class OutputFormat(SelectSetting):
    title = "Output format"
    options = [
        encode.format_WAV,
        encode.format_FLAC,
        encode.format_MP3,
        encode.format_VORBIS,
        encode.format_AAC
    ]
    labels = {
        encode.format_WAV: "WAV",
        encode.format_FLAC: "FLAC",
        encode.format_MP3: "MP3",
        encode.format_VORBIS: "Ogg Vorbis",
        encode.format_AAC: "AAC"
    }
    helpText = {
        encode.format_WAV: "Uncompressed",
        encode.format_FLAC: "Lossless",
        encode.format_MP3: "Lossy, v. common",
        encode.format_VORBIS: "Lossy, free",
        encode.format_AAC: "Lossy, modern"
    }
    config_group = "encoding"
    config_item = "outputFormat"
    loop = True

    def redraw(self, menu):
        super().redraw(menu)
        menu.write_row(2, self.helpText[self.options[self.value]])

def get_quality_setting(repline):
    """Get the correct quality setting class for the current format"""
    format = repline.config.get("encoding", "outputFormat")
    if format == encode.format_MP3:
        return Mp3QualitySetting
    elif format == encode.format_FLAC:
        return FlacQualitySetting
    elif format == encode.format_WAV:
        return WavQualitySetting
    elif format == encode.format_AAC:
        return AacQualitySetting
    elif format == encode.format_VORBIS:
        return VorbisQualitySetting

class Mp3QualitySetting(SelectSetting):
    title = "MP3 Quality"
    options = [
        "q:a 9",
        "q:a 8",
        "q:a 7",
        "q:a 6",
        "q:a 5",
        "q:a 4",
        "q:a 3",
        "q:a 2",
        "q:a 1",
        "q:a 0",
        "b:a 320k",
    ],
    labels = {
        "q:a 9": "Worst",
        "q:a 8": "-4",
        "q:a 7": "-3",
        "q:a 6": "-2",
        "q:a 2": "+2",
        "q:a 5": "-1",
        "q:a 4": "Medium",
        "q:a 3": "+1",
        "q:a 1": "+3",
        "q:a 0": "+4",
        "b:a 320k": "Best",
    }
    config_group = "encoding_mp3"
    config_item = "bitrate"

class AacQualitySetting(SelectSetting):
    title = "AAC Quality"
    # TODO: Fix bitrates
    options = [
        "b:a 320k",
        "b:a 0",
        "b:a 1",
        "b:a 2",
        "b:a 3",
        "b:a 4",
        "b:a 5",
        "b:a 6",
        "b:a 7",
        "b:a 8",
        "b:a 9",
              ],
    labels = {
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
    config_group = "encoding_aac"
    config_item = "bitrate"

class VorbisQualitySetting(Mp3QualitySetting):
    title = "Vorbis Quality"
    config_group = "encoding_oggvorbis"
    config_item = "bitrate"

class WavQualitySetting(DummySetting):
    title = "WAV Quality"
    value = "Perfect"

class FlacQualitySetting(DummySetting):
    title = "FLAC Quality"
    value = "Perfect"

# class SaveLocation()


class SetInputDevice(LabelledNumericSetting):
    title = "Input device"
    config_group = "hardware"
    config_item = "inputDevice"

    def __init__(self, repline):
        devices = repline.recorder.get_audio_devices()
        for elem in devices:
            print (elem)
        self.options = [elem['name'] for elem in devices]
        super().__init__(repline)

    def reset(self):
        self.value = self.repline.recorder.get_default_input_device()

    def left(self):
        print ("Moving left from %s (min: %s, max: %s)" % (self.value, self.min, self.max))
        r = super().left()
        print("New value is %s" % self.value)
        return r

    def right(self):
        print ("Moving right from %s (min: %s, max: %s)" % (self.value, self.min, self.max))
        r = super().right()
        print("New value is %s" % self.value)
        return r

    def cancel(self):
        print("CANCEL")

class SetOutputDevice(LabelledNumericSetting):
    title = "Output device"
    config_group = "hardware"
    config_item = "outputDevice"

    def __init__(self, repline):
        devices = repline.recorder.get_audio_devices()
        self.options = [elem['name'] for elem in devices]
        super().__init__(repline)

    def reset(self):
        self.value = self.repline.recorder.get_default_input_device()

    def cancel(self):
        print("CANCEL")
