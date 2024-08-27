'use client';

import { useParams } from 'next/navigation';
import { RunAgent } from './RunAgent';

export default function RunPage() {
  const { category, accountId, name, version } = useParams();

  switch (category) {
    case 'model':
      return (
        <div>
          <h1>Model Details</h1>
        </div>
      );
    case 'agent':
      return <RunAgent />;
    default:
      return (
        <div>
          <h1>Registry Item</h1>
        </div>
      );
  }
}
