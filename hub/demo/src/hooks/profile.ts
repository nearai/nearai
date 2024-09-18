import { useParams } from 'next/navigation';

export function useProfileParams() {
  const { accountId } = useParams();

  return {
    accountId: accountId as string,
  };
}
