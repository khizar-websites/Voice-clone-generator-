"""Generic Zapier connector tool runner: executes one Zapier MCP tool per run.

Used for the YouTube shorts upload: discover/enable/execute calls are passed
through verbatim so each run costs exactly one Zapier action when executing.
"""

from typing import Any

import pydantic
import mistralai.workflows as workflows
from mistralai.workflows import Depends
from mistralai.workflows.plugins.mistralai.connectors import (
    ConnectorClient,
    connector,
    uses_connectors,
)

zapier = connector("zapier_62ee")


class ZapierToolCallInput(pydantic.BaseModel):
    tool: str
    arguments: dict[str, Any]


@workflows.activity(name="call-zapier-tool")
async def call_zapier_tool(
    tool: str,
    arguments: dict[str, Any],
    client: ConnectorClient = Depends(zapier),
) -> Any:
    return await client.call_tool(tool_name=tool, arguments=arguments)


@workflows.workflow.define(name="zapier-tool-runner", on_behalf_of=True)
@uses_connectors(zapier)
class ZapierToolRunnerWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, prompt: ZapierToolCallInput) -> Any:
        return await call_zapier_tool(prompt.tool, prompt.arguments)
