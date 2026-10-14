"""Live publication, polling, and concurrent investigation checks."""

import asyncio
import unittest

from simulation.live import LiveSimulation
from simulation.scenario_loader import load_scenarios
from src.evaluation.live_validation import validate_mode_b


class ModeBValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_pollers_receive_coherent_snapshots(self):
        report = await validate_mode_b(interval_seconds=0.03,
                                       poll_interval_seconds=0.005, clients=4)
        self.assertTrue(report["passed"], report["checks"])
        self.assertEqual(report["published_minutes"], tuple(range(0, 40, 5)))
        self.assertGreaterEqual(report["max_in_flight"], 2)
        self.assertEqual({item["client"] for item in report["observations"]}, set(range(4)))

    async def test_publication_is_delayed_and_future_events_are_hidden(self):
        scenario = load_scenarios()["SIM-004"]
        async with LiveSimulation(scenario, interval_seconds=0.04) as live:
            self.assertEqual(live.published_minutes, (0,))
            engine = live.snapshot()
            self.assertEqual(len(engine.scenario.events), 1)
            self.assertEqual(engine.metrics(scenario.incident["server_id"])["samples"][-1]["minute"], 0)
            self.assertEqual(await asyncio.wait_for(live.wait_for_change(0), 1), 5)
            self.assertEqual(live.snapshot().scenario.events[-1]["minute"], 5)
            self.assertEqual(engine.scenario.events[-1]["minute"], 0)

    async def test_stopping_wakes_waiters_and_rejects_restart(self):
        scenario = load_scenarios()["SIM-004"]
        live = LiveSimulation(scenario, interval_seconds=1)
        with self.assertRaises(RuntimeError):
            live.snapshot()
        await live.start()
        waiter = asyncio.create_task(live.wait_for_change(0))
        await live.stop()
        self.assertIsNone(await waiter)
        with self.assertRaises(RuntimeError):
            await live.start()

    async def test_invalid_configuration(self):
        scenario = load_scenarios()["SIM-004"]
        for interval in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                LiveSimulation(scenario, interval)
        with self.assertRaises(ValueError):
            await validate_mode_b(clients=1)
        with self.assertRaises(ValueError):
            await validate_mode_b(poll_interval_seconds=0)

    async def test_tool_failure_and_policy_remain_visible_to_live_poll(self):
        scenarios = load_scenarios()
        async with LiveSimulation(scenarios["SIM-016"], interval_seconds=1) as live:
            poll = await live.poll()
            self.assertEqual(
                {result.error_code for result in poll.state.tool_results},
                {None, "permission_denied"})
        async with LiveSimulation(scenarios["SIM-012"], interval_seconds=0.04) as live:
            self.assertEqual(await asyncio.wait_for(live.wait_for_change(5), 1), 10)
            poll = await live.poll()
            self.assertEqual(poll.minute, 10)
            self.assertIn("timeout", {result.error_code for result in poll.state.tool_results})
