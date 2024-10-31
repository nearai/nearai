import { type Account, type Near } from 'near-api-js';
import { type BrowserLocalStorageKeyStore } from 'near-api-js/lib/key_stores';
import { create } from 'zustand';

type NearStore = {
  keyStore: BrowserLocalStorageKeyStore | null;
  near: Near | null;
  viewAccount: Account | null;

  setKeyStore: (keyStore: BrowserLocalStorageKeyStore | null) => void;
  setNear: (wallet: Near | null) => void;
  setViewAccount: (viewAccount: Account | null) => void;
};

export const useNearStore = create<NearStore>((set) => ({
  keyStore: null,
  near: null,
  viewAccount: null,

  setKeyStore: (keyStore) => set({ keyStore }),
  setNear: (near) => set({ near }),
  setViewAccount: (viewAccount) => set({ viewAccount }),
}));
