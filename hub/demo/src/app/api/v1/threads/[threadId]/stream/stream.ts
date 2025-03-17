import { type NextApiRequest, type NextApiResponse } from 'next';
import { env } from '~/env';
import { parseAuthCookie } from '~/utils/cookies';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const threadId = req.query.threadId as string;
  const { authorization } = parseAuthCookie(req);

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const routerStream = await fetch(`${env.ROUTER_URL}/threads/${threadId}/stream`, {
    headers: {
      Authorization: authorization || '',
    },
  });

  if (!routerStream.ok) {
    res.status(routerStream.status).send('Error from ROUTER_URL');
    return;
  }

  routerStream.body?.pipe(res);

  req.socket.on('close', () => {
    res.end();
  });
}