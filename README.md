# Enterprise-Agent-Engineering-Evaluation
# 1. Project overview
  Attribute	         Recommendation
  Repository name	   Enterprise_Agent_Evaluation
  Project type	     Enterprise AI Agent Engineering & Evaluation
  Architecture	     Modular, tool-driven agent framework
  Primary language	 Python
  LLM backend	       Small local model or configurable external provider
  API	               FastAPI
  CLI	               Python CLI
  Testing	           pytest
  Deployment	       Docker
  Development HW	   Apple Silicon Mac, 8 GB RAM
  Implementation 	   Incremental, experiment-driven
# Enterprise problem statement
  Enterprise organizations increasingly use AI agents to automate operational workflows, retrieve information, execute tools, and assist with technical investigations.
  However, building an AI agent is different from deploying a reliable enterprise agent.
  Common challenges include:
    - Unreliable tool execution.
    - Incorrect tool selection.
    - Loss of context during long conversations.
    - Inconsistent memory retrieval.
    - Poor handling of tool failures.
    - Unverified agent-generated recommendations.
    - Difficulty measuring agent performance.
    - Security risks from unrestricted tool execution.
# Proposed solution
  Build an Enterprise IT Operations Agent capable of investigating infrastructure and application incidents using controlled tools.
  The platform will demonstrate how agents plan actions, execute tools, maintain context, retrieve information, and produce recommendations.

# Example use case
  User request:
  "Investigate why the production application is experiencing high latency."

## Implementation status

Phase 6.1 provides a working tool-enabled incident agent with schema checks,
permissions, execution traces, timeout reporting, and a local Ollama adapter.
The default backend works offline with sample fixtures.

Run `PYTHONPATH=. python3 scripts/run_agent.py INC-001` and
`python3 -m unittest discover -s tests -p 'test_*.py' -v`.
See [Lecture 06](docs/lecture_06_agents.md) for phase details.

Phase 6.2 adds an MCP server and a permission-aware MCP client. Install the
project with `python3 -m pip install -e .` before running the MCP experiment.
