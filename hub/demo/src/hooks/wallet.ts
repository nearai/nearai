import { setupBitteWallet } from '@near-wallet-selector/bitte-wallet';
import {
  setupWalletSelector,
  type WalletSelector,
} from '@near-wallet-selector/core';
import { setupHereWallet } from '@near-wallet-selector/here-wallet';
import { setupMeteorWallet } from '@near-wallet-selector/meteor-wallet';
import { setupModal } from '@near-wallet-selector/modal-ui';
import { setupMyNearWallet } from '@near-wallet-selector/my-near-wallet';
import { setupSender } from '@near-wallet-selector/sender';
import { useRef } from 'react';
import { useEffect } from 'react';

import { useWalletStore } from '@/stores/wallet';

export function useWalletInitializer() {
  const setupPromise = useRef<Promise<WalletSelector> | null>(null);
  const setWallet = useWalletStore((store) => store.setWallet);
  const setWalletState = useWalletStore((store) => store.setState);
  const setWalletAccount = useWalletStore((store) => store.setAccount);
  const setWalletSelector = useWalletStore((store) => store.setSelector);
  const loadUsdcBalance = useWalletStore((store) => store.loadUsdcBalance);
  const walletAccount = useWalletStore((store) => store.account);
  const walletSelector = useWalletStore((store) => store.selector);

  useEffect(() => {
    const initialize = async () => {
      if (!setupPromise.current) {
        setupPromise.current = setupWalletSelector({
          // @ts-expect-error: Other url config values (helper, indexer) are not actually required
          network: {
            networkId: 'mainnet',
            nodeUrl: '/api/near-rpc-proxy',
          },
          modules: [
            setupMyNearWallet(),
            setupBitteWallet(),
            setupMeteorWallet(),
            setupSender(),
            setupHereWallet(),
          ],
        });
      }

      const selector = await setupPromise.current;
      const modal = setupModal(selector, {
        contractId: '',
        description: '',
        theme: 'auto',
      });

      setWalletSelector(selector, modal);
    };

    void initialize();
  }, [setWalletSelector]);

  useEffect(() => {
    if (!walletSelector) return;

    setWalletState(walletSelector.store.getState());

    const subscription = walletSelector.store.observable.subscribe((value) => {
      setWalletState(value);
      setWalletAccount(value?.accounts[0] ?? null);

      if (
        value.accounts.length > 0 &&
        value.selectedWalletId &&
        walletSelector
      ) {
        walletSelector
          .wallet()
          .then((wallet) => setWallet(wallet))
          .catch((error) => console.error(error));
      } else {
        setWalletAccount(null);
        setWalletState(null);
        setWallet(null);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [walletSelector, setWalletAccount, setWalletState, setWallet]);

  useEffect(() => {
    if (!walletAccount?.accountId) return;

    function onVisibilityChange() {
      if (document.visibilityState === 'visible') {
        void loadUsdcBalance();
      }
    }

    window.addEventListener('visibilitychange', onVisibilityChange);
    void loadUsdcBalance();

    return () => {
      window.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [walletAccount?.accountId, loadUsdcBalance]);
}
