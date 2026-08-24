import { API_BASE_URL } from "./env";

export interface HealthResponse {
  status: string;
  database: string;
  detail: string | null;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
