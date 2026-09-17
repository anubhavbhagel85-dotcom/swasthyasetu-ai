import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Registers the offline app-shell cache (see public/sw.js). Wrapped so a
// browser without service worker support (or a strict dev sandbox) never
// breaks the app — offline *chat* still works via the in-memory fallback
// engine in src/offline/offlineEngine.js even without this.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Non-fatal: PWA app-shell caching just won't be available.
    });
  });
}
