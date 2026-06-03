import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/global.css";

const USE_MOCK =
  import.meta.env.VITE_USE_MOCK === "true" || import.meta.env.VITE_USE_MOCK === undefined;

async function bootstrap() {
  if (USE_MOCK) {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      onUnhandledRequest: "bypass",
      serviceWorker: { url: "/mockServiceWorker.js" },
    });
  } else if ("serviceWorker" in navigator) {
    // real 백엔드 모드: 이전 mock 세션에서 등록된 MSW service worker가 남아 있으면
    // 실제 요청을 가로채 "FetchEvent.respondWith ... Load failed"를 유발한다. 모두 해제.
    const regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(regs.map((r) => r.unregister()));
  }
  const rootEl = document.getElementById("root");
  if (!rootEl) throw new Error("#root element not found");
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void bootstrap();
