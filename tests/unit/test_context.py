import unittest

from src.context.manager import ContextManager
from src.context.token_budget import ContextBudget, ContextBudgetExceeded, TokenCounter


class ContextTests(unittest.TestCase):
    def test_counter_and_truncation(self):
        counter = TokenCounter()
        self.assertEqual(counter.count("CPU: 95%"), 4)
        self.assertLessEqual(counter.count(counter.truncate("one two three four", 2)), 3)

    def test_long_history_fits_and_keeps_critical_fact(self):
        manager = ContextManager(ContextBudget(
            total_tokens=300, reserved_output_tokens=60, max_tool_output_tokens=15))
        conversation = [{"role": "user" if n % 2 else "assistant",
                         "content": f"Turn {n}: " + "detail " * 30}
                        for n in range(20)]
        tools = [{"name": "incident_record", "ok": True, "content": "log " * 400}]
        managed = manager.build("Investigate INC-001", conversation, tools,
                                ["Database pool utilization 95%"])
        self.assertLessEqual(managed.estimated_tokens, managed.input_budget)
        self.assertIn("Database pool utilization 95%", managed.prompt)
        self.assertIn("Current request: Investigate INC-001", managed.prompt)
        self.assertGreater(managed.summarized_turns, 0)
        self.assertNotIn("log " * 100, managed.prompt)

    def test_critical_facts_cannot_be_silently_dropped(self):
        manager = ContextManager(ContextBudget(30, 10))
        with self.assertRaises(ContextBudgetExceeded):
            manager.build("Investigate INC-001", [], [],
                          ["important " * 100])
