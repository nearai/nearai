import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useMemo } from 'react';

export function useQueryParams<const T extends string[]>(names: T) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const createQueryPath = useCallback(
    (updatedParams: Partial<Record<T[number], string | null>>) => {
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

  const updateQueryPath = useCallback(
    (
      updatedParams: Partial<Record<T[number], string | null>>,
      mode: 'push' | 'replace' = 'push',
      scroll = true,
    ) => {
      const path = createQueryPath(updatedParams);

      if (mode === 'replace') {
        router.replace(path, { scroll });
      } else {
        router.push(path, { scroll });
      }
    },
    [createQueryPath, router],
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

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return {
    createQueryPath,
    queryParams,
    updateQueryPath,
  };
}
