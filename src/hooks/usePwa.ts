import { useEffect, useState } from "react";

type InstallEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};
const standalone = () => window.matchMedia?.("(display-mode: standalone)").matches ||
  (navigator as Navigator & { standalone?: boolean }).standalone === true;

export function usePwa() {
  const [online, setOnline] = useState(() => navigator.onLine);
  const [installed, setInstalled] = useState(standalone);
  const [offer, setOffer] = useState<InstallEvent | null>(null);
  const [guideOpen, setGuideOpen] = useState(false);
  const [updateReady, setUpdateReady] = useState(false);

  useEffect(() => {
    const connected = () => setOnline(navigator.onLine);
    const installOffer = (event: Event) => {
      event.preventDefault();
      setOffer(event as InstallEvent);
    };
    const installedEvent = () => { setInstalled(true); setOffer(null); setGuideOpen(false); };
    const updated = () => setUpdateReady(true);
    window.addEventListener("online", connected);
    window.addEventListener("offline", connected);
    window.addEventListener("beforeinstallprompt", installOffer);
    window.addEventListener("appinstalled", installedEvent);
    window.addEventListener("pwa:update-ready", updated);
    return () => {
      window.removeEventListener("online", connected);
      window.removeEventListener("offline", connected);
      window.removeEventListener("beforeinstallprompt", installOffer);
      window.removeEventListener("appinstalled", installedEvent);
      window.removeEventListener("pwa:update-ready", updated);
    };
  }, []);

  const install = async () => {
    if (!offer) { setGuideOpen(true); return; }
    try {
      await offer.prompt();
      await offer.userChoice;
    } catch {
      setGuideOpen(true);
    } finally {
      setOffer(null);
    }
  };
  const update = async () => {
    if (!("serviceWorker" in navigator)) return;
    const registration = await navigator.serviceWorker.getRegistration(import.meta.env.BASE_URL);
    if (!registration?.waiting) { setUpdateReady(false); return; }
    navigator.serviceWorker.addEventListener("controllerchange", () => window.location.reload(), { once: true });
    registration.waiting.postMessage({ type: "SKIP_WAITING" });
  };
  return { online, installed, guideOpen, setGuideOpen, updateReady, install, update };
}
