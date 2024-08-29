import { useEffect, useState } from 'react';

export type SortableTable = {
  column: string;
  order: 'ASCENDING' | 'DESCENDING';
};

type UseTableOptions<T extends Record<string, unknown>[] | undefined> = {
  data: T;
  sortColumn: T extends Record<string, unknown>[] ? keyof T[number] : never;
  sortOrder?: SortableTable['order'];
};

export function useTable<T extends Record<string, unknown>[] | undefined>({
  data,
  sortColumn,
  sortOrder = 'ASCENDING',
}: UseTableOptions<T>) {
  const [sort, setSort] = useState<SortableTable>({
    column: sortColumn!,
    order: sortOrder,
  });

  const sorted = [...(data ?? [])];

  sorted.sort((a, b) => {
    const valueA = (a[sort.column] as string | number) ?? '';
    const valueB = (b[sort.column] as string | number) ?? '';

    const compare = valueA.toString().localeCompare(valueB.toString());
    return sort.order === 'ASCENDING' ? compare : compare * -1;
  });

  useEffect(() => {
    setSort((v) => ({ ...v, order: sortOrder }));
  }, [sortOrder]);

  useEffect(() => {
    setSort((v) => ({ ...v, column: sortColumn }));
  }, [sortColumn]);

  return {
    sort,
    sorted,
    setSort,
  };
}
