import { type CSSProperties } from 'react';

import { Card } from './Card';
import { Flex } from './Flex';
import s from './Placeholder.module.scss';
import { Section, type SectionProps } from './Section';

type Props = {
  style?: CSSProperties;
};

export const Placeholder = (props: Props) => {
  return <span className={s.placeholder} data-placeholder {...props} />;
};

export const PlaceholderStack = (props: Props) => {
  return (
    <Flex direction="column" gap="s" {...props}>
      <Placeholder />
      <Placeholder />
      <Placeholder style={{ width: '75%' }} />
    </Flex>
  );
};

export const PlaceholderCard = (props: Props) => {
  return (
    <Card gap="s" {...props}>
      <Placeholder />
      <Placeholder />
      <Placeholder style={{ width: '75%' }} />
    </Card>
  );
};

export const PlaceholderSection = (props: SectionProps) => {
  return (
    <Section {...props} gap="s" bleed>
      <Placeholder />
      <Placeholder />
      <Placeholder style={{ width: '75%' }} />
    </Section>
  );
};
