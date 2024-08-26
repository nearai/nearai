'use client';

import { NoSsr } from './NoSsr';

type Props = {
  date?: Date | null;
  options?: Intl.DateTimeFormatOptions;
};

export const Timestamp = ({
  date,
  options = {
    dateStyle: 'short',
    timeStyle: 'short',
  },
}: Props) => {
  if (!date) return null;
  return <NoSsr>{date.toLocaleString(undefined, options)}</NoSsr>;
};
