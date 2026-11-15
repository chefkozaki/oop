from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional

class DeviceStatus(Enum):
    AVAILABLE = "Available"                 # Sẵn sàng cho mượn
    BORROWED = "Borrowed"                   # Đang được mượn
    UNDER_MAINTENANCE = "UnderMaintenance"  # Đang bảo trì
    RETIRED = "Retired"                     # Ngừng sử dụng


class BorrowingException(Exception):
    """Ngoại lệ cơ sở cho toàn bộ nghiệp vụ mượn trả thiết bị"""
    def __init__(self, message: str, inner_exception: Optional[Exception] = None):
        super().__init__(message)
        self.inner_exception = inner_exception


class DeviceUnavailableException(BorrowingException):
    def __init__(self, device_id: str, current_status: DeviceStatus):
        self.device_id = device_id
        self.current_status = current_status
        super().__init__(f"Thiết bị '{device_id}' hiện không sẵn sàng (Trạng thái: {current_status.value}).")


class BorrowLimitExceededException(BorrowingException):
    def __init__(self, borrower_id: str, max_devices: int):
        self.borrower_id = borrower_id
        self.max_devices = max_devices
        super().__init__(f"Người mượn '{borrower_id}' đã đạt giới hạn tối đa {max_devices} thiết bị.")


class InvalidBorrowPeriodException(BorrowingException):
    def __init__(self, device_id: str, requested_days: int, max_days: int):
        self.device_id = device_id
        self.requested_days = requested_days
        self.max_days = max_days
        super().__init__(
            f"Thời hạn mượn không hợp lệ cho thiết bị '{device_id}': "
            f"Yêu cầu {requested_days} ngày (Quy định: 1 đến {max_days} ngày)."
        )


class DuplicateDeviceException(BorrowingException):
    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(f"Thiết bị '{device_id}' đã tồn tại trong phiếu mượn này.")


class DeviceNotInSlipException(BorrowingException):
    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(f"Thiết bị '{device_id}' không có trong phiếu mượn.")


class DeviceAlreadyReturnedException(BorrowingException):
    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(f"Thiết bị '{device_id}' đã được trả trước đó.")


class InvalidReturnDateException(BorrowingException):
    def __init__(self, device_id: str, borrowed_date: datetime, returned_date: datetime):
        super().__init__(
            f"Ngày trả ({returned_date.strftime('%Y-%m-%d')}) của thiết bị '{device_id}' "
            f"không được trước ngày mượn ({borrowed_date.strftime('%Y-%m-%d')})."
        )


class Device(ABC):
    def __init__(
        self,
        device_id: str,
        name: str,
        year_in_use: int,
        purchase_price: float,
        max_borrow_days: int = 1,
        max_periods: int = 5,
        status: DeviceStatus = DeviceStatus.AVAILABLE
    ):
        if not device_id or not device_id.strip():
            raise ValueError("Mã thiết bị không được rỗng.")
        if purchase_price <= 0:
            raise ValueError("Giá mua phải lớn hơn 0.")
        current_year = datetime.now().year
        if year_in_use > current_year:
            raise ValueError(f"Năm đưa vào sử dụng ({year_in_use}) không được lớn hơn năm hiện tại ({current_year}).")

        self._device_id = device_id.strip()
        self.name = name
        self.year_in_use = year_in_use
        self.purchase_price = purchase_price
        self.max_borrow_days = max_borrow_days
        self.max_periods = max_periods
        self.status = status

    @property
    def device_id(self) -> str:
        return self._device_id

    def mark_as_borrowed(self) -> None:
        self.status = DeviceStatus.BORROWED

    def mark_as_available(self) -> None:
        self.status = DeviceStatus.AVAILABLE

    @abstractmethod
    def calculate_annual_maintenance_cost(self) -> float:
        """Tính chi phí bảo trì dự kiến trong 1 năm"""
        pass

    @abstractmethod
    def get_daily_late_fee(self) -> float:
        """Phí phạt trả muộn mỗi ngày"""
        pass

    def __str__(self) -> str:
        return (
            f"[{self.device_id}] {self.name} | Năm SD: {self.year_in_use} | "
            f"Giá: {self.purchase_price:,.0f}đ | Trạng thái: {self.status.value}"
        )


class AirConditionerRemote(Device):
    """Điều khiển điều hòa"""
    def calculate_annual_maintenance_cost(self) -> float:
        return self.purchase_price * 0.05 + 50_000  # 5% giá mua + phí thay pin/kiểm tra

    def get_daily_late_fee(self) -> float:
        return 20_000.0


