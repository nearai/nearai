'use client';

import { Text } from '@nearai/ui';

import s from './StreamingText.module.scss';

export const StreamingText = ({
  text,
  latestChunk,
}: {
  text: string;
  latestChunk: string;
}) => {
  return (
    <Text>
      {text} <span className={s.streaming_glow}>{latestChunk}</span>
    </Text>
  );
};
