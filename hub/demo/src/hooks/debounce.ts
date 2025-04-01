// https://www.developerway.com/posts/debouncing-in-react

import debounce from 'lodash-es/debounce';
import { useEffect, useMemo, useRef, useState } from 'react';

export function useDebouncedFunction<T = void>(
  callback: T extends void ? () => unknown : (argument: T) => unknown,
  delay: number,
  leading = false,
) {
  const ref = useRef<(argument: T) => unknown>(undefined);

  useEffect(() => {
    ref.current = callback;
  }, [callback]);

  const debouncedCallback = useMemo(() => {
    const func = (argument: T) => {
      ref.current?.(argument);
    };

    return debounce(func, delay, { leading, trailing: !leading });
  }, [delay, leading]);

  return debouncedCallback;
}

export function useDebouncedValue<T>(value: T, delay: number) {
  const [internalValue, setInternalValue] = useState<T>(value);

  const updateValue = useDebouncedFunction(() => {
    setInternalValue(value);
  }, delay);

  useEffect(() => {
    updateValue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return internalValue;
}
