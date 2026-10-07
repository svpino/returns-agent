# /// script
# requires-python = ">=3.11"
# dependencies = ["google-adk==2.6.0"]
# ///
"""One model context has both order-reading and refund capabilities.

uv run before.py --demo   # Inspect the capability boundary; no model/API key.
uv run before.py          # Live ADK execution; GOOGLE_API_KEY required.

All data/payments are fictional. Both scripts use the same common.py backend;
the comparison changes agent architecture, not refund correctness.
"""

import json

from google.adk.agents import Agent

from common import MODEL, REQUEST, Store, cli, run


def build_agent(store: Store) -> Agent:
    return Agent(
        name="return_agent", model=MODEL,
        instruction=(
            "You are the Return agent. Help with return requests. Look up the order. "
            "Check that the returned order_id matches the customer's requested ID; "
            "stop if it does not. For status requests, report warehouse_received "
            "separately from return_approved and refund_eligible. "
            "Refund only if refund_eligible is true. Report actual tool results."
        ),
        tools=[store.lookup_order, store.refund_order],
    )


async def workflow(store: Store, message: str):
    await run(build_agent(store), message)


def demo(store: Store):
    # Deterministic stand-in for a bad model decision; not a live injection test.
    print("Customer:", REQUEST)
    tools = {tool.__name__: tool for tool in build_agent(store).tools}
    order = tools["lookup_order"]("ORD-1001")
    print("Return status:", json.dumps({key: order[key] for key in (
        "return_approved", "warehouse_received", "refund_eligible",
    )}))
    tools["refund_order"]("ORD-1001")


if __name__ == "__main__":
    cli(workflow, demo, __doc__)
