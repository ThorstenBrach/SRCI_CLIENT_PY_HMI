"""The option "Force Core functions" without a robot."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from srci.types import AxesGroup

from srci_py_hmi.robot import CORE_FUNCTIONS, ForceCoreFunctions, RobotService, Target


def initialized_group() -> AxesGroup:
    ag = AxesGroup()
    ag.State.Initialized = True
    return ag


def test_off_by_default() -> None:
    assert not Target().force_core


def test_core_list_is_table_5_2_with_a_bit() -> None:
    assert len(CORE_FUNCTIONS) == len(set(CORE_FUNCTIONS)) == 28
    bits = AxesGroup().State.RobotData.RCSupportedFunctions
    assert all(hasattr(bits, name) for name in CORE_FUNCTIONS)


def test_sets_the_core_bits_and_leaves_the_others() -> None:
    ag = initialized_group()
    bits = ag.State.RobotData.RCSupportedFunctions
    bits.MoveCircularAbsolute = True  # reported by the RC
    ForceCoreFunctions()(AxesGroup=ag)
    assert all(getattr(bits, name) is True for name in CORE_FUNCTIONS)
    assert bits.MoveCircularAbsolute is True
    assert bits.WaitTime is False  # profile Extended, not reported


def test_set_again_in_every_cycle() -> None:
    ag = initialized_group()
    block = ForceCoreFunctions()
    block(AxesGroup=ag)
    bits = ag.State.RobotData.RCSupportedFunctions
    bits.GroupJog = False  # the RobotTask copies the reported bits back
    block(AxesGroup=ag)
    assert bits.GroupJog is True


def test_nothing_before_the_initialization() -> None:
    ag = AxesGroup()
    block = ForceCoreFunctions()
    block(AxesGroup=ag)
    assert ag.State.RobotData.RCSupportedFunctions.GroupJog is False
    assert not block.active


def test_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    ag = initialized_group()
    block = ForceCoreFunctions()
    with caplog.at_level(logging.WARNING, logger="srci_py_hmi.robot"):
        block(AxesGroup=ag)
        block(AxesGroup=ag)
    assert len([r for r in caplog.records if "forced" in r.message]) == 1


@pytest.mark.parametrize("force", [False, True])
def test_supported_between_two_cycles(force: bool) -> None:
    """Outside of the cycle the AxesGroup holds what the RC reports."""
    ag = AxesGroup()
    ag.State.RobotData.RCSupportedFunctions.ReadRobotData = True
    service = RobotService()
    service._client = SimpleNamespace(  # type: ignore[assignment]
        program=SimpleNamespace(initialized=True, axes_group=ag)
    )
    service._force_core = force
    known = service.supported()
    assert known is not None
    assert (set(CORE_FUNCTIONS) <= known) is force
    service._client = None
