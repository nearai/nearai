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

import {
  MAINNET_NEAR_USDC_CONTRACT_ID,
  usdcAtomicAmountToDollars,
} from '@/utils/usdc';

import { useNearStore } from './near';

type WalletStore = {
  account: AccountState | null;
  hasResolved: boolean;
  modal: WalletSelectorModal | null;
  selector: WalletSelector | null;
  state: WalletSelectorState | null;
  usdcBalanceDollars: number;
  wallet: (Wallet & SignMessageMethod) | null;

  loadUsdcBalance: () => Promise<void>;

  setAccount: (account: AccountState | null) => void;
  setSelector: (
    selector: WalletSelector | null,
    modal: WalletSelectorModal | null,
  ) => void;
  setState: (state: WalletSelectorState | null) => void;
  setWallet: (wallet: (Wallet & SignMessageMethod) | null) => void;
};

const store: StateCreator<WalletStore> = (set, get) => ({
  account: null,
  hasResolved: false,
  selector: null,
  modal: null,
  state: null,
  usdcBalanceDollars: 0,
  wallet: null,

  loadUsdcBalance: async () => {
    const accountId = get().account?.accountId;
    const viewAccount = useNearStore.getState().viewAccount;
    if (!viewAccount || !accountId) return;

    try {
      const usdcAtomicAmount = (await viewAccount.viewFunction({
        contractId: MAINNET_NEAR_USDC_CONTRACT_ID,
        methodName: 'ft_balance_of',
        args: {
          account_id: accountId,
        },
      })) as string;

      const dollars = usdcAtomicAmountToDollars(
        parseInt(usdcAtomicAmount) || 0,
      );

      set({ usdcBalanceDollars: dollars });
    } catch (error) {
      console.error(
        `Failed to fetch USDC balance for account: ${accountId}`,
        error,
      );
      set({ usdcBalanceDollars: 0 });
    }
  },

  setAccount: (account) => {
    if (account) {
      set({ account });
      return;
    }
    set({ account, usdcBalanceDollars: 0 });
  },
  setSelector: (selector, modal) => set({ selector, modal }),
  setState: (state) => {
    if (state) {
      set({ hasResolved: true, state });
      return;
    }
    set({ state });
  },
  setWallet: (wallet) => set({ wallet }),
});

const name = 'WalletStore';

export const useWalletStore = create<WalletStore>()(
  devtools(store, {
    name,
  }),
);
