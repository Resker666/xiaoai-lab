"""Offline checks for selecting the same speaker across Xiaomi services."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from xiaoai_lab.device_binding import DeviceBindingError, build_speaker_class


class DeviceBindingTests(unittest.IsolatedAsyncioTestCase):
    def speaker(self, device=None, miio_devices=None):
        speaker = build_speaker_class(object)()
        speaker.device = device or {"deviceID": "sample-selected", "name": "experiment-speaker", "model": "speaker-model"}
        speaker.miio = SimpleNamespace(device_list=AsyncMock(return_value=miio_devices or []))
        return speaker

    async def test_same_model_does_not_select_other_speaker_before_unique_name(self):
        speaker = self.speaker(miio_devices=[
            {"did": "101", "name": "other-speaker", "model": "speaker-model"},
            {"did": "202", "name": "experiment-speaker", "model": "speaker-model"},
        ])
        result = await speaker._resolve_mi_did([speaker.device, {"name": "other-speaker"}])
        self.assertEqual(result, "202")
        speaker.miio.device_list.assert_awaited_once_with("full")

    async def test_direct_numeric_binding_needs_no_other_service(self):
        for field in ("miotDID", "miotDid", "did"):
            with self.subTest(field=field):
                speaker = self.speaker(device={"deviceID": "sample-selected", field: "202"})
                self.assertEqual(await speaker._resolve_mi_did([speaker.device]), "202")
                speaker.miio.device_list.assert_not_awaited()

    async def test_duplicate_source_names_stop_before_another_account_query(self):
        speaker = self.speaker()
        with self.assertRaises(DeviceBindingError):
            await speaker._resolve_mi_did([speaker.device, {"name": speaker.device["name"]}])
        speaker.miio.device_list.assert_not_awaited()

    async def test_ambiguous_missing_or_conflicting_destination_is_rejected(self):
        for matches in (
            [],
            [{"name": "other-speaker", "model": "speaker-model", "did": "101"}],
            [{"name": "experiment-speaker", "did": "101"}, {"name": "experiment-speaker", "did": "202"}],
            [{"name": "experiment-speaker", "model": "different-model", "did": "202"}],
            [{"name": "experiment-speaker", "did": "not-a-numeric-did"}],
        ):
            with self.subTest(matches=matches):
                speaker = self.speaker(miio_devices=matches)
                with self.assertRaises(DeviceBindingError) as caught:
                    await speaker._resolve_mi_did([speaker.device])
                for private in ("sample-selected", "experiment-speaker", "101", "202"):
                    self.assertNotIn(private, str(caught.exception))

    async def test_missing_model_is_supported_when_names_uniquely_match(self):
        speaker = self.speaker(device={"deviceID": "sample-selected", "name": "experiment-speaker", "model": None}, miio_devices=[{"name": "experiment-speaker", "did": 202}])
        self.assertEqual(await speaker._resolve_mi_did([speaker.device]), "202")

    async def test_conflicting_direct_bindings_are_not_resolved_by_order(self):
        speaker = self.speaker(device={"deviceID": "sample-selected", "miotDID": "101", "did": "202"})
        with self.assertRaises(DeviceBindingError):
            await speaker._resolve_mi_did([speaker.device])
        speaker.miio.device_list.assert_not_awaited()

    async def test_query_failure_is_sanitized(self):
        speaker = self.speaker()
        speaker.miio.device_list.side_effect = RuntimeError("PRIVATE_TOKEN PRIVATE_USERNAME")
        with self.assertRaises(DeviceBindingError) as caught:
            await speaker._resolve_mi_did([speaker.device])
        self.assertNotIn("PRIVATE_", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
