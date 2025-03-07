import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

export function useEmbeddedWithinIframe() {
  const path = usePathname();
  const [embedded, setEmbedded] = useState(path.startsWith('/embed/'));

  useEffect(() => {
    if (path.startsWith('/embed/')) {
      setEmbedded(true);
    }
  }, [path]);

  return { embedded };
}
