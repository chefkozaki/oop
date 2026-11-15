from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Generic, Iterable, Optional, Protocol, Sequence, TypeVar, runtime_checkable


class DeviceStatus(Enum):
    AVAILABLE = "Available"
    BORROWED = "Borrowed"
    UNDER_MAINTENANCE = "UnderMaintenance"


class DuplicateIdException(Exception):
    def __init__(self, duplicate_id: str, message: Optional[str] = None) -> None:
        self.duplicate_id = duplicate_id
        super().__init__(message or f"Thiết bị với mã '{duplicate_id}' đã tồn tại trong kho.")


class NoSuitableItemException(Exception):
    def __init__(self, message: str = "Không tìm thấy thiết bị phù hợp để cấp phát.") -> None:
        super().__init__(message)


class DeviceNotReadyException(Exception):
    def __init__(self, device_id: str, current_status: DeviceStatus, message: Optional[str] = None) -> None:
        self.device_id = device_id
        self.current_status = current_status
        super().__init__(
            message or f"Thiết bị '{device_id}' chưa sẵn sàng sử dụng (Trạng thái hiện tại: {current_status.value})."
        )


@runtime_checkable
class IIdentifiable(Protocol):
    @property
    def id(self) -> str:
        ...


class TeachingDevice(ABC):
    def __init__(self, device_id: str, name: str, storage_location: str) -> None:
        if not device_id or not device_id.strip():
            raise ValueError("Mã thiết bị (id) không được để trống.")
        if not name or not name.strip():
            raise ValueError("Tên thiết bị (name) không được để trống.")
        if not storage_location or not storage_location.strip():
            raise ValueError("Vị trí lưu trữ (storage_location) không được để trống.")

        self._id: str = device_id.strip()
        self._name: str = name.strip()
        self._storage_location: str = storage_location.strip()
        self._status: DeviceStatus = DeviceStatus.AVAILABLE

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def storage_location(self) -> str:
        return self._storage_location

    @property
    def status(self) -> DeviceStatus:
        return self._status

    def set_maintenance(self) -> None:
        if self._status == DeviceStatus.BORROWED:
            raise DeviceNotReadyException(self._id, self._status, "Không thể bảo trì thiết bị đang được mượn.")
        self._status = DeviceStatus.UNDER_MAINTENANCE

    @abstractmethod
    def is_ready_for_use(self) -> bool:
        ...

    @abstractmethod
    def get_default_priority_score(self) -> float:
        ...

    def borrow(self) -> None:
        if not self.is_ready_for_use():
            raise DeviceNotReadyException(self._id, self._status)
        self._status = DeviceStatus.BORROWED

    def return_device(self) -> None:
        if self._status != DeviceStatus.BORROWED:
            raise DeviceNotReadyException(
                self._id,
                self._status,
                f"Chỉ có thể trả thiết bị đang ở trạng thái Borrowed (hiện tại: {self._status.value}).",
            )
        self._status = DeviceStatus.AVAILABLE

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id!r} name={self._name!r} status={self._status.value}>"


class ProjectorRemote(TeachingDevice):
    def __init__(self, device_id: str, name: str, storage_location: str, battery_level: int) -> None:
        super().__init__(device_id, name, storage_location)
        if not (0 <= battery_level <= 100):
            raise ValueError("Mức pin phải nằm trong khoảng từ 0 đến 100.")
        self._battery_level: int = battery_level

    @property
    def battery_level(self) -> int:
        return self._battery_level

    def is_ready_for_use(self) -> bool:
        return self.status == DeviceStatus.AVAILABLE and self._battery_level >= 20

    def get_default_priority_score(self) -> float:
        return float(self._battery_level)


class AirConditionerRemote(TeachingDevice):
    def __init__(
        self,
        device_id: str,
        name: str,
        storage_location: str,
        compatible_rooms: Iterable[str],
    ) -> None:
        super().__init__(device_id, name, storage_location)
        self._compatible_rooms: frozenset[str] = frozenset(
            room.strip().upper() for room in compatible_rooms if room and room.strip()
        )

    @property
    def compatible_rooms(self) -> frozenset[str]:
        return self._compatible_rooms

    def is_compatible_with(self, room_id: str) -> bool:
        if not room_id:
            return False
        return room_id.strip().upper() in self._compatible_rooms

    def is_ready_for_use(self) -> bool:
        return self.status == DeviceStatus.AVAILABLE

    def get_default_priority_score(self) -> float:
        return 100.0 if len(self._compatible_rooms) > 0 else 0.0

    def get_priority_for_room(self, room_id: str) -> float:
        return 100.0 if self.is_compatible_with(room_id) else 0.0


