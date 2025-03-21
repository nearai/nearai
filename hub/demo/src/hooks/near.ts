import { connect, keyStores, type Near } from 'near-api-js';
import { useRef } from 'react';
import { useEffect } from 'react';

import { useNearStore } from '@/stores/near';

export function useNearInitializer() {
  const connectPromise = useRef<Promise<Near> | null>(null);
  const setKeyStore = useNearStore((store) => store.setKeyStore);
  const setNear = useNearStore((store) => store.setNear);
  const setViewAccount = useNearStore((store) => store.setViewAccount);

  useEffect(() => {
    const initialize = async () => {
      if (!connectPromise.current) {
        const keyStore = new keyStores.BrowserLocalStorageKeyStore();

        setKeyStore(keyStore);

        connectPromise.current = connect({
          networkId: 'mainnet',
          keyStore,
          nodeUrl: '/api/near-rpc-proxy',
        });
      }

      const near = await connectPromise.current;
      const viewAccount = await near.account('near');

      setNear(near);
      setViewAccount(viewAccount);
    };

    void initialize();
  }, [setNear, setViewAccount, setKeyStore]);
}
