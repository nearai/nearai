import type { CSSProperties, ReactNode } from 'react';

import s from './Container.module.scss';

export type ContainerSize = 'xs' | 's' | 'm' | 'l';

type Props = {
  children: ReactNode;
  className?: string;
  id?: string;
  size?: ContainerSize;
  style?: CSSProperties;
};

export const Container = ({ className = '', size = 'l', ...props }: Props) => {
  return (
    <div
      className={`${s.container} ${className}`}
      data-size={size}
      {...props}
    />
  );
};
