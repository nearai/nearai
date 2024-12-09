'use client';

import { PagodaUiProvider, Toaster } from '@near-pagoda/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type ReactNode } from 'react';

import { TRPCReactProvider } from '~/trpc/react';

import { Footer } from './Footer';
import s from './Layout.module.scss';
import { Navigation } from './Navigation';
import { NearInitializer } from './NearInitializer';
import { ZustandHydration } from './ZustandHydration';

export const Layout = ({ children }: { children: ReactNode }) => {
  return (
    <PagodaUiProvider
      value={{
        Link,
        useRouter,
      }}
    >
      <TRPCReactProvider>
        <NearInitializer />
        <ZustandHydration />
        <Toaster />

        <div className={s.wrapper}>
          <Navigation />
          <main className={s.main}>{children}</main>
          <Footer conditional />
        </div>
      </TRPCReactProvider>
    </PagodaUiProvider>
  );
};
