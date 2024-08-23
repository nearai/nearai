'use client';

import type { ComponentPropsWithRef, ReactElement, ReactNode } from 'react';
import { forwardRef } from 'react';

import s from './Badge.module.scss';

type Variant = 'neutral' | 'primary' | 'warning' | 'success' | 'alert';

type Props = Omit<ComponentPropsWithRef<'span'>, 'children'> & {
  count?: boolean;
  iconLeft?: ReactElement;
  label: ReactNode;
  variant?: Variant;
  iconRight?: ReactElement;
};

export const Badge = forwardRef<HTMLSpanElement, Props>(
  (
    {
      className = '',
      count,
      label,
      iconLeft,
      iconRight,
      variant = 'primary',
      ...props
    },
    ref,
  ) => {
    return (
      <span
        className={`${s.badge} ${className}`}
        data-count={count}
        data-variant={variant}
        role={props.onClick ? 'button' : undefined}
        tabIndex={props.tabIndex ?? props.onClick ? 0 : undefined}
        ref={ref}
        {...props}
      >
        {iconLeft && <span className={s.icon}>{iconLeft}</span>}
        {label}
        {iconRight && <span className={s.icon}>{iconRight}</span>}
      </span>
    );
  },
);

Badge.displayName = 'Badge';
