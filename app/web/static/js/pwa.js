(() => {
  let installPrompt = null;

  const isStandalone = () =>
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
  const isAppleMobile = () => /iphone|ipad|ipod/i.test(window.navigator.userAgent);

  const updateInstallUI = () => {
    const installed = isStandalone();
    document.querySelectorAll("[data-pwa-install]").forEach((button) => {
      button.hidden = installed || !installPrompt;
    });
    document.querySelectorAll("[data-pwa-install-status]").forEach((status) => {
      if (installed) {
        status.textContent = "AquaOps is installed and opens like an app on this device.";
      } else if (installPrompt) {
        status.textContent = "Install AquaOps for a full-screen home-screen experience.";
      } else if (isAppleMobile()) {
        status.textContent = "In Safari, tap Share, then Add to Home Screen.";
      } else {
        status.textContent = "Use your browser menu and choose Install app or Add to Home screen.";
      }
    });
  };

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    updateInstallUI();
  });

  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    updateInstallUI();
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-pwa-install]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!installPrompt) {
          return;
        }
        installPrompt.prompt();
        await installPrompt.userChoice;
        installPrompt = null;
        updateInstallUI();
      });
    });
    updateInstallUI();

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/", updateViaCache: "none" });
    }
  });
})();
