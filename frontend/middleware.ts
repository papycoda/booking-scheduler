import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const hasRefreshCookie = request.cookies.has("refresh_token");
  const hasDashboardSession = request.cookies.has("dashboard_session");
  const pathname = request.nextUrl.pathname;
  const hasSession = hasRefreshCookie || hasDashboardSession;

  if (pathname.startsWith("/dashboard") && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  if ((pathname === "/login" || pathname === "/register") && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/register"],
};
