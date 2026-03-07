/**
 * Settings page placeholder.
 *
 * This must expose privacy-sensitive controls clearly.
 * Weak agents often under-spec privacy UI. Do not do that here.
 *
 * Required setting groups for v1:
 * - model/provider selection
 * - proactive behavior
 * - screenshot capture policy
 * - blacklisted applications
 * - cloud fallback permissions
 * - persona intensity
 */
export function SettingsPage() {
  return `
    <section data-region="settings">
      <h2>Settings</h2>
      <ul>
        <li id="settings-provider">Provider: local-first</li>
        <li id="settings-proactive">Proactive: unknown</li>
        <li id="settings-persona">Persona intensity: normal</li>
      </ul>
    </section>
  `;
}
