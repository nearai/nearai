'use client';

import { BookOpenText, CodeBlock } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { EntryDetailsLayout } from '@/components/EntryDetailsLayout';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';

export default function EntryLayout({ children }: { children: ReactNode }) {
  return (
    <EntryDetailsLayout
      category="model"
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
        {
          path: '/evaluations',
          label: 'Evaluations',
          icon: ENTRY_CATEGORY_LABELS.evaluation.icon,
        },
      ]}
    >
      {children}
    </EntryDetailsLayout>
  );
}
