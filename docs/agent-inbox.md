# Agent Inbox & Live Conversation Manager (Phase 7)

The **Agent Inbox** provides support agents, managers, and business owners with real-time visibility into customer conversations across all websites, complete with automated RAG tool traces and human takeover capabilities.

---

## 1. Conversation Lifecycle & Statuses

```
[ Visitor Starts Chat ]
         │
         ▼
 ┌───────────────┐
 │  BOT_ACTIVE   │ ◄─── (Automated AI RAG responses active)
 └───────┬───────┘
         │
         ├─▶ Visitor asks for human / low confidence ──▶ [ WAITING_HUMAN ]
         │                                                       │
         ├─▶ Agent sends manual reply via Inbox ─────────────────┤
         │                                                       ▼
         │                                             ┌───────────────────┐
         │                                             │  HUMAN_TAKEOVER   │ (AI bot paused)
         │                                             └─────────┬─────────┘
         │                                                       │
         ├─▶ Agent clicks "Resume AI Bot" ───────────────────────┤
         │                                                       ▼
         └─▶ Agent/Visitor completes inquiry ──────────▶ [     CLOSED      ]
```

| Status | Description | AI Behavior |
| :--- | :--- | :--- |
| `BOT_ACTIVE` | Default active conversation state. | Automated Local LLM RAG responses generated. |
| `WAITING_HUMAN` | Visitor requested human support or WhatsApp handoff. | AI bot still active, but flagged in Inbox queue with amber badge. |
| `HUMAN_TAKEOVER` | Support agent took over the thread or sent an agent reply. | AI bot is **paused**; visitor receives a system notice while waiting for agent. |
| `CLOSED` | Conversation resolved or archived. | Session preserved for reporting and transcripts. New visitor messages reopen session. |

---

## 2. Human Agent Takeover

Agents can take over any conversation with a single click or simply by typing a message into the **Agent Reply Composer**:
- When an agent replies, the message is stored with `sender: "AGENT"`.
- The conversation status automatically transitions to `HUMAN_TAKEOVER`.
- The session is assigned to the replying agent (`assigned_user_id`).
- When the inquiry is solved, the agent can click **"Resume AI Bot"** or **"Close Conversation"**.

---

## 3. REST API Reference (`/api/v1/conversations`)

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/conversations?org_id={id}&website_id=...&status=...&search=...` | List paginated conversations with latest message preview | `VIEWER`+ |
| `GET` | `/api/v1/conversations/{session_id}?org_id={id}` | Retrieve full chronological message transcript and visitor metadata | `VIEWER`+ |
| `PUT` | `/api/v1/conversations/{session_id}/status?org_id={id}` | Change conversation status (`BOT_ACTIVE`, `HUMAN_TAKEOVER`, `CLOSED`) | `AGENT`+ |
| `POST` | `/api/v1/conversations/{session_id}/agent-reply?org_id={id}` | Send a human agent reply directly into the visitor chat stream | `AGENT`+ |
| `PUT` | `/api/v1/conversations/{session_id}/assign?org_id={id}` | Assign conversation to a team member | `AGENT`+ |