class WirelessMicrophone(TeachingDevice):
    def __init__(
        self,
        device_id: str,
        name: str,
        storage_location: str,
        battery_level: int,
        signal_quality: int,
    ) -> None:
        super().__init__(device_id, name, storage_location)
        if not (0 <= battery_level <= 100):
            raise ValueError("Mức pin phải nằm trong khoảng từ 0 đến 100.")
        if not (0 <= signal_quality <= 100):
            raise ValueError("Chất lượng tín hiệu phải nằm trong khoảng từ 0 đến 100.")
        self._battery_level: int = battery_level
        self._signal_quality: int = signal_quality

    @property
    def battery_level(self) -> int:
        return self._battery_level

    @property
    def signal_quality(self) -> int:
        return self._signal_quality

    def is_ready_for_use(self) -> bool:
        return (
            self.status == DeviceStatus.AVAILABLE
            and self._battery_level >= 30
            and self._signal_quality >= 40
        )

    def get_default_priority_score(self) -> float:
        return (self._battery_level + self._signal_quality) / 2.0


TIdentifiable = TypeVar("TIdentifiable", bound=IIdentifiable)
T = TypeVar("T")
TDevice = TypeVar("TDevice", bound=TeachingDevice)


class IRepository(ABC, Generic[TIdentifiable]):
    @abstractmethod
    def add(self, item: TIdentifiable) -> None:
        ...

    @abstractmethod
    def remove(self, item_id: str) -> bool:
        ...

    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[TIdentifiable]:
        ...

    @abstractmethod
    def get_all(self) -> Sequence[TIdentifiable]:
        ...

    @abstractmethod
    def find_all(self, condition: Callable[[TIdentifiable], bool]) -> Sequence[TIdentifiable]:
        ...


class InMemoryRepository(IRepository[TIdentifiable], Generic[TIdentifiable]):
    def __init__(self) -> None:
        self._storage: dict[str, TIdentifiable] = {}

    def add(self, item: TIdentifiable) -> None:
        if item is None:
            raise ValueError("Không chấp nhận phần tử None vào kho lưu trữ.")
        if item.id in self._storage:
            raise DuplicateIdException(item.id)
        self._storage[item.id] = item

    def remove(self, item_id: str) -> bool:
        if item_id in self._storage:
            del self._storage[item_id]
            return True
        return False

    def find_by_id(self, item_id: str) -> Optional[TIdentifiable]:
        return self._storage.get(item_id)

    def get_all(self) -> tuple[TIdentifiable, ...]:
        return tuple(self._storage.values())

    def find_all(self, condition: Callable[[TIdentifiable], bool]) -> tuple[TIdentifiable, ...]:
        if condition is None:
            raise ValueError("Điều kiện lọc không được là None.")
        return tuple(item for item in self._storage.values() if condition(item))


class ISelectionStrategy(ABC, Generic[T]):
    @abstractmethod
    def select(self, candidates: Sequence[T]) -> T:
        ...


class HighestPriorityStrategy(ISelectionStrategy[T], Generic[T]):
    def __init__(self, score_selector: Callable[[T], float]) -> None:
        if score_selector is None:
            raise ValueError("Hàm tính điểm score_selector không được là None.")
        self._score_selector = score_selector

    def select(self, candidates: Sequence[T]) -> T:
        if not candidates:
            raise NoSuitableItemException("Danh sách ứng viên rỗng, không thể chọn thiết bị ưu tiên cao nhất.")
        return max(candidates, key=self._score_selector)


class FirstAvailableStrategy(ISelectionStrategy[T], Generic[T]):
    def select(self, candidates: Sequence[T]) -> T:
        if not candidates:
            raise NoSuitableItemException("Danh sách ứng viên rỗng, không thể chọn thiết bị đầu tiên.")
        return candidates[0]


class AllocationService(Generic[TDevice]):
    def __init__(
        self,
        repository: IRepository[TDevice],
        strategy: ISelectionStrategy[TDevice],
    ) -> None:
        if repository is None:
            raise ValueError("Repository không được là None.")
        if strategy is None:
            raise ValueError("Strategy không được là None.")
        self._repository = repository
        self._strategy = strategy

    def change_strategy(self, new_strategy: ISelectionStrategy[TDevice]) -> None:
        if new_strategy is None:
            raise ValueError("Chiến lược mới không được là None.")
        self._strategy = new_strategy

    def allocate(self, additional_condition: Optional[Callable[[TDevice], bool]] = None) -> TDevice:
        all_devices = self._repository.get_all()
        ready_devices = [device for device in all_devices if device.is_ready_for_use()]

        if additional_condition is not None:
            candidates = [device for device in ready_devices if additional_condition(device)]
        else:
            candidates = ready_devices

        selected_device = self._strategy.select(candidates)
        selected_device.borrow()
        return selected_device


