import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

import { clearSignInNonce } from '@/lib/auth';

type Auth = {
  accountId: string;
};

type AuthStore = {
  auth: Auth | null;
  unauthorizedErrorHasTriggered: boolean;

  clearAuth: () => void;
  setAuth: (auth: Auth) => void;
};

const store: StateCreator<AuthStore> = (set) => ({
  auth: null,
  unauthorizedErrorHasTriggered: false,

  clearAuth: () => {
    clearSignInNonce();

    set({
      auth: null,
      unauthorizedErrorHasTriggered: false,
    });
  },

  setAuth: (auth: Auth) => {
    set({ auth, unauthorizedErrorHasTriggered: false });
  },
});

export const name = 'AuthStore';

export const useAuthStore = create<AuthStore>()(devtools(store, { name }));
