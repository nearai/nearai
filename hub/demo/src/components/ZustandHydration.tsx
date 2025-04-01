// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { openToast } from '@nearai/ui';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { type z } from 'zod';

import { SIGN_IN_CALLBACK_PATH, signIn } from '@/lib/auth';
import { authorizationModel } from '@/lib/models';
import { useAgentSettingsStore } from '@/stores/agent-settings';
import { name as authStoreName, useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';

function migrateLocalStorageStoreNames() {
  /*
    This function migrates our legacy Zustand local storage keys 
    to our new storage key standard before hydrating:

    "agent-settings" => "AgentSettingsStore"
  */

  if (!localStorage.getItem('AgentSettingsStore')) {
    const store = localStorage.getItem('agent-settings');
    if (store) {
      localStorage.setItem('AgentSettingsStore', store);
      localStorage.removeItem('agent-settings');
    }
  }
}

function returnLocalStorageAuthStoreToMigrate() {
  let auth: z.infer<typeof authorizationModel> | null = null;
  const raw = localStorage.getItem(authStoreName);

  if (raw) {
    try {
      auth = authorizationModel.parse(JSON.parse(raw)?.state?.auth);

      localStorage.removeItem(authStoreName);
    } catch (_error) {}
  }

  return auth;
}

export const ZustandHydration = () => {
  const unauthorizedErrorHasTriggered = useAuthStore(
    (store) => store.unauthorizedErrorHasTriggered,
  );
  const getTokenQuery = trpc.auth.getSession.useQuery();
  const saveTokenMutation = trpc.auth.saveToken.useMutation();
  const pathname = usePathname();
  const utils = trpc.useUtils();

  useEffect(() => {
    async function rehydrate() {
      migrateLocalStorageStoreNames();
      await useAgentSettingsStore.persist.rehydrate();
    }

    void rehydrate();
  }, []);

  useEffect(() => {
    if (
      pathname.startsWith(SIGN_IN_CALLBACK_PATH) ||
      (!getTokenQuery.isSuccess && !getTokenQuery.isError)
    ) {
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

    /*
      The following logic keeps users signed in who had previously signed in before 
      we switched to using a secure cookie to store their auth token. We can safely 
      remove this migration logic in a few months after this code has been deployed 
      to production:
    */

    // Start auth migration logic --------------

    const authToMigrate = returnLocalStorageAuthStoreToMigrate();

    if (authToMigrate) {
      if (!saveTokenMutation.isIdle) return;

      saveTokenMutation.mutate(authToMigrate, {
        onError: () => {
          handleUnauthorized();
        },
        onSuccess: () => {
          void utils.invalidate();
        },
        onSettled: () => {
          localStorage.removeItem(authStoreName);
        },
      });

      return;
    }

    // End auth migration logic --------------

    if (unauthorizedErrorHasTriggered) {
      utils.auth.getSession.setData(undefined, null);
      handleUnauthorized();
    }
  }, [
    utils,
    saveTokenMutation,
    getTokenQuery,
    pathname,
    unauthorizedErrorHasTriggered,
  ]);

  return null;
};
