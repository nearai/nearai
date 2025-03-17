import { handleClientError } from '@near-pagoda/ui';
import { z } from 'zod';

import { env } from '~/env';
import { useAuthStore } from '~/stores/auth';
import { clientUtils } from '~/trpc/TRPCProvider';

const authenticatedPostMessageModel = z.object({
  authenticated: z.boolean(),
});

export function signIn() {
  setTimeout(() => {
    openAuthUrl();
  }, 10);
}

export function openAuthUrl() {
  const width = 775;
  const height = 775;
  const left = screen.width / 2 - width / 2;
  const top = screen.height / 2 - height / 2;

  const popup = window.open(
    env.NEXT_PUBLIC_AUTH_URL,
    '_blank',
    `popup=yes,scrollbars=yes,resizable=yes,width=${width},height=${height},left=${left},top=${top}`,
  );

  if (popup) {
    async function postMessageEventHandler(event: MessageEvent) {
      if (!popup) return;
      const data = event.data as Record<string, unknown>;
      const parsed = authenticatedPostMessageModel.safeParse(data);
      if (!parsed.data?.authenticated) return;

      const { setAuth, clearAuth } = useAuthStore.getState();

      try {
        const auth = await clientUtils.auth.getSession.fetch();
        await clientUtils.invalidate();
        if (!auth) throw new Error('Failed to return current auth session');
        setAuth(auth);
        popup.close();
        window.focus();
      } catch (error) {
        clearAuth();
        handleClientError({ error, title: 'Failed to sign in' });
      }
    }

    popup.focus();
    window.addEventListener('message', postMessageEventHandler);

    const interval = setInterval(() => {
      if (popup?.closed) {
        window.removeEventListener('message', postMessageEventHandler);
        clearInterval(interval);
      }
    }, 500);
  }
}
