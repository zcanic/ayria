import { ChatPanel } from '../features/chat/ChatPanel';
import { PresenceBadge } from '../features/presence/PresenceBadge';
import { SettingsPage } from '../features/settings/SettingsPage';

/**
 * High-level desktop shell.
 *
 * Keep this component thin.
 * It should compose feature modules rather than own business logic.
 *
 * Recommended child regions:
 * - status bar: runtime health, active model, presence mode
 * - main panel: chat and proactive messages
 * - side panel: world state and debug data
 * - settings entry: privacy, providers, persona intensity
 *
 * Product guidance:
 * The UI should make the runtime legible.
 * Users need to understand what ayria is seeing, when it is active, and why it
 * responded. Do not hide all system state behind a cute chat surface.
 */
export function App() {
  return `
    <main data-app="ayria">
      <header>
        <h1>ayria v1</h1>
        ${PresenceBadge()}
        <div id="transport-status">Events: polling mode</div>
      </header>
      <section>
        ${ChatPanel()}
      </section>
      <aside>
        <h2>World State</h2>
        <pre id="world-state">Loading...</pre>
      </aside>
      <footer>
        ${SettingsPage()}
      </footer>
    </main>
  `;
}
