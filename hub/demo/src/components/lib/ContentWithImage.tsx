import { type ReactNode } from 'react';

import s from './ContentWithImage.module.scss';

type Props = {
  alt: string;
  children: ReactNode;
  imageSide: 'left' | 'right';
  src: string;
};

export const ContentWithImage = ({ alt, src, imageSide, children }: Props) => {
  return (
    <div className={s.wrapper} data-image-side={imageSide}>
      <div className={s.image}>
        <img src={src} alt={alt} />
      </div>

      <div className={s.content}>{children}</div>
    </div>
  );
};
