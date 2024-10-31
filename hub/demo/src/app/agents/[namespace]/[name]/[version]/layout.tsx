'use client';

import { BookOpenText, CodeBlock, Play } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { EntryDetailsLayout } from '~/components/EntryDetailsLayout';
import { env } from '~/env';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';

export default function EntryLayout({ children }: { children: ReactNode }) {
  return (
    <EntryDetailsLayout
      category="agent"
      defaultConsumerModePath="/run"
      tabs={
        !env.NEXT_PUBLIC_CONSUMER_MODE
          ? [
              {
                path: '',
                label: 'Overview',
                icon: <BookOpenText fill="bold" />,
              },
              {
                path: '/source',
                label: 'Source',
                icon: <CodeBlock fill="bold" />,
              },
              {
                path: '/run',
                label: 'Run',
                icon: <Play fill="bold" />,
              },
              {
                path: '/evaluations',
                label: 'Evaluations',
                icon: ENTRY_CATEGORY_LABELS.evaluation.icon,
              },
            ]
          : null
      }
    >
      {children}
    </EntryDetailsLayout>
  );
}
