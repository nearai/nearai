import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

import { clearSignInNonce } from '~/lib/auth';
import { type authorizationModel } from '~/lib/models';

type AuthStore = {
  auth: z.infer<typeof authorizationModel> | null;
  isAuthenticated: boolean;
  unauthorizedErrorHasTriggered: boolean;

  clearAuth: () => void;
  setAuth: (auth: z.infer<typeof authorizationModel>) => void;
};

const store: StateCreator<AuthStore> = (set) => ({
  auth: null,
  isAuthenticated: false,
  unauthorizedErrorHasTriggered: false,

  clearAuth: () => {
    clearSignInNonce();

    set({
      auth: null,
      isAuthenticated: false,
      unauthorizedErrorHasTriggered: false,
    });
  },

  setAuth: (auth: z.infer<typeof authorizationModel>) => {
    set({ auth, isAuthenticated: true, unauthorizedErrorHasTriggered: false });
  },
});

export const name = 'AuthStore';

export const useAuthStore = create<AuthStore>()(devtools(store, { name }));
