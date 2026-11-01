/** Registro local ao escopo Vite: funciona em Pages /webgis-transporte-canoas/. */
export function registerPwa() {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;
  const register = async () => {
    try {
      const registration = await navigator.serviceWorker.register(
        import.meta.env.BASE_URL + "sw.js",
        { scope: import.meta.env.BASE_URL },
      );
      const notify = () => {
        if (registration.waiting && navigator.serviceWorker.controller)
          window.dispatchEvent(new Event("pwa:update-ready"));
      };
      notify();
      registration.addEventListener("updatefound", () => {
        const installing = registration.installing;
        installing?.addEventListener("statechange", () => {
          if (installing.state === "installed") notify();
        });
      });
      // Verifica novas versões quando o usuário volta ao aplicativo.
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") void registration.update().catch(() => {});
      });
    } catch (error) {
      console.warn("PWA indisponível; o WebGIS continua funcionando online.", error);
    }
  };
  if (document.readyState === "complete") void register();
  else window.addEventListener("load", () => void register(), { once: true });
}
