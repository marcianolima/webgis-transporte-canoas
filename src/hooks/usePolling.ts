import { useEffect, useRef } from "react";

/** Uma chamada por vez; reduz consultas quando a aba não está visível. */
export function usePolling(
  task: (signal: AbortSignal) => Promise<void>,
  enabled: boolean,
  visibleInterval = 60_000,
  hiddenInterval = 300_000,
) {
  const current = useRef(task);
  current.current = task;
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let pending: AbortController | undefined;
    const schedule = (ms: number) => {
      clearTimeout(timer);
      if (alive) timer = setTimeout(() => void tick(), ms);
    };
    const tick = async () => {
      if (!alive) return;
      if (document.hidden) {
        schedule(hiddenInterval);
        return;
      }
      // Nunca sobrepor duas requisições, mesmo quando a rede fica lenta.
      if (pending) return;
      const controller = new AbortController();
      pending = controller;
      const timeout = setTimeout(() => controller.abort(), 10_000);
      try {
        await current.current(controller.signal);
      } finally {
        clearTimeout(timeout);
        if (pending === controller) pending = undefined;
        if (alive) schedule(document.hidden ? hiddenInterval : visibleInterval);
      }
    };
    const onVisibility = () => {
      if (document.hidden) {
        pending?.abort();
        schedule(hiddenInterval);
      } else {
        clearTimeout(timer);
        if (!pending) void tick();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    void tick();
    return () => {
      alive = false;
      clearTimeout(timer);
      pending?.abort();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [enabled, visibleInterval, hiddenInterval]);
}
