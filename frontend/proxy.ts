import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const hasRefreshCookie = request.cookies.has("refresh_token");
  const hasDashboardSession = request.cookies.has("dashboard_session");
  const pathname = request.nextUrl.pathname;
  const hasSession = hasRefreshCookie || hasDashboardSession;

  if ((pathname.startsWith("/dashboard") || pathname.startsWith("/onboarding")) && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/onboarding/:path*", "/onboarding", "/login", "/register"],
};
