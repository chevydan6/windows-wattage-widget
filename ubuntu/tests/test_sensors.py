import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('wattage_widget', Path(__file__).parents[1] / 'wattage_widget.py')
widget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(widget)


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def battery(self, name='BAT0', **values):
        directory = self.root / name
        directory.mkdir(exist_ok=True)
        for key, value in {'type': 'Battery', 'present': 1, **values}.items():
            (directory / key).write_text(str(value))

    def test_discharge_microwatts(self):
        self.battery(status='Discharging', power_now=12_500_000)
        self.assertEqual(widget.read_power(self.root)['watts'], 12.5)

    def test_charging(self):
        self.battery(status='Charging', power_now=20_000_000)
        result = widget.read_power(self.root)
        self.assertEqual(result['mode'], 'BATTERY CHARGE')
        self.assertEqual(result['watts'], 20)

    def test_current_and_voltage_fallback(self):
        self.battery(status='Discharging', current_now=-1_000_000, voltage_now=15_000_000)
        self.assertEqual(widget.read_power(self.root)['watts'], 15)

    def test_ac_does_not_claim_total_consumption(self):
        self.battery(status='Full', power_now=0)
        result = widget.read_power(self.root)
        self.assertEqual(result['mode'], 'AC POWER')
        self.assertIsNone(result['watts'])

    def test_missing_sensor_is_not_zero(self):
        self.battery(status='Discharging')
        self.assertIsNone(widget.read_power(self.root)['watts'])

    def test_unplugged_battery_is_ignored(self):
        self.battery(present=0, status='Discharging', power_now=12_000_000)
        self.assertEqual(widget.read_power(self.root)['detail'], 'Sensor unavailable')

    def test_multiple_batteries_use_net_power(self):
        self.battery(status='Discharging', power_now=15_000_000)
        self.battery('BAT1', status='Charging', power_now=5_000_000)
        result = widget.read_power(self.root)
        self.assertEqual(result['mode'], 'BATTERY DRAW')
        self.assertEqual(result['watts'], 10)


if __name__ == '__main__':
    unittest.main()
