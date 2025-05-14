import { Badge, Flex, SvgIcon, Text, Tooltip } from '@nearai/ui';
import { CircleNotch } from '@phosphor-icons/react/dist/ssr';
import { useEffect, useState } from 'react';

import s from './ThreadThinking.module.scss';

export const ThreadThinking = ({ length }: { length?: number }) => {
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
    <Flex gap="s" align="center">
      <SvgIcon
        icon={<CircleNotch weight="bold" />}
        size="xs"
        className={s.spinner}
        color="sand-10"
      />

      <Text color="sand-10" size="text-xs" weight={500} noWrap>
        Thinking
      </Text>

      {!!length && (
        <Tooltip content="Number of streamed tokens">
          <Badge
            label={length.toLocaleString()}
            count
            size="small"
            variant="neutral-alpha"
          />
        </Tooltip>
      )}

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
