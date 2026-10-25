"""Narrow runtime guard for binding a selected speaker to its MIOT target."""

from __future__ import annotations


class DeviceBindingError(RuntimeError):
    """A safe diagnostic that never includes account or device identifiers."""


def _numeric_did(value: object) -> str:
    if type(value) is int:
        value = str(value)
    if isinstance(value, str):
        value = value.strip()
        if 1 <= len(value) <= 32 and value.isascii() and value.isdecimal() and int(value) > 0:
            return value
    return ""


def build_speaker_class(upstream_class):
    """Keep upstream behavior except for rejecting uncertain MIOT mappings."""

    class BoundSpeaker(upstream_class):
        async def _resolve_mi_did(self, mina_devices):
            device = self.device
            if not isinstance(device, dict):
                raise DeviceBindingError("尚未明确选择音箱，已停止设备绑定。")
            direct = {_numeric_did(device.get(key)) for key in ("miotDID", "miotDid", "did")}
            direct.discard("")
            if len(direct) > 1:
                raise DeviceBindingError("音箱直接返回的 MIOT 标识相互冲突，已停止设备绑定。")
            if direct:
                return direct.pop()

            name = device.get("name")
            if not isinstance(name, str) or not name.strip() or not isinstance(mina_devices, list):
                raise DeviceBindingError("缺少可用于核对的唯一音箱名称，已停止设备绑定。")
            source_matches = [item for item in mina_devices if isinstance(item, dict) and item.get("name") == name]
            if len(source_matches) != 1:
                raise DeviceBindingError("账号中存在同名音箱；请先给目标设置唯一名称，再重试。")
            try:
                records = await self.miio.device_list("full")
            except Exception:
                raise DeviceBindingError("MIOT 设备列表查询失败，未启动音箱监听。") from None
            if not isinstance(records, list):
                raise DeviceBindingError("MIOT 设备列表格式异常，已停止设备绑定。")
            matches = [item for item in records if isinstance(item, dict) and item.get("name") == name]
            if len(matches) != 1:
                raise DeviceBindingError("无法在两个设备列表中唯一对应音箱名称；请核对改名是否同步后重试。")
            match = matches[0]
            if device.get("model") and match.get("model") and device["model"] != match["model"]:
                raise DeviceBindingError("设备名称对应的型号不一致，已停止设备绑定。")
            did = _numeric_did(match.get("did"))
            if not did:
                raise DeviceBindingError("匹配的音箱缺少数字 MIOT 标识，已停止设备绑定。")
            return did

    return BoundSpeaker
