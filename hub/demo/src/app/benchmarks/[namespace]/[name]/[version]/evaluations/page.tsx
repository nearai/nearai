'use client';

import { EvaluationsTable } from '@/components/EvaluationsTable';
import { useCurrentEntry } from '@/hooks/entries';

export default function EntryEvaluationsPage() {
  const { currentEntry } = useCurrentEntry('benchmark');

  if (!currentEntry) return null;

  return <EvaluationsTable entry={currentEntry} />;
}
