// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { openToast } from '@near-pagoda/ui';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { type z } from 'zod';

import { signInWithNear } from '~/lib/auth';
import { type authorizationModel } from '~/lib/models';
import { useAgentSettingsStore } from '~/stores/agent-settings';
import { useAuthStore } from '~/stores/auth';
import { trpc } from '~/trpc/TRPCProvider';

function migrateLocalStorageStoreNames() {
  /*
    This function migrates our legacy Zustand local storage keys 
    to our new storage key standard before hydrating:

    "store" => "AuthStore"
    "agent-settings" => "AgentSettingsStore"
  */

  if (!localStorage.getItem('AuthStore')) {
    const store = localStorage.getItem('store');
    if (store) {
      localStorage.setItem('AuthStore', store);
      localStorage.removeItem('store');
    }
  }

  if (!localStorage.getItem('AgentSettingsStore')) {
    const store = localStorage.getItem('agent-settings');
    if (store) {
      localStorage.setItem('AgentSettingsStore', store);
      localStorage.removeItem('agent-settings');
    }
  }
}

export const ZustandHydration = () => {
  const setAuth = useAuthStore((store) => store.setAuth);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const unauthorizedErrorHasTriggered = useAuthStore(
    (store) => store.unauthorizedErrorHasTriggered,
  );
  const getTokenQuery = trpc.auth.getToken.useQuery();
  const saveTokenMutation = trpc.auth.saveToken.useMutation();
  const pathname = usePathname();
  const utils = trpc.useUtils();
  const [hasRehydrated, setHasRehydrated] = useState(false);

  useEffect(() => {
    async function rehydrate() {
      migrateLocalStorageStoreNames();

      await useAuthStore.persist.rehydrate();
      await useAgentSettingsStore.persist.rehydrate();

      /*
        Make sure `isAuthenticated` stays synced with `auth` in case 
        an edge case or bug causes them to deviate:
      */

      const state = useAuthStore.getState();
      if (state.auth && !state.isAuthenticated) {
        useAuthStore.setState({
          isAuthenticated: true,
        });
      } else if (!state.auth && state.isAuthenticated) {
        useAuthStore.setState({
          isAuthenticated: false,
        });
      }

      setHasRehydrated(true);
    }

    void rehydrate();
  }, []);

  useEffect(() => {
    // TODO: Test like crazy

    console.log(pathname);

    if (pathname === '/sign-in/callback' || !hasRehydrated) return;

    function handleUnauthorized() {
      clearAuth();

      openToast({
        type: 'error',
        title: 'Your session has expired',
        description: 'Please sign in to continue',
        actionText: 'Sign In',
        action: signInWithNear,
      });
    }

    function migrateToCookie(auth: z.infer<typeof authorizationModel>) {
      /*
        This function keeps users signed in who had previously signed in 
        before we switched to using a secure cookie to store their auth token. 
        We can safely remove this migration logic in a few months after this 
        code has been deployed to production.
      */

      if (!saveTokenMutation.isIdle) return;

      saveTokenMutation.mutate(auth, {
        onError: () => {
          handleUnauthorized();
        },
        onSuccess: () => {
          void utils.invalidate();
        },
      });
    }

    const { auth } = useAuthStore.getState();

    const shouldMigrateToCookie =
      auth &&
      (getTokenQuery.isError ||
        (getTokenQuery.isSuccess && getTokenQuery.data == null));

    if (getTokenQuery.data) {
      console.log('Setting auth result from getTokenQuery()');
      setAuth(getTokenQuery.data);
    } else if (shouldMigrateToCookie) {
      console.log('Migrating auth token to cookie');
      migrateToCookie(auth);
    } else if (unauthorizedErrorHasTriggered) {
      console.log('Handling unauthorized error');
      handleUnauthorized();
    }
  }, [
    hasRehydrated,
    utils,
    saveTokenMutation,
    getTokenQuery,
    setAuth,
    clearAuth,
    pathname,
    unauthorizedErrorHasTriggered,
  ]);

  return null;
};
