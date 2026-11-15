from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, List, Sequence


class DeviceStatus(Enum):
    AVAILABLE = "Available"
    BORROWED = "Borrowed"
    UNDER_MAINTENANCE = "UnderMaintenance"


class AlertSeverity(Enum):
    INFORMATION = "Information"
    WARNING = "Warning"
    CRITICAL = "Critical"


class InvalidDeviceReadingException(Exception):
    def __init__(self, device_id: str, invalid_value: int, message: str = ""):
        self.device_id = device_id
        self.invalid_value = invalid_value
        msg = message or f"Thiết bị '{device_id}' nhận giá trị đọc không hợp lệ: {invalid_value} (yêu cầu 0-100)."
        super().__init__(msg)


class Event:
    def __init__(self):
        self._handlers: List[Callable] = []

    def __iadd__(self, handler: Callable):
        if handler not in self._handlers:
            self._handlers.append(handler)
        return self

    def __isub__(self, handler: Callable):
        if handler in self._handlers:
            self._handlers.remove(handler)
        return self

    def _invoke(self, sender: object, args: object) -> None:
        for handler in list(self._handlers):
            handler(sender, args)


@dataclass(frozen=True)
class DeviceStatusChangedEventArgs:
    device_id: str
    old_status: DeviceStatus
    new_status: DeviceStatus
    changed_at: datetime


@dataclass(frozen=True)
class DeviceAlertEventArgs:
    device_id: str
    message: str
    severity: AlertSeverity
    occurred_at: datetime


class TeachingDevice(ABC):
    def __init__(self, device_id: str, name: str):
        self._id: str = device_id
        self._name: str = name
        self._status: DeviceStatus = DeviceStatus.AVAILABLE
        self.status_changed = Event()
        self.alert_raised = Event()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> DeviceStatus:
        return self._status

    def change_status(self, new_status: DeviceStatus) -> None:
        if new_status == self._status:
            return

        old_status = self._status
        self._status = new_status
        self._on_status_changed(
            DeviceStatusChangedEventArgs(
                device_id=self._id,
                old_status=old_status,
                new_status=new_status,
                changed_at=datetime.now()
            )
        )

    def _raise_alert(self, message: str, severity: AlertSeverity) -> None:
        self._on_alert_raised(
            DeviceAlertEventArgs(
                device_id=self._id,
                message=message,
                severity=severity,
                occurred_at=datetime.now()
            )
        )

    def _on_status_changed(self, e: DeviceStatusChangedEventArgs) -> None:
        self.status_changed._invoke(self, e)

    def _on_alert_raised(self, e: DeviceAlertEventArgs) -> None:
        self.alert_raised._invoke(self, e)


class ProjectorRemote(TeachingDevice):
    def __init__(self, device_id: str, name: str, initial_battery: int = 100):
        super().__init__(device_id, name)
        self._validate_reading(initial_battery)
        self._battery_level: int = initial_battery

    @property
    def battery_level(self) -> int:
        return self._battery_level

    def _validate_reading(self, value: int) -> None:
        if not (0 <= value <= 100):
            raise InvalidDeviceReadingException(self.id, value)

    def update_battery_level(self, new_level: int) -> None:
        self._validate_reading(new_level)
        old_level = self._battery_level
        self._battery_level = new_level

        if new_level == 0 and old_level > 0:
            self._raise_alert("Pin điều khiển máy chiếu đã cạn kiệt (0%)!", AlertSeverity.CRITICAL)
        elif 0 < new_level < 20 and old_level >= 20:
            self._raise_alert(f"Pin điều khiển máy chiếu xuống thấp ({new_level}%).", AlertSeverity.WARNING)


class AirConditionerRemote(TeachingDevice):
    def __init__(self, device_id: str, name: str, assigned_room: str):
        super().__init__(device_id, name)
        self._assigned_room: str = assigned_room
        self._is_responsive: bool = True

    @property
    def assigned_room(self) -> str:
        return self._assigned_room

    @property
    def is_responsive(self) -> bool:
        return self._is_responsive

    def update_response_state(self, is_responsive: bool) -> None:
        if self._is_responsive and not is_responsive:
            self._is_responsive = False
            self._raise_alert(
                f"Điều khiển điều hòa phòng {self._assigned_room} mất phản hồi!",
                AlertSeverity.CRITICAL
            )
        else:
            self._is_responsive = is_responsive


class WirelessMicrophone(TeachingDevice):
    def __init__(self, device_id: str, name: str, initial_battery: int = 100, initial_signal: int = 100):
        super().__init__(device_id, name)
        self._validate_reading(initial_battery)
        self._validate_reading(initial_signal)
        self._battery_level: int = initial_battery
        self._signal_quality: int = initial_signal

    @property
    def battery_level(self) -> int:
        return self._battery_level

    @property
    def signal_quality(self) -> int:
        return self._signal_quality

    def _validate_reading(self, value: int) -> None:
        if not (0 <= value <= 100):
            raise InvalidDeviceReadingException(self.id, value)

    def update_battery_level(self, new_level: int) -> None:
        self._validate_reading(new_level)
        old_level = self._battery_level
        self._battery_level = new_level

        if new_level == 0 and old_level > 0:
            self._raise_alert("Micro không dây hết pin (0%)!", AlertSeverity.CRITICAL)
        elif 0 < new_level < 30 and old_level >= 30:
            self._raise_alert(f"Pin micro không dây yếu ({new_level}%).", AlertSeverity.WARNING)

    def update_signal_quality(self, new_quality: int) -> None:
        self._validate_reading(new_quality)
        old_quality = self._signal_quality
        self._signal_quality = new_quality

        if new_quality == 0 and old_quality > 0:
            self._raise_alert("Micro không dây mất tín hiệu hoàn toàn (0%)!", AlertSeverity.CRITICAL)
        elif 0 < new_quality < 40 and old_quality >= 40:
            self._raise_alert(f"Chất lượng tín hiệu micro thấp ({new_quality}%).", AlertSeverity.WARNING)


