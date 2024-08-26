import { type ComponentPropsWithRef, forwardRef } from 'react';

type Props = ComponentPropsWithRef<'form'>;

export const Form = forwardRef<HTMLFormElement, Props>(
  (
    {
      autoCapitalize = 'off',
      autoCorrect = 'off',
      children,
      noValidate = true,
      ...props
    },
    ref,
  ) => {
    return (
      <form
        noValidate={noValidate}
        autoCapitalize={autoCapitalize}
        autoCorrect={autoCorrect}
        ref={ref}
        {...props}
      >
        {children}
      </form>
    );
  },
);
Form.displayName = 'Form';
