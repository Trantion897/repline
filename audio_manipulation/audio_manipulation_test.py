import unittest
import audio_manipulation


class TestMatchTracks(unittest.TestCase):
    def test_match_tracks(self):
        """Test that match tracks matches some samples correctly"""
        samples = [
            {
                "label": "Single track",
                "tracks": [[0, 10000]],
                "metadata": [{"length": 10000, "number": 1}],
                "splits": [1], "cost": 0
            },
            {
                "label": "Two tracks",
                "tracks": [[0, 10000], [11000, 20000]],
                "metadata": [{"length": 10000, "number": 1}, {"length": 10000, "number": 2}],
                "splits":[1,1], "cost": 0
            },
            {
                "label": "Three tracks",
                "tracks": [[0, 10000], [11000, 20000], [21000, 30000]],
                "metadata": [{"length": 10000, "number": 1}, {"length": 10000, "number": 2}, {"length": 10000, "number": 3}],
                "splits": [1,1,1], "cost":0
            },
            {
                "label": "Single track with silence",
                "tracks": [[0, 10000], [10500, 20000]],
                "metadata": [{"length": 20000, "number": 1}],
                "splits": [2], "cost":0
            },
            {
                "label": "Two tracks without silence",
                "tracks": [[0, 20000]],
                "metadata": [{"length": 10000, "number": 1}, {"length": 10000, "number": 2}],
                "splits": [1], "cost": 10
            },
            {
                # This makes it start with track 1, so it spots the missing silence. Longer tracks make sure they aren't lost
                "label": "Multiple tracks with missing silences",
                "tracks": [[0, 100000], [101000, 301000], [302000, 402000]],
                "metadata": [{"length": 100000, "number": 1}, {"length": 100000, "number": 2},
                             {"length": 100000, "number": 3}, {"length": 100000, "number": 4}],
                "splits": [1, 1, 1], "cost": 13
            },
            {
                "label": "Two tracks with mismatch",
                "tracks": [[0, 10000], [11000, 20000]],
                "metadata": [{"length": 8000, "number": 1}, {"length": 12000, "number": 2}],
                "splits": [1, 1], "cost": 2
            },
        ]

        for sample in samples:
            (splits, cost) = audio_manipulation.match_part(sample["tracks"], sample["metadata"])
            self.assertEqual(sample["splits"], splits, sample["label"])
            self.assertEqual(sample["cost"], cost, sample["label"])


if __name__ == '__main__':
    print ("GO")
    unittest.main()
