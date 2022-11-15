from dothat import lcd, backlight
from dot3k.menu import MenuIcon

class AbstractUI():
    def display_message(self, message):
        if type(message) == 'str':
            newline_split = message.split("\n")
            # TODO: Maybe auto word-wrapping
            return self.display_message(newline_split)

        if len(message) < 1:
            return

        lcd.set_cursor_position(0, 0)
        lcd.write(message[0])

        if len(message) < 2:
            return

        lcd.set_cursor_position(0, 1)
        lcd.write(message[1])

        if len(message) < 3:
            return

        lcd.set_cursor_position(0, 2)
        lcd.write(message[2])