import { useEffect, useState } from 'react';

const BANNER_HIDDEN_ID_KEY = 'banner-hidden';

export function useBanner(bannerId: string) {
  const [bannerIsHidden, setBannerIsHidden] = useState(true);

  useEffect(() => {
    const storedHiddenId = localStorage.getItem(BANNER_HIDDEN_ID_KEY);

    if (bannerId !== storedHiddenId) {
      setBannerIsHidden(false);
    }
  }, [bannerId]);

  const hideBanner = () => {
    setBannerIsHidden(true);
    localStorage.setItem(BANNER_HIDDEN_ID_KEY, bannerId);
  };

  return {
    bannerIsHidden,
    hideBanner,
  };
}
