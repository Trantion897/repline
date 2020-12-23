from multiprocessing import Pool

from pydub import AudioSegment
from pydub.silence import *
from math import floor
from itertools import chain

def detect_nonsilent_wrapper(audio_segment):
    # TODO: Configurable
    detect_nonsilent(audio_segment, 1000, -16, 1)

class TrackLayout():
    """If we can't find a split near an expected track boundary, apply this penalty.
    This means it will search up to that many seconds for a nearby silence.
    The purpose is to cope with albums where one track runs into another."""

    # Penalty added to any track layout that skips an expected track boundary
    # This allows it to cope with albums where one track runs into the next without silence,
    # without encouraging a boundary to be missed if it's a few seconds out of expected alignment
    missed_split_penalty = 10

    audio_segment = None
    audio_metadata = None
    tracks = None
    defaultSplit = None
    split = None
    first_track = None

    # List of detected silences
    silences = []

    def read_file(self, file):
        """Load a WAV file into memory

        :param file string /path/to/file
        """
        self.audio_segment = AudioSegment.from_wav(file)

    def set_metadata(self, metadata):
        self.audio_metadata = metadata

    def set_silences(self, silences):
        self.silences = silences
        print("TrackLayout received silences: ", end="")
        print(silences)

    def match(self, min_silence_len=1000, silence_thresh=-16, seek_step=1):
        if self.audio_segment is None:
            raise AudioNotLoadedException
        # TODO: We'll need to check if a silence crosses the boundary between tracks
        print("fork into threads")
        length = len(self.audio_segment)
        split1 = int(length/4)
        split2 = int(length/2)
        split3 = split1 * 3
        segments = [self.audio_segment[:split1], self.audio_segment[split1:split2], self.audio_segment[split2:split3], self.audio_segment[split3:]]

        with Pool() as pool:
            tracks = pool.map(detect_nonsilent_wrapper, segments)

        pool.join()
        print("Threads finished")

        # Join these lists into one
        self.tracks = list(chain.from_iterable(tracks))
        print("detect_nonsilent done")

        if self.audio_metadata is None:
            # Without metadata, just take each non-silent section as a track
            # TODO: Could try something fancy like aiming to keep the tracks at similar lengths, avoid very short tracks, etc.
            self.split = [1] * len(self.tracks)
        else:
            self.split = self.match_part(self.tracks, self.audio_metadata)

    def detect_nonsilent_thread(self, start_time, audio_segment, min_silence_len, silence_thresh, seek_step):
        detect_nonsilent(audio_segment, min_silence_len, silence_thresh, seek_step)
        # TODO: How do I record this safely?

    def match_part(self, tracks, album_metadata, last_track_matched=0):
        print("match_part(last_track_matched=%d)" % last_track_matched)
        """Work out the possibilities of matching part of the tracks against the track listing and return the costs
        This is a recursive function. It works out the cost of the next track, whether that's up to the first possible split
        or the last, then recurses from that point onwards.

        :param tracks array           Non-silent segments detected by detect_nonsilent
        :param album_metadata array   Album metadata from musicbrainz
        :param last_track_matched int Last track we found. Defaults to 0 so we are more likely to match track 1 at first. Increases when this is called recursively.

        :return (best_match, best_score) Tuple of the best match (as a list of split points), and the score of that match

        The list of split points is the number of non-silent segments included in each track.
        E.g. [2, 1, 3] means the first track has 2 segments, then 1, then the third track includes 3 segments"""

        # Remember the timestamps in tracks start from the beginning of the recording, not the part we're looking at.
        # Each split option tells us the list of split points and the total cost.
        # E.g. {[2,1,5]: 30}
        best_cost = -1
        best_split = []

        for split_point in range(len(tracks)):
            # Get the timestamp of this split
            # Each non-silent range gives us the start and end of the non-silent portion, so cutting out the silence.
            (start, end) = tracks[split_point]
            if len(tracks) > split_point+1:
                # We take the track split to be the middle of the silent period
                # or 2 seconds before the start of the next track, whichever is later
                (next_start, next_end) = tracks[split_point+1]
                split_time = max((next_start+end)/2, next_start-2000)
            else:
                # End of the album
                split_time = end

            # Iterate over the metadata track until we find the one with the closest end time to this split
            cost = -1
            length_so_far = 0
            this_track_match = None
            if album_metadata is not None:
                for track in album_metadata:
                    length_so_far += track["length"]
                    track_number = track["number"]
                    this_cost = floor(abs(length_so_far - split_time)/1000)
                    if last_track_matched is not None and track_number > last_track_matched + 1:
                        this_cost += (track_number - last_track_matched - 1)*self.missed_split_penalty
                    if cost < 0 or this_cost < cost:
                        cost = this_cost
                        this_track_match = track_number
                    else:
                        # Cost has increased, so we must have passed the best match
                        break
            else:
                # No metadata available, so always match at the first split
                # TODO: Could try something fancy like aiming to keep the tracks at similar lengths,
                # avoid very short tracks, etc.
                this_track_match = last_track_matched + 1

            # Recurse
            if len(tracks) > split_point+1:
                (splits, recursive_costs) = self.match_part(tracks[1:], album_metadata, this_track_match)
                splits.insert(0, split_point+1)
                cost += recursive_costs
            else:
                splits = [split_point+1] # Index works with zero-index, but we're counting the number of tracks

            # Find the best split from this method and its recursions
            if best_cost < 0 or cost < best_cost:
                best_cost = cost
                best_split = splits

        self.defaultSplit = best_split
        self.reset_split()
        self.first_track = this_track_match
        return (best_split, best_cost)

    def reset_split(self):
        """Reset the current split to the default"""
        self.split = self.defaultSplit

    def lengthen_track(self, track):
        """Lengthen a specific track to the next silence, and shorten the next track

        :param track Track number to lengthen"""
        if (not self.can_lengthen_track(track)):
            return False

        self.split[track-1] += 1
        self.split[self._get_next_nonzero_track(track)-1] -= 1

    def can_lengthen_track(self, track):
        """Check if a track can be lengthened

        :param track int Track number to lengthen"""
        return track <= len(self.split) and self._get_next_nonzero_track(track)

    def _get_next_nonzero_track(self, track):
        """Get the next track that has a non-zero length

        :param track int Get the next track AFTER this one

        :return int|boolean Non-zero track number, or False if there isn't one"""
        while (track < len(self.split) and self.split[track] == 0):
            track += 1

        if (track < len(self.split)) :
            return track
        else:
            return False

    def shorten_track(self, track):
        """Shorten a specific track to the next silence, and lengthen the next track

        :param track Track number to shorten"""
        if (not self.can_lengthen_track(track)):
            return False

        self.split[track-1] -= 1
        self.split[track] += 1

    def can_shorten_track(self, track):
        """Check if a track can be shorten

        :param track int Track number to lengthen"""
        return self.split[track-1] > 0

    def get_track_listing(self):
        """Get a track listing of the current split layout"""
        listing = []
        track_number = self.first_track
        for track in self.split:
            listing.append(self.audio_metadata[track_number])
            track_number += 1

        return listing

class AudioNotLoadedException(AttributeError):
    pass

# class FindSilences(threading.Thread):
#     """Find silences within a portion of audio, and therefore the track boundaries"""
#     def __init__(self, audio_segment, start_time, min_silence_len, silence_thresh, seek_step):
#         threading.Thread.__init__(self)
#         self.start_time = start_time
#         self.audio_segment = audio_segment
#         self.min_silence_len = min_silence_len
#         self.silence_thresh = silence_thresh
#         self.seek_step = seek_step
#
#     def run(self) -> None:
#         detect_nonsilent(self.audio_segment, self.min_silence_len, self.silence_thresh, self.seek_step)

