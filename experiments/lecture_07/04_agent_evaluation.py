"""Evaluate a real fixture-backed agent run with the mock backend."""

import json
from src.agents.runtime import IncidentAgent
from src.evaluation.agent_evaluator import AgentCase, ExpectedCall, evaluate_agent_state


if __name__ == "__main__":
    case = AgentCase("incident-001", "Investigate INC-001",
                     (ExpectedCall("get_incident", {"incident_id": "INC-001"}),),
                     ("database connection pool", "slow queries"))
    state = IncidentAgent().run(case.request)
    print(json.dumps(evaluate_agent_state(case, state), indent=2))
