'use client';

import { EntrySource } from '@/components/EntrySource';
import { useCurrentEntry } from '@/hooks/entries';

export default function EntrySourcePage() {
  const { currentEntry } = useCurrentEntry('dataset');

  if (!currentEntry) return null;

  return <EntrySource entry={currentEntry} />;
}
