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
  minHeight = '50vh',
  onPostMessage,
  postMessage,
  ...props
}: Props) => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [dataUrl, setDataUrl] = useState('');
  const [height, setHeight] = useState(0);
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
            const height = data.height || 0;
            setHeight(height);
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
  }, [onPostMessage]);

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
      {isLoading && (
        <Placeholder
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            width: '100%',
            zIndex: 10,
          }}
        />
      )}

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

  if (!html.includes('</body>')) {
    wrappedHtml = `<html><body>${html}</body></html>`;
  }

  const script = `
    <script>
      function setHeight() {
        document.body.style.height = '1px';
        document.body.style.display = 'block';
        document.body.style.overflow = 'auto';

        const bodyStyle = getComputedStyle(document.body, null);
        const bodyPaddingBottom = parseInt(bodyStyle.getPropertyValue('padding-bottom').replace('px', ''));
        const bodyMarginBottom = parseInt(bodyStyle.getPropertyValue('margin-bottom').replace('px', ''));

        let height = 0;
        const ignoreTags = ['SCRIPT', 'STYLE'];
        const ignorePositions = ['fixed', 'absolute'];

        for (let i = document.body.children.length; i >= 0; i--) {
          const child = document.body.children[i];
          if (child && !ignoreTags.includes(child.tagName)) {
            const style = getComputedStyle(child, null);
            const position = style.getPropertyValue('position');
            const display = style.getPropertyValue('display');
            if (display !== 'none' && ![ignorePositions].includes(position)) {
              height = child.getBoundingClientRect().bottom + window.scrollY + bodyPaddingBottom + bodyMarginBottom;
              break;
            }
          }
        }

        window.parent.postMessage({
          type: "SET_HEIGHT",
          height
        }, '*');
      }

      const mutationObserver = new MutationObserver(setHeight);
      mutationObserver.observe(document.body, {
        attributes: true,
        childList: true,
        subtree: true
      });

      const resizeObserver = new ResizeObserver(setHeight);
      resizeObserver.observe(document.body);

      setHeight();

      window.addEventListener('load', setHeight);
    </script>
  `;

  const extendedHtml = wrappedHtml.replace('</body>', `${script}</body>`);

  return extendedHtml;
}
