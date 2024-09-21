import { type ComponentProps, useEffect, useRef, useState } from 'react';

import s from './IframeWithBlob.module.scss';

type Props = ComponentProps<'iframe'> & {
  html: string;
};

export const IframeWithBlob = ({ className = '', html, ...props }: Props) => {
  const hiddenHeightCalculationIframeRef = useRef<HTMLIFrameElement | null>(
    null,
  );
  const [dataUrl, setDataUrl] = useState('');
  const [height, setHeight] = useState(0);

  const resizeIframe = () => {
    const iframe = hiddenHeightCalculationIframeRef.current;
    setHeight((iframe?.contentWindow?.document.body.scrollHeight ?? 0) + 1);
  };

  useEffect(() => {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);

    setDataUrl(url);
    resizeIframe();

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [html]);

  useEffect(() => {
    function onResize() {
      resizeIframe();
    }
    window.addEventListener('resize', onResize);
    () => {
      window.removeEventListener('resize', onResize);
    };
  }, []);

  /*
    SECURITY NOTE:
    
    We should avoid adding "allow-same-origin" in combination with 
    "allow-scripts" to the sandbox flags. That would allow potentially 
    malicious JS access to the current user's local storage and cookies 
    (stealing their connected wallet keys, etc).

    The primary way this might happen is a bad actor generating malicious 
    HTML output with an agent and then sharing that agent or environment 
    URL to the public. Anyone who views that URL could have their secrets 
    compromised if they're signed in to AI Hub.
  */

  return (
    <div className={s.iframeWrapper}>
      <iframe
        height={0}
        ref={hiddenHeightCalculationIframeRef}
        src={dataUrl}
        onLoad={resizeIframe}
        sandbox="allow-same-origin"
        className={s.hiddenHeightCalculationIframe}
      />

      <iframe
        height={height}
        src={dataUrl}
        sandbox="allow-scripts"
        className={`${s.visibleIframe} ${className}`}
        data-loading={height < 10}
        {...props}
      />
    </div>
  );
};
