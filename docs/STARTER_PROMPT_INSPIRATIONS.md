# Starter Prompt Inspirations

Use these when you want your coding agent to create, tighten, or recover
Odylith-owned repo truth.

If Odylith is installed locally, the Cheatsheet drawer in `odylith/index.html`
is the live source for these patterns.

## Good First Prompts

Use these when you want Odylith to take one concrete first step.

### Start

- Ground one real path:
  `Start Odylith and ground me in src/payments/service.py.`
- Recover a known component or workstream:
  `Show me the files and records for the payments component.`
- Search governed repo memory:
  `Search Odylith for benchmark proof posture.`

### Create

- Create a Radar backlog item:
  `Create a Radar backlog item titled "Payments boundary cleanup". Make it about clarifying that checkout can call payments but does not own payment state. Include goals to update the Registry component boundary, refresh the Atlas diagram, and leave a Compass note once the change lands. Add success criteria for one Registry update, one Atlas refresh, and one validation pass before closeout.`
- Create a Registry component:
  `Create a Registry component named "payments". Set its purpose to owning payment intent, provider routing, capture and refund state, and webhook reconciliation. Call out that checkout and orders depend on it, but payment state lives here. Include key interfaces for checkout requests, provider webhooks, and order-status updates.`
- Create an Atlas diagram:
  `Create an Atlas diagram for the payments component. Show checkout sending payment requests to payments, payments calling the external PSP, PSP webhooks returning into payments, and payments publishing status back to orders. Mark the PSP as an external boundary and label webhooks as inbound traffic.`
- Create a Casebook bug:
  `Create a Casebook bug titled "Duplicate payment capture after webhook retry". Record the symptom as two captures for one order after a delayed provider retry. Mark the suspected area as webhook idempotency in payments. Add first checks for provider event ids, retry logs, settlement records, and the exact order id that reproduced it.`

## Short-Form Patterns

Use these when you already know which Odylith surface you want to touch.

## Backlog

- Create: `Create a new backlog item and queue it for [codepath {or} backlog item description].`
- Edit: `Tighten the Radar item for [B###].`
- Delete: `Drop the Radar item [B###].`

## Components

- Create: `Define the Registry component for [component description].`
- Edit: `Tighten the Registry boundary for [component].`
- Delete: `Drop the Registry component for [component].`

## Diagrams

- Create: `Draw the Atlas diagram for [codepath].`
- Edit: `Update the Atlas diagram for [codepath].`
- Delete: `Drop the Atlas diagram [D###].`

## Developer Notes

- Create: `Add developer note [Note Brief].`
- Edit: `Update developer note [N###] with [...].`
- Delete: `Delete developer note [N###].`
