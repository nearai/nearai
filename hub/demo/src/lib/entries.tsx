import {
  ChartBar,
  Database,
  GraduationCap,
  Graph,
  Lightbulb,
  TerminalWindow,
} from '@phosphor-icons/react';
import { type ReactElement } from 'react';
import { type z } from 'zod';

import { type EntryCategory, type entryModel } from './models';

export const ENTRY_CATEGORY_LABELS: Record<
  // eslint-disable-next-line @typescript-eslint/ban-types
  EntryCategory | (string & {}),
  {
    icon: ReactElement;
    label: string;
  }
> = {
  agent: {
    icon: <Lightbulb />,
    label: 'Agent',
  },
  benchmark: {
    icon: <GraduationCap />,
    label: 'Benchmark',
  },
  dataset: {
    icon: <Database />,
    label: 'Dataset',
  },
  environment: {
    icon: <TerminalWindow />,
    label: 'Environment',
  },
  evaluation: {
    icon: <ChartBar />,
    label: 'Evaluation',
  },
  model: {
    icon: <Graph />,
    label: 'Model',
  },
};

export function primaryUrlForEntry(entry: z.infer<typeof entryModel>) {
  let url: string | undefined;

  switch (entry.category as EntryCategory) {
    case 'agent':
      url = `/agents/${entry.namespace}/${entry.name}/${entry.version}`;
      break;

    case 'benchmark':
      url = `/benchmarks/${entry.namespace}/${entry.name}/${entry.version}`;
      break;

    case 'dataset':
      url = `/datasets/${entry.namespace}/${entry.name}/${entry.version}`;
      break;

    case 'model':
      url = `/models/${entry.namespace}/${entry.name}/${entry.version}`;
      break;
  }

  return url;
}

export function benchmarkEvaluationsUrlForEntry(
  entry: z.infer<typeof entryModel>,
) {
  let url: string | undefined;

  switch (entry.category as EntryCategory) {
    case 'agent':
      url = `${primaryUrlForEntry(entry)}/evaluations`;
      break;

    case 'benchmark':
      url = `${primaryUrlForEntry(entry)}/evaluations`;
      break;

    case 'model':
      url = `${primaryUrlForEntry(entry)}/evaluations`;
      break;
  }

  return url;
}

export function idForEntry(entry: z.infer<typeof entryModel>) {
  return `${entry.namespace}/${entry.name}/${entry.version}`;
}
