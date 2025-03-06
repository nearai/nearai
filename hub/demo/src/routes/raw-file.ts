import mime from 'mime';
import { type NextRequest } from 'next/server';

import { env } from '~/env';
import { conditionallyIncludeAuthorizationHeader } from '~/trpc/utils/headers';
import { parseAuthCookie } from '~/utils/cookies';

export async function GET(
  req: NextRequest,
  {
    params,
  }: {
    params: Promise<{
      namespace: string;
      name: string;
      version: string;
      filePath: string[];
    }>;
  },
) {
  const { namespace, name, version, filePath } = await params;
  const path = filePath.join('/');
  const { authorization } = parseAuthCookie(req);

  const response = await fetch(`${env.ROUTER_URL}/registry/download_file`, {
    method: 'POST',
    headers: conditionallyIncludeAuthorizationHeader(authorization, {
      Accept: 'binary/octet-stream',
      'Content-Type': 'application/json',
    }),
    body: JSON.stringify({
      entry_location: {
        namespace,
        name,
        version,
      },
      path,
    }),
  });

  if (!response.ok) {
    return new Response(null, {
      status: response.status,
    });
  }

  const result = new Response(await response.blob());
  result.headers.set('Content-Type', mime.getType(path) || 'text/plain');

  return result;
}
