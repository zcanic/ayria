/**
 * Chat panel placeholder.
 *
 * This feature eventually renders:
 * - user messages
 * - assistant messages
 * - proactive interruptions
 * - tool execution summaries
 * - retry / stop controls
 *
 * Important rule:
 * Do not bake API calling logic directly into view code.
 * UI should call a typed client from `src/lib/api`.
 *
 * Desired future UI regions:
 * - scrollable message list
 * - transient typing indicator
 * - proactive suggestion block with different styling
 * - tool activity trace
 * - input box with optional image attach affordance
 */
export function ChatPanel() {
  return `
    <section data-region="chat-panel">
      <h2>Chat</h2>
      <div data-region="messages">No messages yet.</div>
      <div data-region="composer">Input not wired yet.</div>
    </section>
  `;
}
