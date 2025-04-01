import { type NextRequest, NextResponse } from 'next/server';

import { env } from '@/env';

const defaultRoute = env.NEXT_PUBLIC_CONSUMER_MODE ? '/chat' : '/';
const agentWithoutVersionRegex = /^\/agents\/[^\/]+\/[^\/]+$/;

function redirectUrlPath(path: string, request: NextRequest) {
  return new URL(
    `${path}${request.nextUrl.search}${request.nextUrl.hash}`,
    request.url,
  );
}

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === '/' && defaultRoute != '/') {
    return NextResponse.redirect(redirectUrlPath(defaultRoute, request));
  }

  if (agentWithoutVersionRegex.test(request.nextUrl.pathname)) {
    // Redirect "/agents/account.near/cool-agent" to "/agents/account.near/cool-agent/latest"
    return NextResponse.redirect(
      redirectUrlPath(`${request.nextUrl.pathname}/latest`, request),
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
