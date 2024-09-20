'use client';

import { BookOpenText } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { EntryDetailsLayout } from '~/components/EntryDetailsLayout';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';

export default function EntryLayout({ children }: { children: ReactNode }) {
  return (
    <EntryDetailsLayout
      category="benchmark"
      tabs={[
        {
          path: '',
          label: 'Overview',
          icon: <BookOpenText fill="bold" />,
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
