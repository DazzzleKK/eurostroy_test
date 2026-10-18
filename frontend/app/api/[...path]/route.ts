import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const FORWARDED_HEADERS = ["content-type", "cache-control"] as const;

/**
 * Прокси к backend.
 *
 * Страница и картинки живут на одном origin: браузер и Telegram WebView не
 * делают cross-origin запросов, а адреса вида /api/products/... работают
 * и локально, и за любым доменом.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  const target = new URL(`/api/${path.join("/")}`, BACKEND_URL);
  target.search = request.nextUrl.search;

  const upstream = await fetch(target, { cache: "no-store" });
  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }

  return new Response(upstream.body, { status: upstream.status, headers });
}
