"""Commands beside a running EnableRobot, without a robot."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest

from srci_py_hmi import robot as robot_module
from srci_py_hmi.robot import Activity, RobotService


@pytest.fixture
def busy() -> Iterator[RobotService]:
    """A service with a command sequence that ends after 0.3 s."""
    service = RobotService()
    holding, done = threading.Event(), threading.Event()

    def hold() -> None:
        with service._busy:
            holding.set()
            time.sleep(0.3)
        done.set()

    threading.Thread(target=hold, daemon=True).start()
    holding.wait(1.0)
    yield service
    done.wait(2.0)


def test_enable_may_take_as_long_as_after_an_emergency_stop() -> None:
    assert robot_module.ENABLE_TIME >= 20.0  # JAKA SRCI User Manual V3, EnableRobot


def test_no_long_wait_for_other_commands(busy: RobotService) -> None:
    assert not busy._acquire(0.01, True)


def test_reading_waits_for_a_running_enable(busy: RobotService) -> None:
    busy._enabling = True
    assert busy._acquire(0.01, True)
    busy._busy.release()


def test_motion_does_not_wait_for_a_running_enable(busy: RobotService) -> None:
    busy._enabling = True
    assert not busy._acquire(0.01, False)


def test_motion_sequence_is_not_patient(busy: RobotService) -> None:
    busy._enabling = True
    with pytest.raises(Exception, match="another command"), busy._command("Move", Activity.MOVING, wait=0.01):
        pass


def test_second_request_to_switch_on_is_ignored() -> None:
    service = RobotService()
    service._enabling = True
    service.set_enabled(True)  # no error, "not connected" would be raised otherwise
    assert service._enabling


def test_enabling_flag_ends_with_an_error() -> None:
    service = RobotService()
    with pytest.raises(Exception):  # noqa: B017 - not connected
        service.set_enabled(True)
    assert not service._enabling
