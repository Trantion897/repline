"""Encode files using pydub

Supports lots of formats, but requires ffmpeg to be installed."""

from pydub import AudioSegment

format_WAV = "WAV"
format_FLAC = "FLAC"
format_MP3 = "MP3"
format_VORBIS = "Vorbis"
format_AAC = "AAC"

"""
Convert a temporary WAV file to a specified output format

:param tempFile Path to the temporary file
:param start Time to start encoding from in milliseconds (if not specified, encode from start)
:param end Time to end encoding in milliseconds (if not specified, encode to end)
:param duration Length of sample to encode (only if end is not specified)
:param outFile Path to the output file
:param format Output format
"""
def convert(tempFile, start, end, duration, outFile, format):
    # TODO: Need to specify codec, bitrate, tags...
    if (duration and not end):
        end = start + duration
    sound = AudioSegment.from_wav(tempFile)
    if (start and end):
        sound = sound[start:end]
    elif (start):
        sound = sound[start:]
    sound.export(outFile, format=format)