class Microphone(Device):
    """Micro không dây"""
    def calculate_annual_maintenance_cost(self) -> float:
        return self.purchase_price * 0.12 + 150_000  # Chi phí bảo trì cao hơn do dễ hư đầu thu

    def get_daily_late_fee(self) -> float:
        return 50_000.0


class ProjectorRemote(Device):
    """Điều khiển máy chiếu"""
    def calculate_annual_maintenance_cost(self) -> float:
        return self.purchase_price * 0.08 + 70_000

    def get_daily_late_fee(self) -> float:
        return 30_000.0


class ClassRoom:
    def __init__(self, room_id: str, room_name: str, capacity: int):
        self.room_id = room_id
        self.room_name = room_name
        self.capacity = capacity
        self._devices: List[Device] = []

    @property
    def devices(self) -> List[Device]:
        return list(self._devices)

    def add_device(self, device: Device) -> None:
        if device is None:
            raise ValueError("Không chấp nhận đối tượng thiết bị null.")
        if any(d.device_id == device.device_id for d in self._devices):
            raise ValueError(f"Thiết bị có mã '{device.device_id}' đã tồn tại trong phòng {self.room_name}.")
        self._devices.append(device)

    def remove_device(self, device_id: str) -> bool:
        device = self.find_device(device_id)
        if device:
            self._devices.remove(device)
            return True
        return False

    def find_device(self, device_id: str) -> Optional[Device]:
        for d in self._devices:
            if d.device_id == device_id:
                return d
        return None

    def calculate_annual_maintenance_cost(self) -> float:
        return sum(device.calculate_annual_maintenance_cost() for device in self._devices)

    def get_devices_requiring_maintenance(self) -> List[Device]:
        current_year = datetime.now().year
        return [
            d for d in self._devices
            if d.status == DeviceStatus.UNDER_MAINTENANCE or (current_year - d.year_in_use) > 5
        ]


class IBorrower(ABC):
    @property
    @abstractmethod
    def borrower_id(self) -> str:
        pass

    @property
    @abstractmethod
    def full_name(self) -> str:
        pass

    @abstractmethod
    def get_maximum_devices(self) -> int:
        pass


class Lecturer(IBorrower):
    """Giảng viên: mượn tối đa 3 thiết bị"""
    def __init__(self, borrower_id: str, full_name: str):
        self._borrower_id = borrower_id
        self._full_name = full_name

    @property
    def borrower_id(self) -> str:
        return self._borrower_id

    @property
    def full_name(self) -> str:
        return self._full_name

    def get_maximum_devices(self) -> int:
        return 3


class TeachingAssistant(IBorrower):
    """Trợ giảng: mượn tối đa 2 thiết bị"""
    def __init__(self, borrower_id: str, full_name: str):
        self._borrower_id = borrower_id
        self._full_name = full_name

    @property
    def borrower_id(self) -> str:
        return self._borrower_id

    @property
    def full_name(self) -> str:
        return self._full_name

    def get_maximum_devices(self) -> int:
        return 2


class BorrowItem:
    def __init__(
        self,
        device: Device,
        borrowed_date: datetime,
        due_date: datetime,
        from_period: int = 1,
        to_period: int = 3
    ):
        if device is None:
            raise ValueError("Device không được null.")
        if due_date < borrowed_date:
            raise ValueError("Hạn trả (DueDate) phải sau hoặc bằng ngày mượn (BorrowedDate).")
        if to_period < from_period:
            raise ValueError("Tiết kết thúc phải lớn hơn hoặc bằng tiết bắt đầu.")

        self._device = device
        self._borrowed_date = borrowed_date
        self._due_date = due_date
        self.from_period = from_period
        self.to_period = to_period
        self._returned_date: Optional[datetime] = None

    @property
    def device(self) -> Device:
        return self._device

    @property
    def borrowed_date(self) -> datetime:
        return self._borrowed_date

    @property
    def due_date(self) -> datetime:
        return self._due_date

    @property
    def returned_date(self) -> Optional[datetime]:
        return self._returned_date

    @property
    def is_returned(self) -> bool:
        return self._returned_date is not None

    @property
    def is_overdue(self) -> bool:
        check_date = self._returned_date if self.is_returned else datetime.now()
        return check_date.date() > self._due_date.date()

    def calculate_late_fee(self) -> float:
        if not self.is_overdue:
            return 0.0
        end_date = self._returned_date.date() if self.is_returned else datetime.now().date()
        overdue_days = (end_date - self._due_date.date()).days
        return max(0, overdue_days) * self._device.get_daily_late_fee()

    def return_device(self, returned_date: datetime) -> None:
        if self.is_returned:
            raise DeviceAlreadyReturnedException(self._device.device_id)
        if returned_date.date() < self._borrowed_date.date():
            raise InvalidReturnDateException(self._device.device_id, self._borrowed_date, returned_date)
        self._returned_date = returned_date


