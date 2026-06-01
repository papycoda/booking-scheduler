import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const hasRefreshCookie = request.cookies.has("refresh_token");
  const hasDashboardSession = request.cookies.has("dashboard_session");
  if (request.nextUrl.pathname.startsWith("/dashboard") && !hasRefreshCookie && !hasDashboardSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
