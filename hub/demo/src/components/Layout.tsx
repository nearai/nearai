'use client';

import { PagodaUiProvider, Toaster } from '@near-pagoda/ui';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { type ComponentProps, type ReactNode } from 'react';

import { TRPCProvider } from '~/trpc/TRPCProvider';

import { Footer } from './Footer';
import s from './Layout.module.scss';
import { Navigation } from './Navigation';
import { NearInitializer } from './NearInitializer';
import { ZustandHydration } from './ZustandHydration';

export const Layout = ({ children }: { children: ReactNode }) => {
  const params = useSearchParams();

  return (
    <PagodaUiProvider
      value={{
        forcedTheme: params.get('theme') as NonNullable<
          ComponentProps<typeof PagodaUiProvider>['value']
        >['forcedTheme'],
        Link,
        useRouter,
      }}
    >
      <TRPCProvider>
        <NearInitializer />
        <ZustandHydration />
        <Toaster />

        <div className={s.wrapper}>
          <Navigation />
          <main className={s.main}>{children}</main>
          <Footer conditional />
        </div>
      </TRPCProvider>
    </PagodaUiProvider>
  );
};
