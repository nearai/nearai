// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { openToast } from '@near-pagoda/ui';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

import { signIn } from '~/lib/auth';
import { useAuthStore } from '~/stores/auth';
import { trpc } from '~/trpc/TRPCProvider';

export const ZustandHydration = () => {
  const unauthorizedErrorHasTriggered = useAuthStore(
    (store) => store.unauthorizedErrorHasTriggered,
  );
  const getTokenQuery = trpc.auth.getSession.useQuery();
  const pathname = usePathname();
  const utils = trpc.useUtils();

  useEffect(() => {
    if (!getTokenQuery.isSuccess && !getTokenQuery.isError) {
      return;
    }

    const { setAuth, clearAuth } = useAuthStore.getState();

    function handleUnauthorized() {
      clearAuth();

      openToast({
        id: 'auth-session-expired', // Prevents duplicate toasts from spawning in quick succession
        type: 'error',
        title: 'Your session has expired',
        description: 'Please sign in to continue',
        actionText: 'Sign In',
        action: signIn,
      });
    }

    if (getTokenQuery.data && !unauthorizedErrorHasTriggered) {
      setAuth(getTokenQuery.data);
      return;
    }

    if (unauthorizedErrorHasTriggered) {
      utils.auth.getSession.setData(undefined, null);
      handleUnauthorized();
    }
  }, [utils, getTokenQuery, pathname, unauthorizedErrorHasTriggered]);

  return null;
};