class ConsoleNotificationService:
    def handle_alert(self, sender: object, e: DeviceAlertEventArgs) -> None:
        print(f"[{e.severity.value}] {e.device_id}: {e.message}")


class DeviceAuditLogger:
    def __init__(self):
        self._entries: List[str] = []

    @property
    def entries(self) -> Sequence[str]:
        return tuple(self._entries)

    def handle_status_changed(self, sender: object, e: DeviceStatusChangedEventArgs) -> None:
        timestamp = e.changed_at.strftime("%Y-%m-%d %H:%M:%S")
        self._entries.append(f"{timestamp}: {e.device_id}, {e.old_status.value} -> {e.new_status.value}")


class MaintenanceService:
    def __init__(self):
        self._requests: List[str] = []

    @property
    def requests(self) -> Sequence[str]:
        return tuple(self._requests)

    def handle_critical_alert(self, sender: object, e: DeviceAlertEventArgs) -> None:
        if e.severity != AlertSeverity.CRITICAL:
            return
        self._requests.append(f"Maintenance request for {e.device_id}: {e.message}")


AlertFilter = Callable[[DeviceAlertEventArgs], bool]
AlertAction = Callable[[DeviceAlertEventArgs], None]


class FilteredAlertSubscriber:
    def __init__(self, alert_filter: AlertFilter, action: AlertAction):
        self._filter = alert_filter
        self._action = action

    def handle_alert(self, sender: object, e: DeviceAlertEventArgs) -> None:
        if self._filter(e):
            self._action(e)


class DeviceMonitoringCoordinator:
    def __init__(
        self,
        devices: Sequence[TeachingDevice],
        notification_service: ConsoleNotificationService,
        audit_logger: DeviceAuditLogger,
        maintenance_service: MaintenanceService,
    ):
        self._devices = list(devices)
        self._notification_service = notification_service
        self._audit_logger = audit_logger
        self._maintenance_service = maintenance_service
        self._is_subscribed = False

    def subscribe(self) -> None:
        if self._is_subscribed:
            return
        for device in self._devices:
            device.status_changed += self._audit_logger.handle_status_changed
            device.alert_raised += self._notification_service.handle_alert
            device.alert_raised += self._maintenance_service.handle_critical_alert
        self._is_subscribed = True

    def unsubscribe(self) -> None:
        if not self._is_subscribed:
            return
        for device in self._devices:
            device.status_changed -= self._audit_logger.handle_status_changed
            device.alert_raised -= self._notification_service.handle_alert
            device.alert_raised -= self._maintenance_service.handle_critical_alert
        self._is_subscribed = False

    def dispose(self) -> None:
        self.unsubscribe()

    def __enter__(self):
        self.subscribe()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


if __name__ == "__main__":
    proj_remote = ProjectorRemote("PROJ-101", "Remote Máy chiếu P.101", initial_battery=80)
    ac_remote = AirConditionerRemote("AC-202", "Remote Điều hòa P.202", assigned_room="P.202")
    mic = WirelessMicrophone("MIC-303", "Micro không dây P.303", initial_battery=50, initial_signal=90)

    devices = [proj_remote, ac_remote, mic]

    console_service = ConsoleNotificationService()
    audit_logger = DeviceAuditLogger()
    maintenance_service = MaintenanceService()

    critical_sms_alerter = FilteredAlertSubscriber(
        alert_filter=lambda alert: alert.severity == AlertSeverity.CRITICAL,
        action=lambda alert: print(f"   >>> [GỬI SMS KHẨN CẤP] Thiết bị {alert.device_id}: {alert.message}")
    )
    mic.alert_raised += critical_sms_alerter.handle_alert

    print("=== BẮT ĐẦU GIÁM SÁT THIẾT BỊ ===\n")
    with DeviceMonitoringCoordinator(devices, console_service, audit_logger, maintenance_service) as coordinator:
        coordinator.subscribe()

        proj_remote.change_status(DeviceStatus.BORROWED)
        proj_remote.change_status(DeviceStatus.BORROWED)
        mic.change_status(DeviceStatus.BORROWED)

        proj_remote.update_battery_level(65)
        proj_remote.update_battery_level(15)

        ac_remote.update_response_state(False)
        ac_remote.update_response_state(False)

        mic.update_signal_quality(35)
        mic.update_battery_level(0)
        mic.change_status(DeviceStatus.UNDER_MAINTENANCE)

        try:
            proj_remote.update_battery_level(120)
        except InvalidDeviceReadingException as ex:
            print(f"\n[BẮT NGOẠI LỆ THÀNH CÔNG] {ex}")

    print("\n=== SAU KHI HỦY ĐĂNG KÝ (DISPOSE) ===")
    proj_remote.update_battery_level(0)

    print("\n--- LỊCH SỬ THAY ĐỔI TRẠNG THÁI (AUDIT LOG) ---")
    for entry in audit_logger.entries:
        print(" •", entry)

    print("\n--- DANH SÁCH YÊU CẦU BẢO TRÌ (MAINTENANCE) ---")
    for req in maintenance_service.requests:
        print(" •", req)