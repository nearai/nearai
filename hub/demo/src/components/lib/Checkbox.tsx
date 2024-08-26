import { Check } from '@phosphor-icons/react';
import { type ComponentPropsWithRef, forwardRef } from 'react';

import s from './Checkbox.module.scss';

type Props = Omit<ComponentPropsWithRef<'input'>, 'type' | 'name'> & {
  name: string;
  type?: 'checkbox' | 'radio';
};

export const Checkbox = forwardRef<HTMLInputElement, Props>(
  ({ className = '', type = 'checkbox', ...props }, ref) => {
    return (
      <div className={`${s.checkbox} ${className}`}>
        <input type={type} {...props} ref={ref} />
        <Check weight="bold" />
      </div>
    );
  },
);
Checkbox.displayName = 'Checkbox';

export const CheckboxGroup = forwardRef<HTMLInputElement, Props>(
  ({ className = '', ...props }, ref) => {
    return (
      <div
        role="group"
        className={`${s.group} ${className}`}
        ref={ref}
        {...props}
      />
    );
  },
);
CheckboxGroup.displayName = 'CheckboxGroup';
