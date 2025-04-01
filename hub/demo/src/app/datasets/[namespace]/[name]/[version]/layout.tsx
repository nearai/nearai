'use client';

import { BookOpenText, CodeBlock } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { EntryDetailsLayout } from '@/components/EntryDetailsLayout';

export default function EntryLayout({ children }: { children: ReactNode }) {
  return (
    <EntryDetailsLayout
      category="dataset"
      tabs={[
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
      ]}
    >
      {children}
    </EntryDetailsLayout>
  );
}
