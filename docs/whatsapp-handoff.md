# WhatsApp Human Handoff Bridge Guide (Phase 9)

The **WhatsApp Human Handoff Bridge** allows AI Customer & Commerce Assistant chatbots to hand off visitors smoothly to human support staff on WhatsApp with rich context summaries pre-filled into the chat thread.

---

## 1. Handoff Flow & Deep-Linking Architecture

```
[ Customer Inquiry / Escalation Request ]
                    │
                    ▼
          [ ToolSelectionEngine ]
                    │
     Intent: ESCALATE_HUMAN ("Talk to agent")
                    │
                    ▼
       [ WhatsAppHandoffService ]
                    │
   1. Normalizes phone digits (e.g. +1 (555) 123-4567 ➔ 15551234567)
   2. Interpolates message template variables:
      {store_name}, {visitor_id}, {session_id}, {last_inquiry}
   3. Constructs deep link: https://wa.me/{clean_phone}?text={encoded_text}
                    │
                    ▼
   [ Action Button Delivered to Visitor in Widget ]
                    │
                    ▼
 [ One-Click Launch of WhatsApp App / Web with Pre-Filled Inquiry ]
```

---

## 2. Supported Template Variables

Business owners can customize the pre-filled inquiry text using these template tags:

| Variable | Description | Example Output |
| :--- | :--- | :--- |
| `{store_name}` | Name of the website/store | `Apex Outfitters` |
| `{website_name}` | Alias for store name | `Apex Outfitters` |
| `{visitor_id}` | Unique visitor session identifier | `vis_usr_892` |
| `{session_id}` | Short session code | `89a1c4` |
| `{last_inquiry}` | The customer's last question or request | `Do you offer express shipping to Canada?` |

### Default Message Template
```text
Hello {store_name}, I was chatting with your AI assistant (Visitor: {visitor_id}) regarding: "{last_inquiry}". Could a human support agent please assist me?
```

---

## 3. Trigger & Visibility Modes

| Mode | Behavior |
| :--- | :--- |
| `ON_ESCALATION` | WhatsApp handoff button appears dynamically in the chat stream when customer asks for a human agent or AI model confidence is low. |
| `ALWAYS_VISIBLE` | Displays a persistent WhatsApp click-to-chat action button in the widget header at all times, plus renders escalation buttons when requested. |
| `DISABLED` | Disables WhatsApp buttons across the chatbot widget. |

---

## 4. REST API Reference

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/websites/{website_id}/whatsapp-preview?org_id={id}` | Generate live WhatsApp deep link preview and formatted text | `VIEWER`+ |
| `PUT` | `/api/v1/websites/{website_id}/settings?org_id={id}` | Update WhatsApp number, template, and trigger modes | `ADMIN`+ |
