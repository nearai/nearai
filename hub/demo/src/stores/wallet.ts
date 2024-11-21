import type {
  AccountState,
  Wallet,
  WalletSelector,
  WalletSelectorState,
} from '@near-wallet-selector/core';
import type { SignMessageMethod } from '@near-wallet-selector/core/src/lib/wallet';
import type { WalletSelectorModal } from '@near-wallet-selector/modal-ui';
import { create, type StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

type WalletStore = {
  account: AccountState | null;
  hasResolved: boolean;
  modal: WalletSelectorModal | null;
  selector: WalletSelector | null;
  state: WalletSelectorState | null;
  wallet: (Wallet & SignMessageMethod) | null;

  setAccount: (account: AccountState | null) => void;
  setSelector: (
    selector: WalletSelector | null,
    modal: WalletSelectorModal | null,
  ) => void;
  setState: (state: WalletSelectorState | null) => void;
  setWallet: (wallet: (Wallet & SignMessageMethod) | null) => void;
};

const store: StateCreator<WalletStore> = (set) => ({
  account: null,
  hasResolved: false,
  selector: null,
  modal: null,
  state: null,
  wallet: null,

  setAccount: (account) => set({ account }),
  setSelector: (selector, modal) => set({ selector, modal }),
  setState: (state) => {
    if (state) {
      return set({ hasResolved: true, state });
    }
    return set({ state });
  },
  setWallet: (wallet) => set({ wallet }),
});

const name = 'WalletStore';

export const useWalletStore = create<WalletStore>()(
  devtools(store, {
    name,
  }),
);
