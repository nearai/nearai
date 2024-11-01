import { type ComponentProps, useEffect, useRef, useState } from 'react';

import { useDebouncedFunction } from '~/hooks/debounce';

import s from './IframeWithBlob.module.scss';

function extendHtml(html: string) {
  let wrappedHtml = html;

  if (!html.includes('</body>')) {
    wrappedHtml = `<html><body>${html}</body></html>`;
  }

  const script = `
    <style>
      html, body {
        margin: 0 !important;
        overflow: hidden !important;
      }

      body :first-child, #iframe-height-calculator :first-child {
        margin-top: 0 !important;
      }

      #iframe-height-calculator {
        overflow: hidden;
        position: absolute;
        left: 0;
        right: 0;
        top: 0;
        z-index: -1;
        opacity: 0;
        pointer-events: none;
      }
    </style>

    <script>
      let isCalculatingHeight = false;

      function setHeight() {
        isCalculatingHeight = true;

        const calculator = document.createElement('div');
        calculator.id = 'iframe-height-calculator';
        calculator.innerHTML = document.body.innerHTML;
        document.body.append(calculator);
        const height = calculator.offsetHeight;
        calculator.remove();

        window.parent.postMessage({
          type: "SET_HEIGHT",
          height
        }, '*');

        setTimeout(() => {
          isCalculatingHeight = false;
        });
      }

      const mutationObserver = new MutationObserver((mutations) => {
        if (!isCalculatingHeight) setHeight();
      });
      mutationObserver.observe(document.body, {
        attributes: true,
        childList: true,
        subtree: true
      });

      const resizeObserver = new ResizeObserver(() => setHeight());
      resizeObserver.observe(document.body);
      
      setHeight();

      const paragraphs = document.querySelectorAll('p');
      paragraphs.forEach((p) => p.addEventListener('click', () => p.remove()));
    </script>
  `;

  const extended = wrappedHtml.replace('</body>', `${script}</body>`);

  return extended;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type IframePostMessageEventHandler<T = any> = (
  event: Omit<MessageEvent, 'data'> & {
    data: T;
  },
) => unknown;

type Props = ComponentProps<'iframe'> & {
  html: string;
  onPostMessage?: IframePostMessageEventHandler;
  postMessage?: unknown;
};

export const IframeWithBlob = ({
  className = '',
  html,
  onPostMessage,
  postMessage,
  ...props
}: Props) => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [dataUrl, setDataUrl] = useState('');
  const [height, setHeight] = useState(0);

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
      console.log('Received postMessage from <IframeWithBlob />', data);

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
    <div className={s.iframeWrapper}>
      <iframe
        height={height}
        ref={iframeRef}
        src={dataUrl}
        sandbox="allow-scripts allow-popups"
        className={`${s.visibleIframe} ${className}`}
        data-loading={height < 1}
        {...props}
      />
    </div>
  );
};
