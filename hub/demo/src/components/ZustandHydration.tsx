// https://zustand.docs.pmnd.rs/integrations/persisting-store-data#skiphydration

'use client';

import { useEffect } from 'react';

import { useAuthStore } from '~/stores/auth';

export const ZustandHydration = () => {
  useEffect(() => {
    void useAuthStore.persist.rehydrate();
  }, []);

  return null;
};
