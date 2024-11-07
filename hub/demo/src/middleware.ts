import { type NextRequest, NextResponse } from 'next/server';

function redirectUrlPath(path: string, request: NextRequest) {
  return new URL(
    `${path}${request.nextUrl.search}${request.nextUrl.hash}`,
    request.url,
  );
}

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === '/') {
    return NextResponse.redirect(redirectUrlPath('/chat', request));
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
