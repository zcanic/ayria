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
      <div id="settings-provider">Provider: local-first</div>
      <div id="settings-proactive">Proactive: unknown</div>
      <div id="settings-persona">Persona intensity: normal</div>
      <label>
        <span>Proactive</span>
        <input id="settings-proactive-toggle" type="checkbox" />
      </label>
      <label>
        <span>Persona</span>
        <select id="settings-persona-select">
          <option value="low">low</option>
          <option value="normal" selected>normal</option>
          <option value="high">high</option>
        </select>
      </label>
      <label>
        <span>Safe read policy</span>
        <select id="settings-safe-policy-select">
          <option value="allow" selected>allow</option>
          <option value="ask">ask</option>
          <option value="deny">deny</option>
        </select>
      </label>
      <label>
        <span>External read policy</span>
        <select id="settings-external-policy-select">
          <option value="allow">allow</option>
          <option value="ask" selected>ask</option>
          <option value="deny">deny</option>
        </select>
      </label>
      <label>
        <span>Sensitive read policy</span>
        <select id="settings-sensitive-policy-select">
          <option value="allow">allow</option>
          <option value="ask" selected>ask</option>
          <option value="deny">deny</option>
        </select>
      </label>
      <label>
        <span>Action policy</span>
        <select id="settings-action-policy-select">
          <option value="allow">allow</option>
          <option value="ask">ask</option>
          <option value="deny" selected>deny</option>
        </select>
      </label>
      <label>
        <span>Proactive mode</span>
        <select id="settings-proactive-mode-select">
          <option value="quiet">quiet</option>
          <option value="balanced" selected>balanced</option>
          <option value="active">active</option>
        </select>
      </label>
      <button id="settings-save-button" type="button">Apply Settings</button>
    </section>
  `;
}
