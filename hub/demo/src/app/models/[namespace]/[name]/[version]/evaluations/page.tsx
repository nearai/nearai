'use client';

import { EvaluationsTable } from '@/components/EvaluationsTable';
import { useCurrentEntry } from '@/hooks/entries';

export default function EntryEvaluationsPage() {
  const { currentEntry } = useCurrentEntry('model');

  if (!currentEntry) return null;

  return <EvaluationsTable entry={currentEntry} />;
}
