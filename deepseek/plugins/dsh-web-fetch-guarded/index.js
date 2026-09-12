/**
 * DeepSeek Harness fetch provider backed by the Compose-local guarded-fetch
 * gateway. The gateway, rather than the model-visible tool, owns destination
 * validation, DNS/IP pinning, redirect checks, and response limits.
 */

import { WebError } from '@deepseek-ai/dsh-web';

export const name = 'dsh-web-fetch-guarded';
export const inject = ['web'];

const PROVIDER_ID = 'guarded-fetch';
const DEFAULT_BASE_URL = 'http://guarded-fetch:8080/v1/fetch';

function normaliseBaseUrl(value) {
  const baseUrl = new URL(value ?? DEFAULT_BASE_URL);
  if (baseUrl.protocol !== 'http:' && baseUrl.protocol !== 'https:') {
    throw new Error('dsh-web-fetch-guarded: baseURL must use HTTP or HTTPS');
  }
  return baseUrl;
}

function string(value) {
  return typeof value === 'string' ? value : undefined;
}

function number(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function bodyKind(contentType) {
  const mediaType = (contentType ?? '').split(';', 1)[0].trim().toLowerCase();
  return mediaType === 'text/html' || mediaType === 'application/xhtml+xml'
    ? 'html'
    : 'text';
}

class GuardedFetchProvider {
  id = PROVIDER_ID;

  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  available() {
    return true;
  }

  async fetch(request, signal) {
    let response;
    try {
      response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ url: request.url }),
        signal,
      });
    } catch (error) {
      throw new WebError('guarded fetch gateway request failed', 'WEB_PROVIDER_ERROR', {
        cause: error,
      });
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new WebError('guarded fetch gateway returned invalid JSON', 'WEB_PROVIDER_ERROR', {
        cause: error,
      });
    }

    if (!response.ok) {
      throw new WebError(
        string(payload?.error) ?? 'guarded fetch gateway rejected the request',
        'WEB_BLOCKED_URL',
      );
    }

    const finalUrl = string(payload?.url);
    const statusCode = number(payload?.status);
    const content = string(payload?.body);
    if (finalUrl === undefined || statusCode === undefined || content === undefined) {
      throw new WebError('guarded fetch gateway returned an invalid result', 'WEB_PROVIDER_ERROR');
    }

    return {
      url: finalUrl,
      statusCode,
      body: {
        kind: bodyKind(string(payload?.contentType)),
        content,
      },
      truncated: payload?.truncated === true,
    };
  }
}

export function apply(ctx, config = {}) {
  ctx.web.registerFetchProvider(new GuardedFetchProvider(normaliseBaseUrl(config.baseURL)));
}
