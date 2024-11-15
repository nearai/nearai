import { Placeholder } from '@near-pagoda/ui';
import { type ComponentProps, useEffect, useRef, useState } from 'react';

import { useDebouncedFunction } from '~/hooks/debounce';

import s from './IframeWithBlob.module.scss';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type IframePostMessageEventHandler<T = any> = (
  event: Omit<MessageEvent, 'data'> & {
    data: T;
  },
) => unknown;

type Props = ComponentProps<'iframe'> & {
  html: string;
  minHeight?: string;
  onPostMessage?: IframePostMessageEventHandler;
  postMessage?: unknown;
};

export const IframeWithBlob = ({
  className = '',
  html,
  minHeight,
  onPostMessage,
  postMessage,
  ...props
}: Props) => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [dataUrl, setDataUrl] = useState('');
  const previousHeightDiffRef = useRef(0);
  const previousHeightChangeUnixTimestampRef = useRef(0);
  const shouldClampHeightRef = useRef(false);
  const [height, __setHeight] = useState(0);
  const isLoading = !height;

  const executePostMessage = useDebouncedFunction((message: unknown) => {
    console.log('Sending postMessage to <IframeWithBlob />', message);
    iframeRef.current?.contentWindow?.postMessage(message, '*');
    /*
      NOTE: Since our iframe is sandboxed and doesn't have access to "allow-same-origin",
      it won't have an origin to check against. This forces us to use "*". Due to how this 
      component is utilized, we can safely use "*" as our postMessage origin.
    */
  }, 10);

  const setHeight = useDebouncedFunction((height: number) => {
    __setHeight((previousHeight) => {
      const previousHeightDiff = previousHeightDiffRef.current;
      const previousHeightChangeUnixTimestamp =
        previousHeightChangeUnixTimestampRef.current;
      const heightDiff = height - previousHeight;
      const elapsedMsSinceLastChange =
        Date.now() - previousHeightChangeUnixTimestamp;

      if (
        previousHeight > 0 &&
        heightDiff > 0 &&
        elapsedMsSinceLastChange < 25 &&
        previousHeightDiff === heightDiff
      ) {
        /*
          At this point we've detected an infinite loop where the iframe is 
          consistently growing in height. This is caused by an element inside 
          the iframe using viewport relative units like "vh" or "svh". To exit 
          this loop, we'll need to clamp the iframe height.
        */
        shouldClampHeightRef.current = true;
      }

      previousHeightChangeUnixTimestampRef.current = Date.now();
      previousHeightDiffRef.current = heightDiff;

      if (shouldClampHeightRef.current) {
        return Math.min(height, window.innerHeight);
      }

      return height;
    });
  }, 5);

  useEffect(() => {
    shouldClampHeightRef.current = false;
    const extendedHtml = extendHtml(html);
    const blob = new Blob([extendedHtml], { type: 'text/html;charset=UTF-8' });
    const url = URL.createObjectURL(blob);

    setDataUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [html]);

  useEffect(() => {
    function messageListener(event: MessageEvent) {
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data: unknown = event.data;

      if (data && typeof data === 'object') {
        if ('type' in data) {
          if (
            data.type === 'SET_HEIGHT' &&
            'height' in data &&
            typeof data.height === 'number'
          ) {
            setHeight(data.height || 0);
            return;
          }
        }
      }

      console.log('Received postMessage from <IframeWithBlob />', data);
      onPostMessage?.(event);
    }

    window.addEventListener('message', messageListener);

    return () => {
      window.removeEventListener('message', messageListener);
    };
  }, [onPostMessage, setHeight]);

  useEffect(() => {
    if (postMessage) {
      executePostMessage(postMessage);
    }
  }, [executePostMessage, postMessage]);

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
    <div
      className={s.iframeWrapper}
      style={{ minHeight }}
      data-loading={isLoading}
    >
      <div className={s.placeholder}>
        <Placeholder />
      </div>

      <iframe
        height={height}
        ref={iframeRef}
        src={dataUrl}
        sandbox="allow-scripts allow-popups"
        className={`${s.iframe} ${className}`}
        {...props}
      />
    </div>
  );
};

function extendHtml(html: string) {
  let wrappedHtml = html;
  const bodyStyle = getComputedStyle(document.body, null);
  const bodyBackgroundColor = bodyStyle.getPropertyValue('background-color');

  if (!html.includes('</body>')) {
    wrappedHtml = `<html><body>${html}</body></html>`;
  }

  const script = `
    <script>
      let hasLoaded = false;
      
      function setStyles() {
        document.documentElement.style.height = '100%';
        document.documentElement.style.background = '${bodyBackgroundColor}';
        document.body.style.margin = '0px';
        document.body.style.overflow = 'auto';
      }

      function setHeight() {
        if (!hasLoaded) return;

        setStyles();

        let height = 0;
        height = document.body.scrollHeight;

        window.parent.postMessage({
          type: "SET_HEIGHT",
          height
        }, '*');
      }

      setStyles();

      const mutationObserver = new MutationObserver(setHeight);
      mutationObserver.observe(document.body, {
        attributes: true,
        childList: true,
        subtree: true
      });

      const resizeObserver = new ResizeObserver(setHeight);
      resizeObserver.observe(document.body);

      window.addEventListener('load', () => {
        hasLoaded = true;
        setHeight();
      });
    </script>
  `;

  const extendedHtml = wrappedHtml.replace('</body>', `${script}</body>`);

  return extendedHtml;
}
