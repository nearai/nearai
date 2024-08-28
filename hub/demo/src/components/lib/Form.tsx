import { type ComponentPropsWithRef, forwardRef } from 'react';

import s from './Form.module.scss';

type Props = ComponentPropsWithRef<'form'> & {
  stretch?: boolean;
};

export const Form = forwardRef<HTMLFormElement, Props>(
  (
    {
      autoCapitalize = 'off',
      autoCorrect = 'off',
      children,
      className = '',
      noValidate = true,
      stretch,
      ...props
    },
    ref,
  ) => {
    return (
      <form
        noValidate={noValidate}
        autoCapitalize={autoCapitalize}
        autoCorrect={autoCorrect}
        data-stretch={stretch}
        ref={ref}
        className={`${s.form} ${className}`}
        {...props}
      >
        {children}
      </form>
    );
  },
);
Form.displayName = 'Form';
