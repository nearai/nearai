import { type ReactNode } from 'react';

import { type ThemeColor } from '~/utils/theme';

import s from './IconCircle.module.scss';

type Props = {
  color?: ThemeColor;
  icon: ReactNode;
};

export const IconCircle = ({ color = 'sand-11', icon }: Props) => {
  return (
    <div
      className={s.iconCircle}
      style={{
        color: color
          ? color === 'current'
            ? 'currentColor'
            : `var(--${color})`
          : undefined,
      }}
    >
      {icon}
    </div>
  );
};
