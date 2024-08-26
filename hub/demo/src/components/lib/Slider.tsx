'use client';

import * as Primitive from '@radix-ui/react-slider';
import { forwardRef } from 'react';

import { type ThemeInputVariant } from '~/utils/theme';

import { AssistiveText } from './AssistiveText';
import s from './Slider.module.scss';

type Props = {
  assistive?: string;
  error?: string;
  label: string;
  max: number;
  min: number;
  step?: number;
  name: string;
  onBlur?: (event: unknown) => void;
  success?: string;
  value: number | null | undefined;
  onChange: (value: number) => unknown;
};

export const Slider = forwardRef<HTMLInputElement, Props>(
  (
    { assistive, error, success, onChange, value, label, step = 1, ...props },
    ref,
  ) => {
    const variant: ThemeInputVariant = error
      ? 'error'
      : success
        ? 'success'
        : 'default';

    return (
      <label className={s.slider}>
        <span className={s.label}>
          {label}
          <span className={s.value}>: {value}</span>
        </span>

        <Primitive.Root
          className={s.root}
          ref={ref}
          value={value ? [value] : undefined}
          onValueChange={(v) => {
            onChange(v[0] ?? 0);
          }}
          step={step}
          {...props}
        >
          <Primitive.Track className={s.track}>
            <Primitive.Range className={s.range} />
          </Primitive.Track>
          <Primitive.Thumb className={s.thumb} aria-label={label} />
        </Primitive.Root>

        <AssistiveText
          variant={variant}
          message={error ?? success ?? assistive}
        />
      </label>
    );
  },
);
Slider.displayName = 'Slider';
