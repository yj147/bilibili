import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const ALLOWED_PATHS = [
  '/api/accounts',
  '/api/targets',
  '/api/reports',
  '/api/autoreply',
  '/api/scheduler',
  '/api/config',
  '/api/auth',
  '/api/system',
  '/health',
];

async function handler(req: NextRequest) {
  const url = new URL(req.url);
  const pathname = url.pathname;

  // Validate path is in whitelist
  const isAllowed = ALLOWED_PATHS.some(prefix => pathname.startsWith(prefix));
  if (!isAllowed) {
    return NextResponse.json(
      { detail: "Path not allowed" },
      { status: 403 }
    );
  }

  // Normalize path to prevent traversal
  const normalizedPath = new URL(pathname, 'http://localhost').pathname;
  const targetUrl = `${BACKEND_URL}${normalizedPath}${url.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "host") {
      headers.set(key, value);
    }
  });

  const controller = new AbortController();
  const isLongRunning = url.pathname.includes("scan-comments") || url.pathname.includes("execute");
  const timeout = setTimeout(() => controller.abort(), isLongRunning ? 120000 : 30000);

  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? await req.text() : undefined,
      redirect: "follow",
      signal: controller.signal,
    });

    clearTimeout(timeout);

    const body = await resp.text();
    const respHeaders = new Headers();
    resp.headers.forEach((value, key) => {
      if (!key.toLowerCase().startsWith("access-control")) {
        respHeaders.set(key, value);
      }
    });

    return new NextResponse(body, {
      status: resp.status,
      headers: respHeaders,
    });
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof DOMException && err.name === "AbortError") {
      return NextResponse.json(
        { detail: "Backend timeout" },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { detail: "Backend unavailable" },
      { status: 502 }
    );
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
export const OPTIONS = handler;
