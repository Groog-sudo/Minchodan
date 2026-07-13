const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function isLocalHost(hostname: string): boolean {
  return LOCAL_HOSTS.has(hostname.toLowerCase());
}

function trimTrailingSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export function resolveApiBaseUrl(apiBaseUrlFromEnv?: string): string {
  const browserHost = window.location.hostname || "localhost";
  const fallbackProtocol = window.location.protocol === "https:" ? "https:" : "http:";
  const fallbackBaseUrl = `${fallbackProtocol}//${browserHost}:8000`;
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
    }

    return parsed.toString();
  } catch {
    return `${resolveApiBaseUrl(apiBaseUrlFromEnv)}${pathFromApiBase}`;
  }
}
