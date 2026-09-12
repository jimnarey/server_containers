/**
 * A small, local WebSearchProvider for DeepSeek Harness.  SearXNG's JSON API
 * already provides the provider-neutral data that dsh-web expects, so this
 * has no vendor credentials and no model call in its search path.
 */

export const name = 'web-search-searxng';
export const inject = ['web'];

const PROVIDER_ID = 'searxng';
const DEFAULT_BASE_URL = 'http://searxng:8080';

function normaliseBaseUrl(value) {
  const baseUrl = new URL(value ?? DEFAULT_BASE_URL);
  if (baseUrl.protocol !== 'http:' && baseUrl.protocol !== 'https:') {
    throw new Error('web-search-searxng: baseURL must use HTTP or HTTPS');
  }
  return baseUrl;
}

function sourceFromSearxng(result) {
  if (typeof result?.url !== 'string' || result.url.length === 0) return undefined;

  const source = { url: result.url };
  if (typeof result.title === 'string' && result.title.length > 0) source.title = result.title;
  if (typeof result.content === 'string' && result.content.length > 0) source.snippet = result.content;
  if (typeof result.publishedDate === 'string' && result.publishedDate.length > 0) {
    source.publishedAt = result.publishedDate;
  }
  return source;
}

class SearxngSearchProvider {
  id = PROVIDER_ID;

  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  available() {
    return true;
  }

  async search(request, signal) {
    const endpoint = new URL('search', this.baseUrl);
    endpoint.searchParams.set('q', request.query);
    endpoint.searchParams.set('format', 'json');

    let response;
    try {
      response = await fetch(endpoint, {
        headers: { accept: 'application/json' },
        signal,
      });
    } catch (error) {
      throw new Error(`SearXNG search request failed: ${String(error)}`, { cause: error });
    }

    if (!response.ok) {
      throw new Error(`SearXNG search failed with HTTP ${response.status}`);
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new Error(`SearXNG returned invalid JSON: ${String(error)}`, { cause: error });
    }

    if (!Array.isArray(payload.results)) {
      throw new Error('SearXNG response does not contain a results array');
    }

    return {
      sources: payload.results.map(sourceFromSearxng).filter(Boolean),
      truncated: false,
    };
  }
}

export function apply(ctx, config = {}) {
  ctx.web.registerSearchProvider(new SearxngSearchProvider(normaliseBaseUrl(config.baseURL)));
}
