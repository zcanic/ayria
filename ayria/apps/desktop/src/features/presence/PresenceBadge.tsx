/**
 * Presence badge placeholder.
 *
 * This small component is strategically important.
 * It makes the invisible runtime state legible to the user.
 *
 * Minimum fields to display later:
 * - runtime connected/disconnected
 * - presence mode: idle/observing/chatting/busy/sleeping
 * - proactive enabled/disabled
 * - current active window summary
 */
export function PresenceBadge() {
  return `
    <section data-region="presence-badge">
      <strong>Presence</strong>
      <div id="presence-status">Mode: idle</div>
      <div id="runtime-health">Runtime: unknown</div>
    </section>
  `;
}
