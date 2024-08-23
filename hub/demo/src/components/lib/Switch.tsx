'use client';

import * as Primitive from '@radix-ui/react-switch';
import type { ComponentProps, ReactElement } from 'react';
import { forwardRef } from 'react';

import s from './Switch.module.scss';

type Props = ComponentProps<typeof Primitive.Switch> & {
  iconOff?: ReactElement;
  iconOn?: ReactElement;
  size?: 'small' | 'default';
};

export const Switch = forwardRef<HTMLButtonElement, Props>(
  ({ iconOff, iconOn, size = 'default', ...props }, ref) => {
    return (
      <Primitive.Switch
        className={s.switch}
        data-size={size}
        ref={ref}
        {...props}
      >
        <Primitive.SwitchThumb className={s.thumb}>
          {iconOff && (
            <span className={s.icon} data-icon-off>
              {iconOff}
            </span>
          )}

          {iconOn && (
            <span className={s.icon} data-icon-on>
              {iconOn}
            </span>
          )}
        </Primitive.SwitchThumb>
      </Primitive.Switch>
    );
  },
);
Switch.displayName = 'Switch';
