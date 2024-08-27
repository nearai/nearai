'use client';

import { useParams } from 'next/navigation';
import { AgentDetails } from './AgentDetails';

export default function RegistryItem() {
  const { category, accountId, name, version } = useParams();

  switch (category) {
    case 'agent':
      return <AgentDetails />;
    default:
      return (
        <div>
          <h1>Registry Item</h1>
        </div>
      );
  }
}
