import { useParams } from 'next/navigation';

export function AgentDetails() {
  const { category, accountId, name, version } = useParams();

  // fetch agent from registry
  // show code
  // show metadata

  return (
    <div>
      <h1>Agent Details</h1>
    </div>
  );
}
