'use client';

import { NearAiUiProvider, Toaster } from '@nearai/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type ReactNode, Suspense } from 'react';

import { useEmbedStore } from '@/stores/embed';
import { TRPCProvider } from '@/trpc/TRPCProvider';

import { Footer } from './Footer';
import s from './Layout.module.scss';
import { Navigation } from './Navigation';
import { NearInitializer } from './NearInitializer';
import { ZustandHydration } from './ZustandHydration';

export const Layout = ({ children }: { children: ReactNode }) => {
  const forcedTheme = useEmbedStore((store) => store.forcedTheme);

  return (
    <NearAiUiProvider
      value={{
        forcedTheme,
        Link,
        useRouter,
      }}
    >
      <TRPCProvider>
        <NearInitializer />
        <ZustandHydration />
        <Toaster />

        <Suspense>
          <div className={s.wrapper}>
            <Navigation />
            <main className={s.main}>{children}</main>
            <Footer conditional />
          </div>
        </Suspense>
      </TRPCProvider>
    </NearAiUiProvider>
  );
};
