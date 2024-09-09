import {
  ChartBar,
  Database,
  Graph,
  Lightbulb,
  TerminalWindow,
} from '@phosphor-icons/react';
import { type ReactElement } from 'react';

import { type RegistryCategory } from '~/server/api/routers/hub';

export const CATEGORY_LABELS: Record<
  // eslint-disable-next-line @typescript-eslint/ban-types
  RegistryCategory | (string & {}),
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
    icon: <ChartBar />,
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
  model: {
    icon: <Graph />,
    label: 'Model',
  },
};
