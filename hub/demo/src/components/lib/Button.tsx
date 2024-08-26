import Link from 'next/link';
import type { ComponentPropsWithRef, ReactElement } from 'react';
import { forwardRef } from 'react';

import s from './Button.module.scss';

type Fill = 'solid' | 'outline' | 'ghost';
type Size = 'small' | 'default' | 'large';
type Variant = 'primary' | 'secondary' | 'affirmative' | 'destructive';

type Props = Omit<ComponentPropsWithRef<'button'>, 'size'> & {
  fill?: Fill;
  href?: string;
  target?: ComponentPropsWithRef<'a'>['target'];
  icon?: ReactElement;
  iconLeft?: ReactElement;
  iconRight?: ReactElement;
  label: string;
  loading?: boolean;
  size?: Size;
  variant?: Variant;
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  (
    {
      className = '',
      disabled,
      fill = 'solid',
      href,
      icon,
      iconLeft,
      iconRight,
      label,
      loading,
      size = 'default',
      type = 'button',
      variant = 'primary',
      ...forwardedProps
    },
    ref,
  ) => {
    const conditionalAttributes: Record<string, unknown> = href
      ? {
          href,
        }
      : {
          type,
          disabled: disabled ?? loading,
        };

    if (icon) {
      conditionalAttributes['aria-label'] = label;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Element: any = href ? Link : 'button';

    return (
      <Element
        className={`${s.button} ${className}`}
        data-icon={!!icon}
        data-fill={fill}
        data-loading={loading}
        data-size={size}
        data-variant={variant}
        ref={ref}
        {...conditionalAttributes}
        {...forwardedProps}
      >
        <span className={s.inner}>
          {icon ? (
            <span className={s.icon}>{icon}</span>
          ) : (
            <>
              {iconLeft && <span className={s.icon}>{iconLeft}</span>}
              <span className={s.label}>{label}</span>
              {iconRight && <span className={s.icon}>{iconRight}</span>}
            </>
          )}
        </span>
      </Element>
    );
  },
);

Button.displayName = 'Button';
