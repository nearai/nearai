import Link from 'next/link';
import { type ComponentPropsWithRef, forwardRef } from 'react';

import { type ThemeColor } from '~/utils/theme';

import s from './Card.module.scss';

type Props = ComponentPropsWithRef<'div'> & {
  animateIn?: boolean;
  href?: string;
  target?: ComponentPropsWithRef<'a'>['target'];
  background?: ThemeColor;
  border?: ThemeColor;
  padding?: 'm' | 'l';
  gap?: 'm' | 'l';
};

export const Card = forwardRef<HTMLDivElement, Props>(
  (
    {
      animateIn,
      background = 'white',
      border = 'sand5',
      className = '',
      gap,
      padding,
      style,
      ...props
    },
    ref,
  ) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Element: any = props.href ? Link : 'div';

    return (
      <Element
        className={`${s.card} ${className}`}
        data-animate-in={animateIn}
        data-background={background}
        data-gap={gap}
        data-padding={padding}
        role={props.onClick ? 'button' : undefined}
        tabIndex={props.tabIndex ?? props.onClick ? 0 : undefined}
        ref={ref}
        style={{
          '--card-background-color': `var(--${background})`,
          '--card-border-color': `var(--${border})`,
          ...style,
        }}
        {...props}
      />
    );
  },
);

Card.displayName = 'Card';

export const CardThumbnail = ({ alt, src }: { alt: string; src: string }) => {
  return (
    <div className={s.cardThumbnail}>
      <img alt={alt} src={src} />
    </div>
  );
};
