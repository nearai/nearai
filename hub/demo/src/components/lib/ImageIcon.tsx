import type { CSSProperties, ReactNode } from 'react';

import type { ThemeIconSize } from '~/utils/theme';

import s from './ImageIcon.module.scss';

type Props = {
  alt: string;
  className?: string;
  fallbackIcon?: ReactNode;
  size?: ThemeIconSize;
  src: string | undefined;
  style?: CSSProperties;
};

export const ImageIcon = ({
  alt,
  className = '',
  fallbackIcon,
  size = 'm',
  src,
  ...props
}: Props) => {
  return (
    <div
      className={`${s.imageIcon} ${className}`}
      data-icon
      data-size={size}
      {...props}
    >
      {src ? <img src={src} alt={alt} /> : fallbackIcon}
    </div>
  );
};
