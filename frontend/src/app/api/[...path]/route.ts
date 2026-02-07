import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "http://127.0.0.1:8000";

async function handler(req: NextRequest) {
  const url = new URL(req.url);
  const targetUrl = `${BACKEND_URL}${url.pathname}${url.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "host") {
      headers.set(key, value);
    }
  });

  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? await req.text() : undefined,
      redirect: "follow",
    });

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
