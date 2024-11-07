'use client';

import '~/styles/globals.scss';
import '@near-pagoda/ui/styles.css';
import '@near-wallet-selector/modal-ui/styles.css';

import { PagodaUiProvider } from '@near-pagoda/ui';
import { Toaster } from '@near-pagoda/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type ReactNode } from 'react';

import { Footer } from '~/components/Footer';
import { Navigation } from '~/components/Navigation';
import { NearInitializer } from '~/components/NearInitializer';
import { ZustandHydration } from '~/components/ZustandHydration';
import { env } from '~/env';
import { TRPCReactProvider } from '~/trpc/react';

import s from './layout.module.scss';

/*
  The suppressHydrationWarning on <html> is required by <ThemeProvider>:
  https://github.com/pacocoursey/next-themes?tab=readme-ov-file#with-app
*/

export default function RootLayout({ children }: { children: ReactNode }) {
  const title = env.NEXT_PUBLIC_CONSUMER_MODE ? 'AI Chat' : 'AI Hub';

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>{title}</title>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, minimum-scale=1"
        />
        <meta name="description" content={`NEAR ${title}`} />
        <link rel="icon" href="/favicon.ico" />
      </head>

      <body>
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
      </body>
    </html>
  );
}
