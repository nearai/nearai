import type { CSSProperties, ReactNode } from 'react';

import {
  breakpointPropToCss,
  type ThemeBreakpointProps,
  type ThemeGap,
} from '~/utils/theme';

import s from './Grid.module.scss';

type Props = {
  children: ReactNode;
  className?: string;
  id?: string;
  style?: CSSProperties;
} & ThemeBreakpointProps<{
  align?: CSSProperties['alignItems'];
  columns?: CSSProperties['gridTemplateColumns'];
  gap?: ThemeGap;
  justify?: CSSProperties['justifyContent'];
}>;

export const Grid = ({ children, className = '', style, ...props }: Props) => {
  const variables = {
    ...breakpointPropToCss(props, 'align', 'grid-align'),
    ...breakpointPropToCss(props, 'columns', 'grid-columns'),
    ...breakpointPropToCss(props, 'gap', 'grid-gap', true),
    ...breakpointPropToCss(props, 'justify', 'grid-justify'),
  };

  return (
    <div
      className={`${s.grid} ${className}`}
      style={{
        ...style,
        ...variables,
      }}
      {...props}
    >
      {children}
    </div>
  );
};
