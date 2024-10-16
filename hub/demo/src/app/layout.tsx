import '~/styles/globals.scss';

import { ThemeProvider } from 'next-themes';
import { type ReactNode } from 'react';

import { Footer } from '~/components/Footer';
import { Toaster } from '~/components/lib/Toast';
import { Navigation } from '~/components/Navigation';
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
        <ThemeProvider attribute="class">
          <TRPCReactProvider>
            <ZustandHydration />
            <Toaster />

            <div className={s.wrapper}>
              <Navigation />
              <main className={s.main}>{children}</main>
              <Footer conditional />
            </div>
          </TRPCReactProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
