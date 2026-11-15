from abc import ABC, abstractmethod
from contextlib import redirect_stdout
import io
import threading
from typing import cast
import unittest


class IDevice(ABC):

    @abstractmethod
    def turn_on(self) -> None:
        pass

    @abstractmethod
    def turn_off(self) -> None:
        pass


class ILockable(ABC):

    @abstractmethod
    def lock(self) -> None:
        pass

    @abstractmethod
    def unlock(self) -> None:
        pass


class SmartLight(IDevice):

    def __init__(self, name: str) -> None:
        self.name = name

    def turn_on(self) -> None:
        print(f"{self.name}: ON")

    def turn_off(self) -> None:
        print(f"{self.name}: OFF")


class SmartFan(IDevice):

    def __init__(self, name: str) -> None:
        self.name = name

    def turn_on(self) -> None:
        print(f"{self.name}: ON")

    def turn_off(self) -> None:
        print(f"{self.name}: OFF")


class SmartDoor(IDevice, ILockable):

    def __init__(self, name: str) -> None:
        self.name = name

    def turn_on(self) -> None:
        print(f"{self.name}: ON")

    def turn_off(self) -> None:
        print(f"{self.name}: OFF")

    def lock(self) -> None:
        print(f"{self.name}: LOCKED")

    def unlock(self) -> None:
        print(f"{self.name}: UNLOCKED")


class DeviceFactory:

    @staticmethod
    def create(device_type: str, name: str) -> IDevice:
        normalized_type = device_type.strip().lower()
        if normalized_type == "light":
            return SmartLight(name)
        elif normalized_type == "fan":
            return SmartFan(name)
        elif normalized_type == "door":
            return SmartDoor(name)
        else:
            raise ValueError(f"Unsupported device type: {device_type}")


class HomeConfiguration:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        raise RuntimeError(
            "Call get_instance() instead of instantiating directly."
        )

    @classmethod
    def get_instance(cls) -> "HomeConfiguration":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.home_name = "My Home"
                    instance.night_light_level = 30
                    cls._instance = instance
        return cls._instance


class SmartHomeFacade:

    def __init__(self, light: IDevice, fan: IDevice, door: ILockable) -> None:
        self._light = light
        self._fan = fan
        self._door = door

    def go_to_work(self) -> None:
        self._light.turn_off()
        self._fan.turn_off()
        self._door.lock()

    def go_to_sleep(self) -> None:
        self._fan.turn_off()
        self._door.lock()
        self._light.turn_on()
        level = HomeConfiguration.get_instance().night_light_level
        print(f"Night light level: {level}%")


class TestSmartHomePatterns(unittest.TestCase):

    def test_t1_factory_creates_correct_types(self):
        light = DeviceFactory.create("light", "Bedroom Light")
        fan = DeviceFactory.create("FAN", "Ceiling Fan")
        door = DeviceFactory.create(" DoOr ", "Front Door")

        self.assertIsInstance(light, SmartLight)
        self.assertIsInstance(fan, SmartFan)
        self.assertIsInstance(door, SmartDoor)

    def test_t2_factory_unsupported_type_raises_exception(self):
        with self.assertRaises(ValueError) as context:
            DeviceFactory.create("camera", "Garage Camera")
        self.assertIn("Unsupported device type", str(context.exception))

    def test_t3_singleton_returns_same_instance(self):
        c1 = HomeConfiguration.get_instance()
        c2 = HomeConfiguration.get_instance()
        self.assertIs(c1, c2)

    def test_t4_facade_go_to_work(self):
        light = DeviceFactory.create("light", "Living room light")
        fan = DeviceFactory.create("fan", "Living room fan")
        door = DeviceFactory.create("door", "Main door")
        facade = SmartHomeFacade(light, fan, cast(ILockable, door))

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            facade.go_to_work()

        output = buffer.getvalue().strip().splitlines()
        self.assertEqual(
            output,
            [
                "Living room light: OFF",
                "Living room fan: OFF",
                "Main door: LOCKED",
            ],
        )

    def test_t5_facade_go_to_sleep(self):
        HomeConfiguration.get_instance().night_light_level = 30
        light = DeviceFactory.create("light", "Living room light")
        fan = DeviceFactory.create("fan", "Living room fan")
        door = DeviceFactory.create("door", "Main door")
        facade = SmartHomeFacade(light, fan, cast(ILockable, door))

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            facade.go_to_sleep()

        output = buffer.getvalue().strip().splitlines()
        self.assertEqual(
            output,
            [
                "Living room fan: OFF",
                "Main door: LOCKED",
                "Living room light: ON",
                "Night light level: 30%",
            ],
        )


def run_demo() -> None:
    print("=== DEMO CHƯƠNG TRÌNH SMART HOME MINI ===")
    config1 = HomeConfiguration.get_instance()
    config2 = HomeConfiguration.get_instance()
    print(f"Singleton check (config1 is config2): {config1 is config2}")
    print(f"Home Name: {config1.home_name}\n")

    light = DeviceFactory.create("LIGHT", "Living room light")
    fan = DeviceFactory.create("fan", "Living room fan")
    door = DeviceFactory.create("Door", "Main door")

    facade = SmartHomeFacade(light, fan, cast(ILockable, door))

    print("--- Mode: Go To Work ---")
    facade.go_to_work()

    print("\n--- Mode: Go To Sleep ---")
    facade.go_to_sleep()

    print("\n--- Manual Control ---")
    cast(ILockable, door).unlock()
    print("=========================================\n")


if __name__ == "__main__":
    run_demo()
    print("=== CHẠY KIỂM THỬ (T1 -> T5) ===")
    unittest.main(verbosity=2)