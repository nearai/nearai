// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { useEffect } from 'react';

import { useAgentSettingsStore } from '~/stores/agent-settings';
import { useAuthStore } from '~/stores/auth';

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
  useEffect(() => {
    const rehydrate = async () => {
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
    };

    void rehydrate();
  }, []);

  return null;
};
