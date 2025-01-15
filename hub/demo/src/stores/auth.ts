import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

import { type authorizationModel } from '~/lib/models';

type AuthStore = {
  auth: z.infer<typeof authorizationModel> | null;
  currentNonce: string | null;
  isAuthenticated: boolean;
  unauthorizedErrorHasTriggered: boolean;

  clearAuth: () => void;
  setAuth: (auth: z.infer<typeof authorizationModel>) => void;
  setCurrentNonce: (nonce: string) => void;
};

const store: StateCreator<AuthStore> = (set) => ({
  auth: null,
  currentNonce: null,
  isAuthenticated: false,
  unauthorizedErrorHasTriggered: false,

  clearAuth: () => {
    set({
      auth: null,
      currentNonce: null,
      isAuthenticated: false,
      unauthorizedErrorHasTriggered: false,
    });
  },

  setAuth: (auth: z.infer<typeof authorizationModel>) => {
    set({ auth, isAuthenticated: true, unauthorizedErrorHasTriggered: false });
  },

  setCurrentNonce: (currentNonce: string) => {
    set({ currentNonce });
  },
});

const name = 'AuthStore';

export const useAuthStore = create<AuthStore>()(
  devtools(persist(store, { name, skipHydration: true }), {
    name,
  }),
);
