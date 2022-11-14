import sys
import traceback

from dot3k.menu import MenuOption, MenuIcon
from encoding import encode

# TODO: None of these are being saved?

def bind_buttons():
    print ("Binding buttons: settings.py")



class ReplineMenuOption(MenuOption):
    repline = None
    _icons_setup = False
    text_entry = False
    config_location = []
    value = None

    def __init__(self, repline, config_location=[], **kwargs):
        print ("Init ReplineMenuOption")
        print(config_location)
        self.repline = repline
        self.config_location = config_location
        self.definition = kwargs
        if 'loop' not in self.definition:
            self.definition['loop'] = False
        # self.bind_buttons()

        super().__init__()

    def up(self):
        print("ReplineMenuOption.up")
        self.reset_to_default()

    def down(self):
        print("ReplineMenuOption.down")
        self.reset_to_default()

    def select(self):
        print("ReplineMenuOption.select")
        self.save()
        return True # Must return true to go back to previous menu

    def reset_to_default(self):
        # Restore to default value and save to config
        print("Restoring default for %s" % self.__class__)
        self.value = self.repline.config.set_default(self.config_location)

    def setup_icons(self, menu):
        menu.lcd.create_char(0, MenuIcon.arrow_left_right)
        menu.lcd.create_char(1, MenuIcon.arrow_up_down)
        menu.lcd.create_char(2, MenuIcon.arrow_left)
        self._icons_setup = True

    def begin(self):
        print("Begin!")
        self.reset()
        super().begin()


class DictionarySetting(ReplineMenuOption):
    pointer = 0

    def right(self):
        print("DictionarySetting.right")
        if self.pointer < len(self.definition['options']) - 1:
            self.pointer += 1
        elif self.definition['loop']:
            self.pointer = 0
        return True

    def left(self):
        print("DictionarySetting.left")
        if self.pointer > 0:
            self.pointer -= 1
        elif self.definition['loop']:
            self.pointer = len(self.definition['options']) - 1
        return True

    def reset_to_default(self):
        super().reset_to_default()
        if self.value is not None and self.value in self.definition['options']:
            self.pointer = list(self.definition['options']).index(self.value)

    def reset(self):
        # Load current value from config
        print("Resetting %s" % self.__class__)
        value = self.repline.config.get(self.config_location)
        print(value)
        print(self.definition['options'])
        if value is not None and value in self.definition['options']:
            self.pointer = list(self.definition['options']).index(value)
        else:
            self.reset_to_default()

    def save(self):
        value = self.get_value()
        self.repline.config.set(self.config_location, value)
        self.repline.config.save()
        print("Value saved as {0}".format(self.repline.config.get(self.config_location)))

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        value = self.get_value()
        display_value = self.get_display_value(value)
        help_text = self.get_help(value)
        if 'title' in self.definition:
            menu.write_row(0, self.definition['title'])
        else:
            menu.write_row(0, self.config_location[1].capitalize().replace("_", " "))
        menu.write_row(1, "{0}{1}{2}{3}".format(
            chr(0),
            self.definition['prefix'] if 'prefix' in self.definition else '',
            display_value,
            self.definition['suffix'] if 'suffix' in self.definition else '',
        ))
        if help_text is None:
            menu.write_row(2, "{0}Reset {1}OK {2}Back".format(chr(1), "+", chr(251)))
        else:
            menu.write_row(2, help_text)

    def get_value(self, pointer=None):
        if pointer is None:
            pointer = self.pointer
        return list(self.definition['options'])[pointer]

    def get_display_value(self, value=None, pointer=None):
        if value is None:
            value = self.get_value(pointer)
        return self.definition['options'][value]

    def get_help(self, value=None, pointer=None):
        if value is None:
            value = self.get_value(pointer)
        if 'help' in self.definition and value in self.definition['help']:
            return self.definition['help'][value]
        else:
            return None


