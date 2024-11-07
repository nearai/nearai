import { Button, openToast, SvgIcon, Tooltip } from '@near-pagoda/ui';
import { Star } from '@phosphor-icons/react';
import { type CSSProperties, useEffect, useState } from 'react';
import { type z } from 'zod';

import { signInWithNear } from '~/lib/auth';
import { type entryModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';

import s from './StarButton.module.scss';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  style?: CSSProperties;
  variant: 'simple' | 'detailed';
};

export const StarButton = ({ entry, style, variant = 'simple' }: Props) => {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const [starred, setStarred] = useState(false);
  const [count, setCount] = useState(0);
  const [clicked, setClicked] = useState(false);
  const starMutation = api.hub.starEntry.useMutation();
  const visuallyStarred = isAuthenticated && starred;

  useEffect(() => {
    setCount(entry?.num_stars ?? 0);
    setClicked(false);
  }, [entry]);

  useEffect(() => {
    setStarred(!!entry?.starred_by_point_of_view);
    setClicked(false);
  }, [entry]);

  const toggleStar = () => {
    if (!entry) return;

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
      starMutation.mutate({
        action: 'remove',
        name: entry.name,
        namespace: entry.namespace,
      });
    } else {
      setStarred(true);
      setCount((value) => value + 1);
      starMutation.mutate({
        action: 'add',
        name: entry.name,
        namespace: entry.namespace,
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
