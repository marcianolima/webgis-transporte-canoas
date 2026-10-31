import { useRef } from "react";
import type { Vehicles } from "../types";
import { usePolling } from "./usePolling";

/** Só consulta a API HTTPS própria. Nenhum navegador acessa o HTTP da TACOM. */
export function useVehicles(
  apiBase: string | undefined,
  enabled: boolean,
  onUpdate: (value: Vehicles) => void,
) {
  const callback = useRef(onUpdate);
  callback.current = onUpdate;
  usePolling(
    async (signal) => {
      if (!apiBase) return;
      try {
        if (!/^https:\/\//i.test(apiBase) && !/^http:\/\/localhost(?::\d+)?$/i.test(apiBase))
          throw new Error("A API pública exige HTTPS");
        const response = await fetch(apiBase.replace(/\/$/, "") + "/v1/vehicles", {
          signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error("API indisponível");
        const data = (await response.json()) as Vehicles;
        if (!Array.isArray(data.vehicles) ||
            !["available", "reference", "unavailable"].includes(data.status))
          throw new Error("Contrato de veículos inválido");
        if (!signal.aborted) callback.current(data);
      } catch {
        if (!signal.aborted) {
          callback.current({
            status: "unavailable", generated_at: null, vehicles: [],
            message: "Falha de atualização da API. Não é possível inferir ausência de operação.",
          });
        }
      }
    },
    enabled && Boolean(apiBase),
    60_000,
    300_000,
  );
}
