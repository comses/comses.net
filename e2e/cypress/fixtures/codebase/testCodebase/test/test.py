#generated from chatgpt

# test.py
import unittest
import numpy as np
from util import logistic_growth

class TestLogisticGrowth(unittest.TestCase):
    def test_logistic_growth_initial_population(self):
        """
        Test that the initial population is set correctly.
        """
        r = 0.1
        K = 1000
        P0 = 10
        t_max = 100
        dt = 1

        time, population = logistic_growth(r, K, P0, t_max, dt)
        
        self.assertEqual(population[0], P0, "Initial population should be equal to P0")

    def test_logistic_growth_shape(self):
        """
        Test that the shape of the time and population arrays are correct.
        """
        r = 0.1
        K = 1000
        P0 = 10
        t_max = 100
        dt = 1

        time, population = logistic_growth(r, K, P0, t_max, dt)
        
        expected_length = int(t_max / dt)
        self.assertEqual(len(time), expected_length, "Time array length should match expected length")
        self.assertEqual(len(population), expected_length, "Population array length should match expected length")

    def test_logistic_growth_population_limit(self):
        """
        Test that the population approaches the carrying capacity K.
        """
        r = 0.1
        K = 1000
        P0 = 10
        t_max = 1000
        dt = 1

        time, population = logistic_growth(r, K, P0, t_max, dt)
        
        self.assertAlmostEqual(population[-1], K, delta=K*0.01, msg="Final population should approach the carrying capacity K")

if __name__ == '__main__':
    unittest.main()

