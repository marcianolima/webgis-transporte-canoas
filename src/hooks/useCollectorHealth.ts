import { useState } from "react";
import { usePolling } from "./usePolling";

export interface CollectorHealth {
  status: string;
  last_run_at: string | null;
  accepted_last_run: number;
  rejected_last_run: number;
  source_diagnostics: {
    sampled_stops?: number;
    active_itineraries?: number;
    queried_itineraries?: number;
    requests?: number;
    failures?: number;
    rate_limited?: boolean;
    quota_exhausted?: boolean;
  };
  limitation: string;
}

/** Observabilidade agregada; só usa API própria HTTPS, sem dados GPS privados. */
export function useCollectorHealth(apiBase: string | undefined) {
  const [health, setHealth] = useState<CollectorHealth | null>(null);
  usePolling(async (signal) => {
    if (!apiBase || !/^https:\/\//i.test(apiBase)) return;
    try {
      const response = await fetch(apiBase.replace(/\/$/, "") + "/v1/health", {
        signal, cache: "no-store",
      });
      if (!response.ok) throw new Error("API não disponível");
      const value = (await response.json()) as CollectorHealth;
      if (typeof value.status !== "string" || !value.source_diagnostics ||
          typeof value.source_diagnostics !== "object") {
        throw new Error("Contrato de saúde inválido");
      }
      if (!signal.aborted) setHealth(value);
    } catch {
      if (!signal.aborted) setHealth(null);
    }
  }, Boolean(apiBase), 180_000, 900_000);
  return health;
}
