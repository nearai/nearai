import {
  ChartBar,
  Database,
  GraduationCap,
  Graph,
  Lightbulb,
  TerminalWindow,
} from '@phosphor-icons/react';
import { type ReactElement } from 'react';

import { type EntryCategory } from './models';

export const ENTRY_CATEGORY_LABELS: Record<
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
