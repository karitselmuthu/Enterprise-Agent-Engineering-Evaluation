import unittest

from src.agents.runtime import IncidentAgent
from src.agents.state import AgentState
from src.evaluation.agent_evaluator import AgentCase, ExpectedCall, evaluate_agent_state
from src.tools.executor import ToolResult


class AgentEvaluationTests(unittest.TestCase):
    def test_actual_incident_run(self):
        case = AgentCase("incident", "Investigate INC-001",
                         (ExpectedCall("get_incident", {"incident_id": "INC-001"}),),
                         ("database connection pool", "slow queries"))
        result = evaluate_agent_state(case, IncidentAgent().run(case.request))
        self.assertTrue(result["tool_selection_correct"])
        self.assertTrue(result["trajectory_exact"])
        self.assertTrue(result["execution_success"])
        self.assertEqual(result["answer_term_recall"], 1)

    def test_wrong_arguments_and_denied_execution(self):
        case = AgentCase("x", "q", (ExpectedCall("safe", {"id": "1"}),), ())
        state = AgentState("q", [ToolResult("safe", False, error_code="permission_denied")],
                           [{"stage": "selection", "tool": "safe", "arguments": {"id": "2"}},
                            {"stage": "execution", "tool": "safe", "ok": False,
                             "error_code": "permission_denied"}])
        result = evaluate_agent_state(case, state)
        self.assertFalse(result["tool_selection_correct"])
        self.assertFalse(result["trajectory_exact"])
        self.assertFalse(result["execution_success"])
        self.assertTrue(result["permission_violation"])

    def test_missing_tool_is_detected(self):
        case = AgentCase("x", "q", (ExpectedCall("safe", {}),), ())
        result = evaluate_agent_state(case, AgentState("q"))
        self.assertFalse(result["trajectory_exact"])
        self.assertFalse(result["tool_selection_correct"])
