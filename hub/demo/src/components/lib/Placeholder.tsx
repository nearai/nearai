import { type CSSProperties } from 'react';

import { Card } from './Card';
import s from './Placeholder.module.scss';
import { Section, type SectionProps } from './Section';

type Props = {
  style?: CSSProperties;
};

export const Placeholder = (props: Props) => {
  return <span className={s.placeholder} {...props} />;
};

export const PlaceholderCard = (props: Props) => {
  return (
    <Card {...props}>
      <Placeholder />
      <Placeholder />
      <Placeholder style={{ width: '70%' }} />
    </Card>
  );
};

export const PlaceholderSection = (props: SectionProps) => {
  return (
    <Section {...props} gap="m" bleed>
      <Placeholder />
      <Placeholder style={{ width: '80%' }} />
      <Placeholder style={{ width: '50%' }} />
    </Section>
  );
};
