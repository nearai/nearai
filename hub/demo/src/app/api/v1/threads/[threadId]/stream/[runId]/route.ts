// In App Router API routes, we use the native Request type instead of NextApiRequest/NextApiResponse
import { env } from '@/env';
import { parseAuthCookie } from '@/utils/cookies';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ threadId: string; runId: string }> },
) {
  const { threadId, runId } = await params;

  // Extract authorization (adapt parseAuthCookie if needed for the Request object)
  const { authorization } = parseAuthCookie(request);

  // Set up the headers for an SSE response
  const responseHeaders = new Headers({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });

  // Fetch the router stream
  const routerResponse = await fetch(
    `${env.ROUTER_URL}/threads/${threadId}/stream/${runId}`,
    {
      headers: {
        Authorization: authorization || '',
      },
    },
  );

  if (!routerResponse.ok) {
    return new Response('Error from ROUTER_URL', {
      status: routerResponse.status,
    });
  }

  // Return the streamed response
  return new Response(routerResponse.body, { headers: responseHeaders });
}
