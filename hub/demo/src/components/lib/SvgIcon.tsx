import type { CSSProperties, ReactElement } from 'react';

import type { ThemeColor, ThemeIconSize } from '~/utils/theme';

import s from './SvgIcon.module.scss';

type Props = {
  className?: string;
  color?: ThemeColor;
  icon: ReactElement;
  noFill?: boolean;
  noStroke?: boolean;
  size?: ThemeIconSize;
  style?: CSSProperties;
};

export const SvgIcon = ({
  className = '',
  color = 'current',
  icon,
  noFill,
  noStroke,
  size = 's',
  style,
  ...props
}: Props) => {
  return (
    <div
      className={`${s.svgIcon} ${className}`}
      data-color={color}
      data-icon
      data-size={size}
      data-no-fill={noFill}
      data-no-stroke={noStroke}
      style={{
        color: color
          ? color === 'current'
            ? 'currentColor'
            : `var(--${color})`
          : undefined,
        ...style,
      }}
      {...props}
    >
      {icon}
    </div>
  );
};
