import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import { usePolling } from "./usePolling";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function Probe({ task }: { task: () => Promise<void> }) {
  usePolling(async () => task(), true, 100, 500);
  return <p>Consulta controlada</p>;
}

describe("usePolling", () => {
  it("reduz consultas em aba oculta e retoma ao voltar", async () => {
    vi.useFakeTimers();
    let hidden = false;
    const old = Object.getOwnPropertyDescriptor(document, "hidden");
    Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
    try {
      const task = vi.fn(async () => {});
      render(<Probe task={task} />);
      await act(async () => {});
      expect(task).toHaveBeenCalledTimes(1);

      hidden = true;
      act(() => document.dispatchEvent(new Event("visibilitychange")));
      await act(async () => { await vi.advanceTimersByTimeAsync(150); });
      expect(task).toHaveBeenCalledTimes(1);
      hidden = false;
      act(() => document.dispatchEvent(new Event("visibilitychange")));
      await act(async () => {});
      expect(task).toHaveBeenCalledTimes(2);
    } finally {
      if (old) Object.defineProperty(document, "hidden", old);
    }
  });
});
