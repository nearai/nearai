import { type CSSProperties } from 'react';

import s from './HorizontalRule.module.scss';

type Props = {
  className?: string;
  style?: CSSProperties;
};

export const HR = ({ className = '', ...props }: Props) => {
  return <hr className={`${s.hr} ${className}`} {...props} />;
};
