// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { useEffect } from 'react';

import { useAuthStore } from '~/stores/auth';

export const ZustandHydration = () => {
  useEffect(() => {
    const rehydrate = async () => {
      await useAuthStore.persist.rehydrate();

      /*
        Make sure `isAuthenticated` stays synced with `auth` incase 
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

    rehydrate();
  }, []);

  return null;
};
