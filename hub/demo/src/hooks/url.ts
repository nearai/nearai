import { usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useMemo } from 'react';

export function useQueryParams<const T extends string[]>(names: T) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const createQueryPath = useCallback(
    (updatedParams: Partial<Record<T[number], string | undefined>>) => {
      const params = new URLSearchParams(searchParams.toString());

      Object.entries(updatedParams).forEach(([name, value]) => {
        if (typeof value === 'string' && value) {
          params.set(name, value);
        } else {
          params.delete(name);
        }
      });

      return `${pathname}?${params.toString()}`;
    },
    [pathname, searchParams],
  );

  const queryParams = useMemo(() => {
    const params: Record<string, string> = {};

    names.forEach((name) => {
      const value = searchParams.get(name);
      if (value) {
        params[name] = value;
      }
    });

    return params as Partial<Record<T[number], string>>;
  }, [names, searchParams]);

  return {
    createQueryPath,
    queryParams,
  };
}
