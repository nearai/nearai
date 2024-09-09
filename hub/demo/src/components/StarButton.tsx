import { Star } from '@phosphor-icons/react';
import { type CSSProperties, useEffect, useState } from 'react';

import { Button } from './lib/Button';
import { SvgIcon } from './lib/SvgIcon';
import { Tooltip } from './lib/Tooltip';
import s from './StarButton.module.scss';

type Props = {
  count: number;
  variant: 'simple' | 'detailed';
  starred: boolean;
  style?: CSSProperties;
};

export const StarButton = ({ style, variant = 'simple', ...props }: Props) => {
  const [starred, setStarred] = useState(false);
  const [count, setCount] = useState(0);
  const [clicked, setClicked] = useState(false);

  useEffect(() => {
    setCount(props.count);
    setClicked(false);
  }, [props.count]);

  useEffect(() => {
    setStarred(props.starred);
    setClicked(false);
  }, [props.starred]);

  const toggleStar = () => {
    setClicked(true);

    if (starred) {
      setStarred(false);
      setCount((value) => Math.max(0, value - 1));
    } else {
      setStarred(true);
      setCount((value) => value + 1);
    }
  };

  return (
    <Tooltip
      asChild
      content={starred ? 'Unstar' : 'Star'}
      disabled={variant === 'detailed' && !starred}
    >
      <Button
        label={
          variant === 'simple' ? count.toString() : starred ? `Starred` : `Star`
        }
        iconLeft={
          starred ? (
            <SvgIcon size="xs" icon={<Star weight="fill" />} color="amber-10" />
          ) : (
            <SvgIcon size="xs" icon={<Star />} color="sand-9" />
          )
        }
        count={variant === 'detailed' ? count : undefined}
        size="small"
        variant="secondary"
        fill={variant === 'simple' ? 'ghost' : 'outline'}
        onClick={toggleStar}
        style={{
          ...style,
          fontVariantNumeric: 'tabular-nums',
        }}
        className={s.starButton}
        data-clicked={clicked}
        data-starred={starred}
      />
    </Tooltip>
  );
};
