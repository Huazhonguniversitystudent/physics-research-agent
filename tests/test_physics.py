import unittest

from src.tools.physics import electron_energy_from_voltage


class ElectronEnergyTests(unittest.TestCase):
    def test_five_volts(self):
        result = electron_energy_from_voltage(5)

        self.assertEqual(result["voltage_v"], 5.0)
        self.assertEqual(result["energy_ev"], 5.0)
        self.assertAlmostEqual(result["energy_j"], 8.01088317e-19)


if __name__ == "__main__":
    unittest.main()
