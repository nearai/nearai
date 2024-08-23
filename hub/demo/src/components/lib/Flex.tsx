import type { CSSProperties, ReactNode } from 'react';

import {
  breakpointPropToCss,
  type ThemeBreakpointProps,
  type ThemeGap,
} from '~/utils/theme';

import s from './Flex.module.scss';

type Props = {
  as?: 'div' | 'label' | 'span';
  children: ReactNode;
  className?: string;
  id?: string;
  style?: CSSProperties;
} & ThemeBreakpointProps<{
  align?: CSSProperties['alignItems'];
  direction?: CSSProperties['flexDirection'];
  gap?: ThemeGap;
  justify?: CSSProperties['justifyContent'];
  wrap?: CSSProperties['flexWrap'];
}>;

export const Flex = ({
  as = 'div',
  className = '',
  // phone,
  style,
  // tablet,
  ...props
}: Props) => {
  const Element = as;

  const variables = {
    ...breakpointPropToCss(props, 'align', 'flex-align'),
    ...breakpointPropToCss(props, 'direction', 'flex-direction'),
    ...breakpointPropToCss(props, 'gap', 'flex-gap', true),
    ...breakpointPropToCss(props, 'justify', 'flex-justify'),
    ...breakpointPropToCss(props, 'wrap', 'flex-wrap'),
  };

  return (
    <Element
      className={`${s.flex} ${className}`}
      style={{ ...style, ...variables }}
      {...props}
    />
  );
};
