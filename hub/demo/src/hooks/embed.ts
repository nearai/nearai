import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

export function useIsEmbeddedIframe() {
  const path = usePathname();
  const [isEmbedded, setIsEmbedded] = useState(false);

  useEffect(() => {
    if (path.startsWith('/embed/')) {
      document.body.style.setProperty('--header-height', '0px');
      document.body.style.setProperty('--section-fill-height', '100svh');
      setIsEmbedded(true);
    }
  }, [path]);

  return { isEmbedded };
}
