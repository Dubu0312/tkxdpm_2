import "./style.css";
import { fetchHealth } from "./api";
import { API_BASE_URL } from "./env";

const app = document.querySelector<HTMLDivElement>("#app");

async function render(): Promise<void> {
  if (!app) return;

  app.innerHTML = `
    <main>
      <h1>tkxdpm_2</h1>
      <p>Round 0 — development environment only, no features yet.</p>
      <p>Backend: <code>${API_BASE_URL}</code></p>
      <p id="status">Checking backend…</p>
    </main>
  `;

  const status = app.querySelector<HTMLParagraphElement>("#status");
  if (!status) return;

  try {
    const health = await fetchHealth();
    status.textContent = `Backend: ${health.status} · database: ${health.database}`;
  } catch (error) {
    status.textContent = `Backend unreachable (${
      error instanceof Error ? error.message : String(error)
    })`;
  }
}

void render();
