import http from "node:http";

import {
  guardedFetch,
  isGuardedFetchError,
  readBodyAsText,
} from "guarded-fetch";

const MAX_REQUEST_BYTES = 8 * 1024;
const SUPPORTED_MEDIA_TYPES = new Set([
  "application/atom+xml",
  "application/javascript",
  "application/json",
  "application/ld+json",
  "application/rss+xml",
  "application/xhtml+xml",
  "application/xml",
  "application/x-javascript",
]);

class HttpError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

function positiveInteger(name, fallback, maximum) {
  const value = Number.parseInt(process.env[name] ?? "", 10);
  if (!Number.isSafeInteger(value) || value < 1 || value > maximum) {
    return fallback;
  }
  return value;
}

const port = positiveInteger("GUARDED_FETCH_PORT", 8080, 65535);
const timeoutMs = positiveInteger("GUARDED_FETCH_TIMEOUT_MS", 15_000, 60_000);
const maxRedirects = positiveInteger("GUARDED_FETCH_MAX_REDIRECTS", 5, 10);
const maxResponseBytes = positiveInteger(
  "GUARDED_FETCH_MAX_RESPONSE_BYTES",
  1_048_576,
  5 * 1_048_576,
);
const maxBodyChars = positiveInteger(
  "GUARDED_FETCH_MAX_BODY_CHARS",
  100_000,
  500_000,
);
const allowedHosts = (process.env.GUARDED_FETCH_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

function writeJson(response, statusCode, value) {
  const body = JSON.stringify(value);
  response.writeHead(statusCode, {
    "cache-control": "no-store",
    "content-length": Buffer.byteLength(body),
    "content-type": "application/json; charset=utf-8",
    "x-content-type-options": "nosniff",
  });
  response.end(body);
}

async function readJsonBody(request) {
  const contentType = request.headers["content-type"] ?? "";
  if (contentType.split(";", 1)[0].trim().toLowerCase() !== "application/json") {
    throw new HttpError(415, "Content-Type must be application/json.");
  }

  const chunks = [];
  let received = 0;
  for await (const chunk of request) {
    received += chunk.length;
    if (received > MAX_REQUEST_BYTES) {
      throw new HttpError(413, "Request body is too large.");
    }
    chunks.push(chunk);
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "Request body must contain valid JSON.");
  }
}

function isSupportedTextResponse(contentType) {
  const mediaType = contentType.split(";", 1)[0].trim().toLowerCase();
  return mediaType.startsWith("text/") || SUPPORTED_MEDIA_TYPES.has(mediaType);
}

async function cancelResponse(response) {
  try {
    await response.body?.cancel();
  } catch {
    // The response may already have been closed by the upstream.
  }
}

async function fetchText(url) {
  const startedAt = Date.now();
  const response = await guardedFetch(url, {
    allowedHosts: allowedHosts.length === 0 ? undefined : allowedHosts,
    followRedirects: true,
    httpsOnly: true,
    maxRedirects,
    method: "GET",
    opaqueErrors: true,
    timeoutMs,
  });

  const contentType = response.headers.get("content-type") ?? "";
  if (!isSupportedTextResponse(contentType)) {
    await cancelResponse(response);
    throw new HttpError(415, "Upstream response is not a supported text format.");
  }

  const text = await readBodyAsText(response, {
    deadlineAt: startedAt + timeoutMs,
    maxResponseBytes,
    opaqueErrors: true,
  });
  const truncated = text.length > maxBodyChars;

  return {
    body: truncated ? text.slice(0, maxBodyChars) : text,
    contentType,
    status: response.status,
    truncated,
    url: response.url,
  };
}

const server = http.createServer(async (request, response) => {
  try {
    if (request.method === "GET" && request.url === "/healthz") {
      writeJson(response, 200, { status: "ok" });
      return;
    }

    if (request.method !== "POST" || request.url !== "/v1/fetch") {
      writeJson(response, 404, { error: "Not found." });
      return;
    }

    const payload = await readJsonBody(request);
    if (
      !payload ||
      typeof payload !== "object" ||
      Array.isArray(payload) ||
      typeof payload.url !== "string" ||
      payload.url.length === 0 ||
      payload.url.length > 8_192
    ) {
      throw new HttpError(400, "Request body must contain a URL string.");
    }

    writeJson(response, 200, await fetchText(payload.url));
  } catch (error) {
    if (response.headersSent) {
      response.destroy();
      return;
    }

    if (error instanceof HttpError) {
      writeJson(response, error.statusCode, { error: error.message });
      return;
    }

    if (isGuardedFetchError(error)) {
      console.warn("guarded outbound fetch failed", { code: error.code });
      writeJson(response, error.code === "TIMEOUT" ? 504 : 502, {
        error: "The requested URL could not be fetched.",
      });
      return;
    }

    console.error("unexpected guarded-fetch gateway failure", error);
    writeJson(response, 500, { error: "The fetch gateway encountered an error." });
  }
});

// The request body is only an 8 KiB JSON object. Keep slow clients from
// retaining a gateway connection while they trickle that small request body.
server.headersTimeout = 5_000;
server.requestTimeout = 10_000;
server.keepAliveTimeout = 5_000;

server.listen(port, "0.0.0.0", () => {
  console.log(`guarded-fetch gateway listening on port ${port}`);
});

function shutdown() {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
