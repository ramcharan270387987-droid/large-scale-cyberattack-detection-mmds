"""Check target isolation and rejection semantics before cloud modeling."""
import unittest
from src.ml.phase9_label_registry import target, vocabulary, UNKNOWN
from src.ml.open_set_rejection import cutoff, uncertainty


class Phase9Contracts(unittest.TestCase):
    def test_training_vocabulary(self):
        classes = vocabulary({'Bot': 100, 'Web attack': 0, 'DoS': 50})
        self.assertEqual(classes, {'Bot': 0, 'DoS': 1})
        self.assertEqual(target('Web attack', classes), UNKNOWN)
        with self.assertRaises(ValueError):
            vocabulary({'Typo': 1})

    def test_probability_semantics(self):
        self.assertEqual(uncertainty([.5, .5]), {'maximum': .5, 'margin': 0, 'entropy': 1})
        self.assertEqual(uncertainty([1, 0])['entropy'], 0)
        with self.assertRaises(ValueError):
            uncertainty([.5, .8])

    def test_conservative_ties(self):
        histogram = {.1: 90, .8: 8, .9: 2}
        threshold = cutoff(histogram, .05)
        self.assertEqual(threshold, .8)
        self.assertLessEqual(sum(n for x,n in histogram.items() if x > threshold)/100, .05)
        self.assertEqual(cutoff(histogram, 0), .9)
