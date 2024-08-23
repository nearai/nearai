import { type ReactNode, useCallback, useEffect, useRef } from 'react';

import { Button } from '../Button';
import { Text } from '../Text';
import s from './Banner.module.scss';
import { useBanner } from './hooks';

type Props = {
  /*
    NOTE: If an updated banner with new content is desired, consider changing the passed "bannerId" to 
    make sure users who had hidden the previous banner will see the new banner content.
  */

  bannerId: string;
  actions: ReactNode;
  message: ReactNode;
};

export const Banner = ({ actions, bannerId, message }: Props) => {
  const { bannerIsHidden, hideBanner } = useBanner(bannerId);
  const ref = useRef<HTMLDivElement | null>(null);

  const updateBannerHeightProperty = useCallback(() => {
    /*
      Since the mobile navigation menu relies on "position: fixed;", we need to calculate a dynamic 
      offset height based on the banner height and current window scroll position.
    */

    const element = ref.current;
    if (!element) return;

    const offsetHeight = Math.max(element.offsetHeight - window.scrollY, 0);

    if (bannerIsHidden) {
      document.body.style.removeProperty('--banner-nav-offset-height');
    } else {
      document.body.style.setProperty(
        '--banner-nav-offset-height',
        `${offsetHeight}px`,
      );
    }
  }, [bannerIsHidden]);

  useEffect(() => {
    updateBannerHeightProperty();

    function onWindowChange() {
      updateBannerHeightProperty();
    }

    window.addEventListener('resize', onWindowChange);
    window.addEventListener('scroll', onWindowChange);

    return () => {
      window.removeEventListener('resize', onWindowChange);
      window.removeEventListener('scroll', onWindowChange);
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bannerIsHidden]);

  if (bannerIsHidden) return null;

  return (
    <div className={s.banner} ref={ref}>
      <Text weight="500" sizePhone="text-xs">
        {message}
      </Text>

      <div className={s.actions}>{actions}</div>

      <Button
        type="button"
        onClick={hideBanner}
        label="Close"
        icon={<i className="ph-bold ph-x" />}
        size="small"
        className="close-button"
        fill="ghost"
      />
    </div>
  );
};
