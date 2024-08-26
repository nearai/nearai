import { type z } from 'zod';
import { create, type StateCreator } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

import { authorizationModel } from '~/lib/models';

type AuthStore = {
  auth: z.infer<typeof authorizationModel> | null;
  currentNonce: string | null;

  clearAuth: () => void;
  isAuthenticated: () => boolean;
  setAuth: (auth: z.infer<typeof authorizationModel>) => void;
  setAuthRaw: (value: string) => void;
  setCurrentNonce: (nonce: string) => void;
  toBearer: () => string;
};

const createStore: StateCreator<AuthStore> = (set, get) => ({
  auth: null,
  currentNonce: null,

  isAuthenticated: () => {
    return !!get().auth;
  },

  clearAuth: () => {
    set({ auth: null, currentNonce: null });
  },

  setAuth: (auth: z.infer<typeof authorizationModel>) => {
    set({ auth });
  },

  setAuthRaw: (value: string) => {
    if (value.startsWith('Bearer ')) {
      value = value.substring('Bearer '.length);
    }
    const auth = authorizationModel.parse(JSON.parse(value));
    set({ auth });
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

export const useAuthStore = create<AuthStore>()(
  devtools(persist(createStore, { name: 'store', skipHydration: true })),
);
