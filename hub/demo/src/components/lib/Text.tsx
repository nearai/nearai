import { type CSSProperties, type ReactNode } from 'react';

import { type ThemeColor, type ThemeFontSize } from '~/utils/theme';

import s from './Text.module.scss';

type Tag = 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'span' | 'label';

const defaultSizes: Record<Tag, ThemeFontSize> = {
  h1: 'text-3xl',
  h2: 'text-2xl',
  h3: 'text-xl',
  h4: 'text-l',
  h5: 'text-base',
  h6: 'text-s',
  p: 'text-base',
  span: 'text-base',
  label: 'text-base',
};

type Props = {
  as?: Tag;
  children: ReactNode;
  clampLines?: number;
  className?: string;
  color?: ThemeColor;
  decoration?: CSSProperties['textDecoration'];
  forceWordBreak?: boolean;
  id?: string;
  size?: ThemeFontSize;
  sizePhone?: ThemeFontSize;
  sizeTablet?: ThemeFontSize;
  style?: CSSProperties;
  noWrap?: boolean;
  weight?: string | number;
};

export const Text = ({
  as = 'p',
  children,
  clampLines,
  className = '',
  color,
  decoration,
  forceWordBreak,
  size,
  style,
  weight,
  noWrap,
  ...props
}: Props) => {
  const Tag = as;
  const defaultSize = defaultSizes[as];

  return (
    <Tag
      className={`${s.text} ${className}`}
      data-clamp-lines={clampLines}
      data-size={size ?? defaultSize}
      style={{
        color: color
          ? color === 'current'
            ? 'currentColor'
            : `var(--${color})`
          : undefined,
        textDecoration: decoration,
        fontWeight: weight,
        WebkitLineClamp: clampLines,
        whiteSpace: noWrap ? 'nowrap' : undefined,
        wordBreak: forceWordBreak ? 'break-word' : undefined,
        ...style,
      }}
      {...props}
    >
      {children}
    </Tag>
  );
};