def run_tests() -> None:
    print("Kiểm thử\n")

    proj_repo = InMemoryRepository[ProjectorRemote]()
    ac_repo = InMemoryRepository[AirConditionerRemote]()
    mic_repo = InMemoryRepository[WirelessMicrophone]()

    p1 = ProjectorRemote("PRJ-01", "Remote Epson Tầng 1", "Tủ A1", battery_level=15)
    p2 = ProjectorRemote("PRJ-02", "Remote Sony Tầng 2", "Tủ A1", battery_level=65)
    p3 = ProjectorRemote("PRJ-03", "Remote Panasonic Tầng 3", "Tủ A2", battery_level=90)

    ac1 = AirConditionerRemote("AC-01", "Remote Daikin Khu A", "Tủ B1", ["A101", "A102", "A203"])
    ac2 = AirConditionerRemote("AC-02", "Remote LG Khu B", "Tủ B2", ["B101", "B105"])

    m1 = WirelessMicrophone("MIC-01", "Micro Shure 01", "Tủ C1", battery_level=25, signal_quality=90)
    m2 = WirelessMicrophone("MIC-02", "Micro Sennheiser 02", "Tủ C1", battery_level=80, signal_quality=70)
    m3 = WirelessMicrophone("MIC-03", "Micro JBL 03", "Tủ C2", battery_level=95, signal_quality=85)

    for p in (p1, p2, p3):
        proj_repo.add(p)
    for ac in (ac1, ac2):
        ac_repo.add(ac)
    for m in (m1, m2, m3):
        mic_repo.add(m)
    print("[Test 1 & 11] Đã thêm thành công 3 loại thiết bị vào InMemoryRepository<T> mà không lặp mã.")

    try:
        proj_repo.add(ProjectorRemote("PRJ-01", "Remote Trùng Mã", "Tủ A1", battery_level=100))
        assert False, "Phải ném ra DuplicateIdException"
    except DuplicateIdException as ex:
        print(f"[Test 2] Bắt ngoại lệ trùng mã thành công: {ex}")

    found = proj_repo.find_by_id("PRJ-02")
    not_found = proj_repo.find_by_id("PRJ-999")
    assert found is p2 and not_found is None
    print(f"[Test 3] Tìm theo mã 'PRJ-02': {found} | Tìm 'PRJ-999': {not_found}")

    ready_projectors = proj_repo.find_all(lambda d: d.is_ready_for_use())
    ready_mics = mic_repo.find_all(lambda d: d.is_ready_for_use())
    assert [d.id for d in ready_projectors] == ["PRJ-02", "PRJ-03"]
    assert [d.id for d in ready_mics] == ["MIC-02", "MIC-03"]
    print(f"[Test 4] Projector sẵn sàng: {[d.id for d in ready_projectors]} | Mic sẵn sàng: {[d.id for d in ready_mics]}")

    highest_proj_strategy = HighestPriorityStrategy[ProjectorRemote](
        lambda device: device.get_default_priority_score()
    )
    proj_service = AllocationService[ProjectorRemote](proj_repo, highest_proj_strategy)
    allocated_proj = proj_service.allocate()
    assert allocated_proj.id == "PRJ-03"
    assert allocated_proj.status == DeviceStatus.BORROWED
    print(f"[Test 5 & 10] Cấp phát projector ưu tiên cao nhất: {allocated_proj.id} -> Trạng thái: {allocated_proj.status.value}")

    ac_service = AllocationService[AirConditionerRemote](
        ac_repo,
        FirstAvailableStrategy[AirConditionerRemote](),
    )
    allocated_ac = ac_service.allocate(lambda device: device.is_compatible_with("A203"))
    assert allocated_ac.id == "AC-01"
    assert allocated_ac.status == DeviceStatus.BORROWED
    print(f"[Test 6] Cấp phát điều khiển điều hòa cho phòng A203: {allocated_ac.id} -> Trạng thái: {allocated_ac.status.value}")

    mic_service = AllocationService[WirelessMicrophone](
        mic_repo,
        FirstAvailableStrategy[WirelessMicrophone](),
    )
    first_mic = mic_service.allocate()
    assert first_mic.id == "MIC-02"
    print(f"[Test 7] Chọn micro đầu tiên sẵn sàng (FirstAvailable): {first_mic.id}")

    first_mic.return_device()
    assert first_mic.status == DeviceStatus.AVAILABLE

    mic_service.change_strategy(
        HighestPriorityStrategy[WirelessMicrophone](lambda d: d.get_default_priority_score())
    )
    best_mic = mic_service.allocate()
    assert best_mic.id == "MIC-03"
    print(f"[Test 8] Sau khi đổi sang HighestPriority lúc runtime, chọn được: {best_mic.id} (Điểm: {best_mic.get_default_priority_score()})")

    try:
        ac_service.allocate(lambda device: device.is_compatible_with("Z999"))
        assert False, "Phải ném ra NoSuitableItemException"
    except NoSuitableItemException as ex:
        print(f"[Test 9] Bắt ngoại lệ khi không có thiết bị phù hợp: {ex}")

    print("\n=== TẤT CẢ 11 KỊCH BẢN KIỂM THỬ ĐỀU ĐẠT ===")


if __name__ == "__main__":
    run_tests()
