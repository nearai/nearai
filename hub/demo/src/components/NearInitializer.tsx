'use client';

import { useNearInitializer } from '@/hooks/near';
import { useWalletInitializer } from '@/hooks/wallet';

export const NearInitializer = () => {
  useNearInitializer();
  useWalletInitializer();
  return null;
};
