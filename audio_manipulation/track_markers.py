import random


class TrackData:
    tracks = []
    silences = []

    def __init__(self):
        # TODO: Testing data
        for i in range(0, 10):
            newTrack = Track()

            if i == 0:
                newTrack.prevTrack = None
                newTrack.startTime = 0
            else:
                newTrack.prevTrack = self.tracks[-1]
                newTrack.startTime = self.tracks[-1].endTime
                self.tracks[-1].nextTrack = newTrack

            newTrack.endTime = random.randint(newTrack.startTime+60, newTrack.startTime+600)
            self.tracks.append(newTrack)

class Track:
    startTime = 0
    endTime = 0
    prevTrack = None
    nextTrack = None
    isSilent = False

    def adjustStartTime(self, newStartTime):
        """Adjust the start time of this track

        Sets a new start time for this track, and if there's a previous track it adjusts the end time to match

        :param newStartTime New start time in seconds
        :return: False on failure
        """
        # If there is a previous track, the start time must be after that track's start time
        if self.prevTrack and newStartTime < self.prevTrack.startTime:
            return False
        elif newStartTime < 0:
            newStartTime = 0

        self.startTime = newStartTime
        if self.prevTrack:
            self.prevTrack.endTime = newStartTime

    def adjustEndTime(self, newEndTime):
        """Adjust the end time of this track

        Sets a new end time for this track, and if there's a next track it adjusts the start time to match

        :param newEndTime: New end time in seconds
        :return: False on failure
        """
        # If there is a next track, the end time must be before that track's end time
        if self.nextTrack and newEndTime > self.nextTrack.endTime:
            return False

        # TODO: Check we haven't gone beyond the end of the recording
        self.endTime = newEndTime
        if self.nextTrack:
            self.nextTrack.startTime = newEndTime

    def split(self, splitPoint):
        """Splits this track in two at a specified split point

        :param splitPoint: Time to split, from the beginning of the full recording, in seconds
        :return:
        """
        if not self.startTime < splitPoint < self.endTime:
            return False

        newTrack = TrackMarker()
        newTrack.startTime = splitPoint
        newTrack.endTime = self.endTime
        newTrack.prevTrack = self
        newTrack.nextTrack = self.nextTrack
        newTrack.isSilent = self.isSilent

        self.nextTrack.prevTrack = newTrack

        self.nextTrack = newTrack
        self.endTime = splitPoint

    def join(self, other):
        if other == self.prevTrack:
            self.prevTrack.nextTrack = self.nextTrack
            self.prevTrack.endTime = self.endTime
            self.nextTrack.prevTrack = self.prevTrack
        elif other == self.nextTrack:
            self.nextTrack.prevTrack = self.prevTrack
            self.nextTrack.startTime = self.startTime
            self.prevTrack.nextTrack = self.nextTrack
        else:
            return False

    def get_duration(self):
        return self.endTime - self.startTime

class Silence:
    startTime = 0
    duration = 0
    amplitude = None
