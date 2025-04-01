import mime from 'mime';
import { type NextRequest } from 'next/server';

import { env } from '@/env';
import { type EntryCategory } from '@/lib/models';
import { fetchEntryMetadataJson } from '@/trpc/utils/entries';
import { conditionallyIncludeAuthorizationHeader } from '@/trpc/utils/headers';
import { parseAuthCookie } from '@/utils/cookies';

export type FetchRawFileInput = {
  params: Promise<{
    namespace: string;
    name: string;
    version: string;
    filePath: string[];
  }>;
};

export async function fetchRawFile(
  req: NextRequest,
  category: EntryCategory,
  { params }: FetchRawFileInput,
) {
  try {
    const { namespace, name, version, filePath } = await params;
    const path = filePath.join('/');
    const { authorization, signature } = parseAuthCookie(req);

    if (path === 'metadata.json') {
      const metadata = await fetchEntryMetadataJson(
        {
          authorization,
          signature,
        },
        {
          namespace,
          name,
          version,
          category,
        },
      );
      return Response.json(metadata.json);
    }

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
      throw new Error(
        `Download file failed with status code: ${response.status}`,
      );
    }

    const result = new Response(await response.blob());
    result.headers.set('Content-Type', mime.getType(path) || 'text/plain');

    return result;
  } catch (error) {
    console.error(error);
    return new Response(null, {
      status: 500,
    });
  }
}
