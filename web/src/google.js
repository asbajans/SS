const SOURCE = "https://accounts.google.com/gsi/client";

let loader = null;

export function loadGoogleIdentity() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google);
  if (loader) return loader;
  loader = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SOURCE;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.accounts?.id) resolve(window.google);
      else reject(new Error("google identity script failed"));
    };
    script.onerror = () => reject(new Error("google identity script failed"));
    document.head.appendChild(script);
  });
  return loader;
}

export async function renderGoogleButton(element, clientId, options = {}) {
  const google = await loadGoogleIdentity();
  const width = Math.min(360, Math.max(220, element.clientWidth || 360));
  element.innerHTML = "";
  google.accounts.id.initialize({
    client_id: clientId,
    callback: (response) => options.onCredential?.(response.credential),
    ux_mode: "popup",
    hl: options.hl || "tr",
  });
  google.accounts.id.renderButton(element, {
    theme: "filled_black",
    size: "large",
    shape: "pill",
    width,
    text: "continue_with",
  });
}
