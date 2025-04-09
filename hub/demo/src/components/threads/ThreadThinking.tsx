import { Flex, SvgIcon, Text } from '@nearai/ui';
import { CircleNotch } from '@phosphor-icons/react/dist/ssr';
import { useEffect, useState } from 'react';

import s from './ThreadThinking.module.scss';

export const ThreadThinking = () => {
  const [dotsInterval, setDotsInterval] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setDotsInterval((prev) => {
        if (prev === 6) {
          return 0;
        }

        return prev + 1;
      });
    }, 150);

    return () => clearInterval(interval);
  }, []);

  return (
    <Flex align="center" gap="s">
      <SvgIcon
        icon={<CircleNotch weight="bold" />}
        size="xs"
        className={s.spinner}
        color="sand-10"
      />
      <Text color="sand-10" size="text-xs" weight={500}>
        Thinking
      </Text>

      <Text color="sand-10" size="text-xs" weight={500}>
        {dotsInterval === 1 && '.'}
        {dotsInterval === 2 && '. .'}
        {dotsInterval === 3 && '. . .'}
        {dotsInterval === 4 && '. .'}
        {dotsInterval === 5 && '.'}
      </Text>
    </Flex>
  );
};
