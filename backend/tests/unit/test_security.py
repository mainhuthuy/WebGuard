"""Unit tests cho kiểm tra chống SSRF qua phân giải DNS."""

import socket

import pytest

from app.core import InvalidTargetException, assert_public_target, security


def _resolve_to(monkeypatch: pytest.MonkeyPatch, *addresses: str) -> None:
    async def fake(hostname: str) -> list[str]:
        return list(addresses)

    monkeypatch.setattr(security, "_resolve", fake)


async def test_public_address_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    _resolve_to(monkeypatch, "93.184.216.34")
    await assert_public_target("https://example.com")


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "192.168.1.10", "172.16.0.1", "169.254.169.254", "::1", "fe80::1"],
)
async def test_non_public_address_is_blocked(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    _resolve_to(monkeypatch, address)
    with pytest.raises(InvalidTargetException):
        await assert_public_target("https://sneaky.example.com")


async def test_blocked_if_any_resolved_address_is_internal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resolve_to(monkeypatch, "93.184.216.34", "10.0.0.1")
    with pytest.raises(InvalidTargetException):
        await assert_public_target("https://mixed.example.com")


async def test_unresolvable_host_is_not_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(hostname: str) -> list[str]:
        raise socket.gaierror("nope")

    monkeypatch.setattr(security, "_resolve", fail)
    await assert_public_target("https://does-not-exist.invalid")


async def test_missing_hostname_is_rejected() -> None:
    with pytest.raises(InvalidTargetException):
        await assert_public_target("https://")
