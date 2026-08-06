import { describe, expect, it } from "vitest";

import { createTraceClient } from "../src/traces/traceClient";

describe("Trace client", () => {
  it("serializes filters, sends bearer auth, and loads one Trace detail", async () => {
    const requests: Array<{ input: RequestInfo | URL; init: RequestInit }> = [];
    const client = createTraceClient({
      baseUrl: "http://127.0.0.1:8000",
      getAccessToken: () => "token-1",
      fetchImpl: async (input, init) => {
        requests.push({ input, init: init ?? {} });
        const data = input.toString().includes("trace_1")
          ? { trace: trace(), spans: [span()] }
          : { items: [trace()] };
        return new Response(JSON.stringify({ ok: true, data, meta: { requestId: "req_1" } }), {
          headers: { "content-type": "application/json" },
          status: 200
        });
      }
    });

    const list = await client.listTraces({ executionType: "chat", status: "succeeded", limit: 25 });
    const detail = await client.getTrace("trace_1");

    expect(list.items[0]?.id).toBe("trace_1");
    expect(detail.spans[0]?.id).toBe("span_1");
    expect(requests[0]?.input.toString()).toBe(
      "http://127.0.0.1:8000/agent-traces?executionType=chat&status=succeeded&limit=25"
    );
    expect(requests[1]?.input.toString()).toBe("http://127.0.0.1:8000/agent-traces/trace_1");
    expect(new Headers(requests[0]?.init.headers).get("Authorization")).toBe("Bearer token-1");
  });
});

function trace() {
  return {
    id: "trace_1",
    executionType: "chat" as const,
    resourceType: "chat_session",
    resourceId: "chat_1",
    requestId: "req_1",
    status: "succeeded" as const,
    summary: "Chat completed",
    errorCategory: null,
    metadata: {},
    startedAt: "2026-08-06T00:00:00.000Z",
    completedAt: "2026-08-06T00:00:01.000Z",
    durationMs: 1000
  };
}

function span() {
  return {
    id: "span_1",
    traceId: "trace_1",
    parentSpanId: null,
    externalId: null,
    sequence: 1,
    kind: "agent" as const,
    name: "chat.agent",
    status: "succeeded" as const,
    summary: "Agent completed",
    attributes: {},
    startedAt: "2026-08-06T00:00:00.000Z",
    completedAt: "2026-08-06T00:00:01.000Z",
    durationMs: 1000
  };
}