class BorrowingSlip:
    def __init__(
        self,
        slip_id: str,
        borrower: IBorrower,
        teaching_room: str,
        borrowed_date: Optional[datetime] = None
    ):
        if not slip_id or not slip_id.strip():
            raise ValueError("Mã phiếu mượn (SlipId) không hợp lệ.")
        if borrower is None:
            raise ValueError("Người mượn (Borrower) không được null.")
        if not teaching_room or not teaching_room.strip():
            raise ValueError("Phòng dạy (TeachingRoom) không hợp lệ.")

        self._slip_id = slip_id.strip()
        self._borrower = borrower
        self._teaching_room = teaching_room.strip()
        self._borrowed_date = borrowed_date or datetime.now()
        self._items: List[BorrowItem] = []

    @property
    def slip_id(self) -> str:
        return self._slip_id

    @property
    def borrower(self) -> IBorrower:
        return self._borrower

    @property
    def teaching_room(self) -> str:
        return self._teaching_room

    @property
    def borrowed_date(self) -> datetime:
        return self._borrowed_date

    @property
    def items(self) -> tuple[BorrowItem, ...]:
        return tuple(self._items)

    def _validate_borrowing(self, device: Device, borrow_days: int) -> None:
        if device is None:
            raise ValueError("Thiết bị không được null.")
        if borrow_days <= 0 or borrow_days > device.max_borrow_days:
            raise InvalidBorrowPeriodException(device.device_id, borrow_days, device.max_borrow_days)
        if any(item.device.device_id == device.device_id for item in self._items):
            raise DuplicateDeviceException(device.device_id)
        if len(self._items) >= self._borrower.get_maximum_devices():
            raise BorrowLimitExceededException(
                self._borrower.borrower_id, self._borrower.get_maximum_devices()
            )
        if device.status != DeviceStatus.AVAILABLE:
            raise DeviceUnavailableException(device.device_id, device.status)

    def add_device(self, device: Device, borrow_days: int, from_period: int = 1, to_period: int = 3) -> None:
        self._validate_borrowing(device, borrow_days)

        due_date = self._borrowed_date + timedelta(days=borrow_days)
        item = BorrowItem(device, self._borrowed_date, due_date, from_period, to_period)
        device.mark_as_borrowed()
        self._items.append(item)

    def return_device(self, device_id: str, returned_date: datetime) -> float:
        target_item = next((i for i in self._items if i.device.device_id == device_id), None)
        if target_item is None:
            raise DeviceNotInSlipException(device_id)

        target_item.return_device(returned_date)
        target_item.device.mark_as_available()
        return target_item.calculate_late_fee()

    def calculate_total_late_fee(self) -> float:
        return sum(item.calculate_late_fee() for item in self._items)