class NumericSetting(ReplineMenuOption):
    max = 0
    min = 0
    default = 0
    loop = False
    value = 0

    def __init__(self, repline, **kwargs):
        self._icons_setup = False
        super().__init__(repline, **kwargs)
        if 'step' not in self.definition:
            self.definition['step'] = 1

    def right(self):
        self.value += self.definition['step']
        if self.value > self.definition['max']:
            if self.definition['loop']:
                self.value = self.definition['min']
            else:
                self.value = self.definition['max']
        return True

    def left(self):
        self.value -= self.definition['step']
        if self.value < self.definition['min']:
            if self.definition['loop']:
                self.value = self.definition['max']
            else:
                self.value = self.definition['min']
        return True

    def reset(self):
        # Load current value from config
        print ("Resetting %s" % self.__class__)
        value = self.repline.config.get(self.config_location)
        if value is None:
            print("No value for {0} in config".format(self.config_location))
            self.reset_to_default()
        elif value.lstrip('-').isdigit():
            self.value = int(value)
        else:
            print("Invalid value for {0} in config: {1}".format(
                ".".join(self.config_location),
                self.repline.config.get(self.config_location)
            ))

    def cleanup(self):
        self._icons_setup = False

    def save(self):
        self.repline.config.set(self.config_location, self.value)
        self.repline.config.save()
        print("Value saved as %s" % self.repline.config.get(self.config_location))

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        if 'title' in self.definition:
            menu.write_row(0, self.definition['title'])
        else:
            menu.write_row(0, self.config_location[1].capitalize().replace("_", " "))
        menu.write_row(1, "{0}{1}{2}{3}".format(
            chr(0),
            self.definition['prefix'] if 'prefix' in self.definition else '',
            self.value,
            self.definition['suffix'] if 'suffix' in self.definition else ''
        ))
        menu.write_row(2, "%sReset %sOK %sBack" % (chr(1), "+", chr(251)))


class LabelledNumericSetting(NumericSetting):
    options = []
    def __init__(self, repline, **kwargs):
        super().__init__(self, repline, **kwargs)
        self.min = 0
        self.max = len(self.options)-1
        self.reset()

    def redraw(self, menu):
        if not self._icons_setup:
            self.setup_icons(menu)

        if 'title' in self.definition:
            menu.write_row(0, self.definition['title'])
        else:
            menu.write_row(0, self.config_location[1].capitalize().replace("_", " "))
        menu.write_row(1, "{0}{1}{2}{3}".format(
            chr(0),
            self.definition['prefix'] if 'prefix' in self.definition else '',
            self.definition['options'][self.value],
            self.definition['suffix'] if 'suffix' in self.definition else ''
        ))
        menu.write_row(2, "%sReset %sOK %sBack" % (chr(1), "+", chr(251)))

class DummySetting(MenuOption):
    value = ""

    def redraw(self, menu):
        if 'title' in self.definition:
            menu.write_row(0, self.definition['title'])
        else:
            menu.write_row(0, self.config_location[1].capitalize().replace("_", " "))
        menu.write_row(1, "%s" % (self.value))
        menu.clear_row(2)

# TODO: Reimplement this with the new system so you only get to set quality for the format you're currently using
# def get_quality_setting(repline):
#     """Get the correct quality setting class for the current format"""
#     format = repline.config.get("encoding", "output_format")
#     if format == encode.format_MP3:
#         return Mp3QualitySetting
#     elif format == encode.format_FLAC:
#         return FlacQualitySetting
#     elif format == encode.format_WAV:
#         return WavQualitySetting
#     elif format == encode.format_AAC:
#         return AacQualitySetting
#     elif format == encode.format_VORBIS:
#         return VorbisQualitySetting

# class SaveLocation()


class SetInputDevice(DictionarySetting):
    value = None

    # def begin(self):
    #     """Get available devices"""
    #     devices = self.repline.recorder.get_input_devices()
    #     options = {d['name']:d['name'] for d in devices}

    def reset_to_default(self):
        self.value = self.repline.recorder.get_default_input_device()
        self.save()
        self.reset()

    def begin(self):
        devices = self.repline.recorder.get_input_devices()
        self.definition['options'] = {d['name']: d['name'] for d in devices if d['max_input_channels'] > 0}
        super().begin()


class SetOutputDevice(DictionarySetting):
    value = None

    def begin(self):
        devices = self.repline.recorder.get_audio_devices()
        self.definition['options'] = {d['name']: d['name'] for d in devices if d['max_output_channels'] > 0}
        super().begin()

    def reset_to_default(self):
        self.value = self.repline.recorder.get_default_output_device()
        self.save()
        self.reset()

