import { type CSSProperties } from 'react';

import s from './HorizontalRule.module.scss';

type Props = {
  className?: string;
  style?: CSSProperties;
  variant?: 'primary' | 'secondary';
};

export const HR = ({
  className = '',
  variant = 'primary',
  ...props
}: Props) => {
  return (
    <hr className={`${s.hr} ${className}`} data-variant={variant} {...props} />
  );
};
