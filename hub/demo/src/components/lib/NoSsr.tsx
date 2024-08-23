'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';

type Props = {
  children: ReactNode;
};

export const NoSsr = ({ children }: Props) => {
  const [shouldRender, setShouldRender] = useState(false);

  useEffect(() => {
    setShouldRender(true);
  }, []);

  if (!shouldRender) return null;

  return <>{children}</>;
};
