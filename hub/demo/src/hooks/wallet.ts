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

import { useWalletStore } from '~/stores/wallet';

export function useWalletInitializer() {
  const setupPromise = useRef<Promise<WalletSelector> | null>(null);
  const setState = useWalletStore((store) => store.setState);
  const setAccount = useWalletStore((store) => store.setAccount);
  const setWallet = useWalletStore((store) => store.setWallet);
  const setSelector = useWalletStore((store) => store.setSelector);
  const selector = useWalletStore((store) => store.selector);

  useEffect(() => {
    const initialize = async () => {
      if (!setupPromise.current) {
        setupPromise.current = setupWalletSelector({
          network: 'mainnet',
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

      setSelector(selector, modal);
    };

    void initialize();
  }, [setSelector]);

  useEffect(() => {
    if (!selector) return;

    setState(selector.store.getState());

    const subscription = selector.store.observable.subscribe((value) => {
      setState(value);
      setAccount(value?.accounts[0] ?? null);

      if (value.accounts.length > 0 && value.selectedWalletId && selector) {
        selector
          .wallet()
          .then((wallet) => setWallet(wallet))
          .catch((error) => console.error(error));
      } else {
        setWallet(null);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [selector, setAccount, setState, setWallet]);
}
