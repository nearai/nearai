import { Placeholder } from '@nearai/ui';
import { type ComponentProps, useEffect, useRef, useState } from 'react';

import { useDebouncedFunction } from '@/hooks/debounce';

import s from './IframeWithBlob.module.scss';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type IframePostMessageEventHandler<T = any> = (
  event: Omit<MessageEvent, 'data'> & {
    data: T;
  },
) => unknown;

type Props = Omit<ComponentProps<'iframe'>, 'nonce'> & {
  html: string;
  height?: 'auto' | (string & {});
  fixedHeight?: string;
  onPostMessage?: IframePostMessageEventHandler;
  postMessage?: unknown;
};

export const IframeWithBlob = ({
  className = '',
  height = 'auto',
  html,
  onPostMessage,
  postMessage,
  ...props
}: Props) => {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [dataUrl, setDataUrl] = useState('');
  const [computedHeight, __setComputedHeight] = useState(0);
  const isLoading = height === 'auto' ? !computedHeight : false;

  const executePostMessage = useDebouncedFunction((message: unknown) => {
    console.log('Sending postMessage to <IframeWithBlob />', message);
    iframeRef.current?.contentWindow?.postMessage(message, '*');
    /*
      NOTE: Since our iframe is sandboxed and doesn't have access to "allow-same-origin",
      it won't have an origin to check against. This forces us to use "*". Due to how this 
      component is utilized, we can safely use "*" as our postMessage origin.
    */
  }, 10);

  const setComputedHeight = useDebouncedFunction((value: number) => {
    if (height !== 'auto') return;
    __setComputedHeight(() => {
      const newHeight = Math.max(wrapperRef.current?.offsetHeight ?? 0, value);
      return newHeight;
    });
  }, 10);

  const resetComputedHeight = useDebouncedFunction(() => {
    __setComputedHeight(-1);
  }, 150);

  useEffect(() => {
    function resize() {
      resetComputedHeight();
    }
    window.addEventListener('resize', resize);
    () => {
      window.removeEventListener('resize', resize);
    };
  }, [resetComputedHeight]);

  useEffect(() => {
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
            setComputedHeight(data.height || 0);
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
  }, [onPostMessage, setComputedHeight]);

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
    <div className={s.iframeWrapper} data-loading={isLoading} ref={wrapperRef}>
      <div className={s.placeholder}>
        <Placeholder />
      </div>

      <iframe
        ref={iframeRef}
        src={dataUrl}
        sandbox="allow-scripts allow-popups"
        className={`${s.iframe} ${className}`}
        style={{
          height:
            height === 'auto'
              ? computedHeight === -1
                ? undefined
                : `${computedHeight}px`
              : height,
          paddingRight: computedHeight === -1 ? '1px' : undefined,

          /*
            When computedHeight is -1, we adjust the styles above to trigger a 
            ResizeObserver event within the iframe. This will then trigger a 
            SET_HEIGHT postMessage from the iframe to update computedHeight 
            with an updated value.
          */
        }}
        {...props}
      />
    </div>
  );
};

function extendHtml(html: string) {
  let wrappedHtml = html;
  const bodyStyle = getComputedStyle(document.body, null);
  const bodyBackgroundColor = bodyStyle.getPropertyValue('background-color');

  const globalStyles = `
    <style>
      * { box-sizing: border-box !important; }
    </style>
  `;

  if (!html.includes('</body>')) {
    wrappedHtml = `<html><head></head><body>${html}</body></html>`;
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

  const viewportMeta =
    '<meta name="viewport" content="width=device-width, initial-scale=1, minimum-scale=1">';

  const extendedHtml = wrappedHtml
    .replace('</body>', `${script}${globalStyles}</body>`)
    .replace('</head>', `${viewportMeta}</head>`);

  return extendedHtml;
}
