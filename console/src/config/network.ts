const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function isLocalHost(hostname: string): boolean {
  return LOCAL_HOSTS.has(hostname.toLowerCase());
}

function trimTrailingSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export function resolveApiBaseUrl(apiBaseUrlFromEnv?: string): string {
  const browserHost = window.location.hostname || "localhost";
  const browserPort = window.location.port ? `:${window.location.port}` : "";
  const fallbackProtocol = window.location.protocol === "https:" ? "https:" : "http:";
  const fallbackBaseUrl = `${fallbackProtocol}//${browserHost}${browserPort}`;
  const raw = (apiBaseUrlFromEnv || "").trim();

  if (!raw) {
    return trimTrailingSlash(fallbackBaseUrl);
  }

  try {
    const parsed = new URL(raw);

    // If env points to localhost but the console is opened from another host,
    // rewrite to the current browser host so LAN access works without env edits.
    if (isLocalHost(parsed.hostname) && !isLocalHost(browserHost)) {
      parsed.hostname = browserHost;
      parsed.port = window.location.port; // Inherit port to route through Vite proxy
      parsed.protocol = window.location.protocol; // Inherit protocol to avoid mixed content
    }

    return trimTrailingSlash(parsed.toString());
  } catch {
    return trimTrailingSlash(fallbackBaseUrl);
  }
}

export function resolveServiceUrl(
  envUrl: string | undefined,
  pathFromApiBase: string,
  apiBaseUrlFromEnv?: string,
): string {
  const raw = (envUrl || "").trim();

  if (!raw) {
    return `${resolveApiBaseUrl(apiBaseUrlFromEnv)}${pathFromApiBase}`;
  }

  try {
    const parsed = new URL(raw);
    const browserHost = window.location.hostname || "localhost";

    if (isLocalHost(parsed.hostname) && !isLocalHost(browserHost)) {
      parsed.hostname = browserHost;
      parsed.port = window.location.port; // Inherit port to route through Vite proxy
      parsed.protocol = window.location.protocol; // Inherit protocol to avoid mixed content
    }

    return parsed.toString();
  } catch {
    return `${resolveApiBaseUrl(apiBaseUrlFromEnv)}${pathFromApiBase}`;
  }
}
