'use client';

import { MagnifyingGlass } from '@phosphor-icons/react';
import type {
  ComponentPropsWithRef,
  FormEventHandler,
  ReactElement,
} from 'react';
import { forwardRef } from 'react';

import type { NumberInputHandlerOptions } from '~/utils/input-handlers';
import { numberInputHandler } from '~/utils/input-handlers';
import { type ThemeInputVariant } from '~/utils/theme';

import { AssistiveText } from './AssistiveText';
import s from './Input.module.scss';

type Props = ComponentPropsWithRef<'input'> & {
  assistive?: string;
  error?: string;
  iconLeft?: ReactElement;
  iconRight?: ReactElement;
  label?: string;
  left?: ReactElement;
  name: string;
  number?: boolean | NumberInputHandlerOptions;
  right?: ReactElement;
  success?: string;
};

export const Input = forwardRef<HTMLInputElement, Props>(
  (
    {
      assistive,
      autoComplete,
      error,
      iconLeft,
      iconRight,
      inputMode,
      label,
      left,
      name,
      number,
      right,
      style,
      success,
      type = 'text',
      ...props
    },
    ref,
  ) => {
    const isNumber = Boolean(number);
    const assistiveTextId = `${name}-assistive-text`;
    const variant: ThemeInputVariant = error
      ? 'error'
      : success
        ? 'success'
        : 'default';

    if (type === 'search' && !iconLeft) {
      iconLeft = <MagnifyingGlass weight="bold" />;
    }

    const onInput: FormEventHandler<HTMLInputElement> = (event) => {
      if (isNumber) {
        const numberOptions = typeof number === 'object' ? number : undefined;
        numberInputHandler(event, numberOptions);
      }
      props.onInput && props.onInput(event);
    };

    return (
      <div
        className={s.wrapper}
        data-disabled={props.disabled}
        data-grow={typeof style?.width === 'undefined'}
        data-type={type}
        data-variant={variant}
        style={style}
      >
        <label className={s.labelWrapper}>
          {label && <span className={s.label}>{label}</span>}

          <div className={s.inputWrapper}>
            {iconLeft && (
              <span className={s.icon} aria-hidden="true">
                {iconLeft}
              </span>
            )}

            {left}

            <input
              aria-errormessage={error ? assistiveTextId : undefined}
              aria-invalid={!!error}
              autoComplete={autoComplete}
              className={s.input}
              data-1p-ignore={!autoComplete}
              inputMode={(inputMode ?? isNumber) ? 'decimal' : undefined}
              name={name}
              ref={ref}
              type={type}
              {...props}
              onInput={onInput}
              style={{
                textAlign: style?.textAlign,
              }}
            />

            {right}

            {iconRight && (
              <span className={s.icon} aria-hidden="true">
                {iconRight}
              </span>
            )}
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
Input.displayName = 'Input';
