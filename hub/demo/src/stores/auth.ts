import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

import { authorizationModel } from '~/lib/models';

type AuthStore = {
  auth: z.infer<typeof authorizationModel> | null;
  currentNonce: string | null;

  clearAuth: () => void;
  isAuthenticated: boolean;
  setAuth: (auth: z.infer<typeof authorizationModel>) => void;
  setAuthRaw: (value: string) => void;
  setCurrentNonce: (nonce: string) => void;
  toBearer: () => string;
};

const store: StateCreator<AuthStore> = (set, get) => ({
  auth: null,
  currentNonce: null,
  isAuthenticated: false,

  clearAuth: () => {
    set({ auth: null, currentNonce: null, isAuthenticated: false });
  },

  setAuth: (auth: z.infer<typeof authorizationModel>) => {
    set({ auth, isAuthenticated: true });
  },

  setAuthRaw: (value: string) => {
    if (value.startsWith('Bearer ')) {
      value = value.substring('Bearer '.length);
    }
    const auth = authorizationModel.parse(JSON.parse(value));
    set({ auth, isAuthenticated: true });
  },

  setCurrentNonce: (currentNonce: string) => {
    set({ currentNonce });
  },

  toBearer: () => {
    if (!get().auth) {
      return '';
    }
    return `Bearer ${JSON.stringify(get().auth)}`;
  },
});

const name = 'AuthStore';

export const useAuthStore = create<AuthStore>()(
  devtools(persist(store, { name, skipHydration: true }), {
    name,
  }),
);
