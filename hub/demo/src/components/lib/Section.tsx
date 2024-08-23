import { type CSSProperties, type ReactNode } from 'react';

import { type ThemeColor, type ThemeGap } from '~/utils/theme';

import { Container } from './Container';
import { Flex } from './Flex';
import s from './Section.module.scss';

export type SectionProps = {
  background?: 'primary-gradient' | ThemeColor;
  bleed?: boolean;
  children?: ReactNode;
  className?: string;
  id?: string;
  gap?: ThemeGap;
  grow?: 'available' | 'screen-height';
  padding?: 'standard' | 'hero' | 'none';
  style?: CSSProperties;
};

export const Section = ({
  background,
  bleed, // No container or padding
  children,
  className = '',
  gap = 'l',
  grow,
  padding,
  style,
  ...props
}: SectionProps) => {
  const variables = {
    '--section-background-color': `var(--${background})`,
  };

  return (
    <section
      className={`${s.section} ${className}`}
      data-background={background}
      data-grow={grow}
      data-padding={bleed ? 'none' : padding}
      style={{
        ...style,
        ...variables,
      }}
      {...props}
    >
      {bleed ? (
        children
      ) : (
        <Container>
          <Flex direction="column" gap={gap}>
            {children}
          </Flex>
        </Container>
      )}
    </section>
  );
};
