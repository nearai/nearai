import { Star } from '@phosphor-icons/react';
import { type CSSProperties, useEffect, useState } from 'react';
import { type z } from 'zod';

import { signInWithNear } from '~/lib/auth';
import { type registryEntry } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';

import { Button } from './lib/Button';
import { SvgIcon } from './lib/SvgIcon';
import { openToast } from './lib/Toast';
import { Tooltip } from './lib/Tooltip';
import s from './StarButton.module.scss';

type Props = {
  item: z.infer<typeof registryEntry> | undefined;
  style?: CSSProperties;
  variant: 'simple' | 'detailed';
};

export const StarButton = ({ item, style, variant = 'simple' }: Props) => {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const [starred, setStarred] = useState(false);
  const [count, setCount] = useState(0);
  const [clicked, setClicked] = useState(false);
  const mutation = api.hub.starRegistryEntry.useMutation();
  const visuallyStarred = isAuthenticated && starred;

  useEffect(() => {
    setCount(item?.num_stars ?? 0);
    setClicked(false);
  }, [item]);

  useEffect(() => {
    setStarred(!!item?.starred_by_point_of_view);
    setClicked(false);
  }, [item]);

  const toggleStar = () => {
    if (!item) return;

    if (!isAuthenticated) {
      openToast({
        type: 'info',
        title: 'Please Sign In',
        description:
          'Signing in will allow you to star and interact with agents and other resources',
        actionText: 'Sign In',
        action: signInWithNear,
        duration: Infinity,
      });
      return;
    }

    setClicked(true);

    if (starred) {
      setStarred(false);
      setCount((value) => Math.max(0, value - 1));
      mutation.mutate({
        action: 'remove',
        name: item.name,
        namespace: item.namespace,
      });
    } else {
      setStarred(true);
      setCount((value) => value + 1);
      mutation.mutate({
        action: 'add',
        name: item.name,
        namespace: item.namespace,
      });
    }
  };

  return (
    <Tooltip
      asChild
      content={visuallyStarred ? 'Unstar' : 'Star'}
      disabled={variant === 'detailed' && !visuallyStarred}
    >
      <Button
        label={
          variant === 'simple'
            ? count.toString()
            : visuallyStarred
              ? `Starred`
              : `Star`
        }
        iconLeft={
          visuallyStarred ? (
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
        data-starred={visuallyStarred}
      />
    </Tooltip>
  );
};
