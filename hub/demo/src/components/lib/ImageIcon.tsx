import type { CSSProperties } from 'react';

import type { ThemeIconSize } from '~/utils/theme';

import s from './ImageIcon.module.scss';

type Props = {
  alt: string;
  className?: string;
  size?: ThemeIconSize;
  src: string;
  style?: CSSProperties;
};

export const ImageIcon = ({
  alt,
  className = '',
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
      <img src={src} alt={alt} />
    </div>
  );
};
