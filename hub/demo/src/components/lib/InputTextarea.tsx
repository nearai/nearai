'use client';

import type { ComponentPropsWithRef } from 'react';
import { forwardRef } from 'react';

import { type ThemeInputVariant } from '~/utils/theme';

import { AssistiveText } from './AssistiveText';
import s from './Input.module.scss';

type Props = ComponentPropsWithRef<'textarea'> & {
  assistive?: string;
  error?: string;
  label?: string;
  name: string;
  success?: string;
};

export const InputTextarea = forwardRef<HTMLTextAreaElement, Props>(
  ({ assistive, error, label, name, style, success, ...props }, ref) => {
    const assistiveTextId = `${name}-assistive-text`;
    const variant: ThemeInputVariant = error
      ? 'error'
      : success
        ? 'success'
        : 'default';

    return (
      <div
        className={s.wrapper}
        data-disabled={props.disabled}
        data-grow={typeof style?.width === 'undefined'}
        data-textarea="true"
        data-variant={variant}
        style={style}
      >
        <label className={s.labelWrapper}>
          <span className={s.label}>{label}</span>

          <div className={s.inputWrapper}>
            <textarea
              aria-errormessage={error ? assistiveTextId : undefined}
              aria-invalid={!!error}
              className={s.input}
              name={name}
              ref={ref}
              {...props}
            />
          </div>

          <AssistiveText
            variant={variant}
            message={error ?? success ?? assistive}
            id={assistiveTextId}
          />
        </label>
      </div>
    );
  },
);
InputTextarea.displayName = 'InputTextarea';
