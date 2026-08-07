import unittest

from shlex import join

from coding_agents.parser import parse_headers
from coding_agents.supervisor.controller import AgentRunResult, supervise
from coding_agents.provider_adapter import build_agent_command, InvocationPolicy

class CodingAgentsTestCase(unittest.TestCase):
    def test_parser(self):
        sample = "Host: example.com\n\nAccept: application/json"

        try:
            h = parse_headers(sample)
            self.assertEqual(h.get("host"), "example.com")
            print("reproduction_status=passed")
        except Exception as exc:
            print("reproduction_status=failed")
            print(f"error_type={type(exc).__name__}")
            print(f"error={exc}")
            self.fail(f"Failed to parse headers: {exc}")


    def test_adapter(self):
        policy = InvocationPolicy()
        prompt = (
            "Reproduce the parser bug. Do not claim completion. "
            "Return the failing command and evidence."
        )

        for provider in ("claude", "codex"):
            command = build_agent_command(provider, prompt, policy)
            print(f"{provider}_command={join(command)}")
            self.assertTrue(command)

        ## claude_command=claude -p --output-format json --max-turns 6 --max-budget-usd 3.00 --allowedTools Read Edit Bash 'Reproduce the parser bug. Do not claim completion. Return the failing command and evidence.'
        ## codex_command=codex exec --json --sandbox workspace-write 'Reproduce the parser bug. Do not claim completion. Return the failing command and evidence.'

    def test_adapter_with_sandbox(self):
        pass

    def test_supervisory_agent(self):
        result = AgentRunResult(
            provider="codex",
            claimed_complete=True,
            changed_files=(),
            summary="The parser task appears complete.",
        )
        decision, reason = supervise(result)
        self.assertEqual(decision, "replan")
        self.assertEqual(reason, "completion claim rejected; ValueError:not enough values to unpack (expected 2, got 1)")
        self.assertEqual(result.provider, "codex")
        self.assertEqual(result.claimed_complete, True)
        self.assertIsNotNone(result.changed_files, "")
        self.assertEqual(result.summary, "The parser task appears complete.")

if __name__ == '__main__':
    unittest.main()