def main():
    print("=" * 65)
    print("Kiểm thử hệ thống quản lý mượn trả thiết bị phòng học")
    print("=" * 65)
    room_a101 = ClassRoom("A101", "Giảng đường A101", 120)

    proj_remote = ProjectorRemote("PRJ-01", "Điều khiển máy chiếu Sony", 2023, 500_000, max_borrow_days=2)
    ac_remote = AirConditionerRemote("AC-01", "Điều khiển điều hòa Daikin", 2019, 400_000, max_borrow_days=1, status=DeviceStatus.UNDER_MAINTENANCE)
    mic_wireless = Microphone("MIC-01", "Micro không dây Shure", 2024, 2_500_000, max_borrow_days=1)

    room_a101.add_device(proj_remote)
    room_a101.add_device(ac_remote)
    room_a101.add_device(mic_wireless)

    print(f"Tổng chi phí bảo trì dự kiến năm của {room_a101.room_name}: {room_a101.calculate_annual_maintenance_cost():,.0f} VNĐ")
    print("Các thiết bị cần bảo trì:")
    for dev in room_a101.get_devices_requiring_maintenance():
        print(f"  - {dev}")

    print("\n" + "=" * 65)
    print("Kiểm thử luồng nghiệp vụ mượn trả thiết bị")
    print("=" * 65)
    lecturer = Lecturer("GV001", "TS. Nguyễn Văn A")
    borrow_date = datetime(2026, 11, 10, 7, 30)
    slip1 = BorrowingSlip("PM-2026-001", lecturer, "A101", borrow_date)

    try:
        slip1.add_device(proj_remote, borrow_days=2, from_period=1, to_period=3)
        slip1.add_device(mic_wireless, borrow_days=1, from_period=1, to_period=3)
        print(f"Đã tạo phiếu {slip1.slip_id} cho {slip1.borrower.full_name} thành công với {len(slip1.items)} thiết bị.")

        fee1 = slip1.return_device("PRJ-01", datetime(2026, 11, 12, 10, 0))
        print(f"Trả PRJ-01 đúng hạn -> Phí phạt: {fee1:,.0f} VNĐ | Trạng thái mới: {proj_remote.status.value}")

        fee2 = slip1.return_device("MIC-01", datetime(2026, 11, 13, 10, 0))
        print(f"Trả MIC-01 muộn 2 ngày -> Phí phạt: {fee2:,.0f} VNĐ | Trạng thái mới: {mic_wireless.status.value}")

        print(f"=> Tổng phí phạt của phiếu {slip1.slip_id}: {slip1.calculate_total_late_fee():,.0f} VNĐ")
    except BorrowingException as ex:
        print(f"[LỖI NGHIỆP VỤ]: {ex}")

    print("\n" + "=" * 65)
    print("Kiểm thử ngoại lệ")
    print("=" * 65)
    ta = TeachingAssistant("TG001", "Trần Thị B")
    extra_dev1 = ProjectorRemote("PRJ-02", "Điều khiển máy chiếu Panasonic", 2024, 450_000, max_borrow_days=2)
    extra_dev2 = AirConditionerRemote("AC-02", "Điều khiển điều hòa LG", 2024, 350_000, max_borrow_days=2)
    slip2 = BorrowingSlip("PM-2026-002", ta, "B202", borrow_date)
    try:
        print("1. Thử mượn thiết bị đang bảo trì (AC-01):")
        slip2.add_device(ac_remote, borrow_days=1)
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")

    try:
        print("2. Thử cho Trợ giảng mượn thiết bị thứ 3:")
        slip2.add_device(proj_remote, borrow_days=1)   # Thiết bị 1 (Hợp lệ)
        slip2.add_device(extra_dev1, borrow_days=1)    # Thiết bị 2 (Hợp lệ)
        slip2.add_device(extra_dev2, borrow_days=1)    # Thiết bị 3 (Lỗi)
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")
        print(f"   -> Kiểm tra tính nhất quán: Trạng thái AC-02 vẫn là '{extra_dev2.status.value}', số lượng trên phiếu: {len(slip2.items)}")

    try:
        print("3. Thử thêm trùng thiết bị PRJ-01 vào cùng phiếu:")
        slip2.add_device(proj_remote, borrow_days=1)
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")

    try:
        print("4. Thử mượn MIC-01 trong 3 ngày (giới hạn 1 ngày):")
        slip3 = BorrowingSlip("PM-2026-003", lecturer, "C303", borrow_date)
        slip3.add_device(mic_wireless, borrow_days=3)
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")

    try:
        print("5. Thử trả thiết bị MIC-01 không nằm trong phiếu PM-2026-002:")
        slip2.return_device("MIC-01", datetime(2026, 11, 11))
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")

    try:
        print("6. Thử trả thiết bị PRJ-01 hai lần:")
        slip2.return_device("PRJ-01", datetime(2026, 11, 11))  # Lần 1: Thành công
        slip2.return_device("PRJ-01", datetime(2026, 11, 11))  # Lần 2: Lỗi
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")

    try:
        print("7. Thử trả PRJ-02 với ngày trả trước ngày mượn:")
        slip2.return_device("PRJ-02", datetime(2026, 11, 5))   # Ngày mượn là 10/11/2026
    except BorrowingException as e:
        print(f"   -> Bắt được ngoại lệ ({type(e).__name__}): {e}")
    finally:
        print("\n[FINALLY] Kết thúc quá trình kiểm thử hệ thống.")


if __name__ == "__main__":
    main()