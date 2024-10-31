'use client';

import { CaretDown, CheckCircle, Circle } from '@phosphor-icons/react';
import { useCombobox } from 'downshift';
import type { CSSProperties, FocusEventHandler, ReactElement } from 'react';
import { useMemo, useRef } from 'react';
import { forwardRef } from 'react';
import { useEffect } from 'react';
import { useState } from 'react';

import { useDebouncedValue } from '~/hooks/debounce';
import { mergeRefs } from '~/utils/merge-refs';

import s from './Combobox.module.scss';
import { Input } from './Input';
import { SvgIcon } from './SvgIcon';
import { Text } from './Text';

export type ComboboxOption = {
  hidden?: boolean;
  label?: string;
  value: string | number;
};

type BaseProps = {
  allowCustomInput?: boolean;
  allowNone?: boolean;
  assistive?: string;
  error?: string;
  icon?: ReactElement;
  items: ComboboxOption[];
  label?: string;
  maxDropdownHeight?: string;
  name: string;
  noneLabel?: string;
  onBlur?: (event: unknown) => void;
  placeholder?: string;
  style?: CSSProperties;
  success?: string;
};

type ConditionalProps =
  | {
      value: number | null | undefined;
      number: true;
      onChange: (value: number | null) => unknown;
    }
  | {
      value: string | null | undefined;
      number?: never;
      onChange: (value: string | null) => unknown;
    };

type Props = BaseProps & ConditionalProps;

export const Combobox = forwardRef<HTMLInputElement, Props>(
  ({ allowCustomInput, allowNone, noneLabel, ...props }, ref) => {
    const noneItem = useMemo(() => {
      const item: ComboboxOption = {
        label: noneLabel ?? 'None',
        value: '__NONE__',
      };
      return item;
    }, [noneLabel]);

    const internalCurrentValue = useRef<string | number | null | undefined>(
      undefined,
    );
    const internalCurrentValueBeforeFocus = useRef<
      string | number | null | undefined
    >(undefined);
    const onBlurTimeout = useRef<NodeJS.Timeout>();
    const [filteredItems, setFilteredItems] = useState(
      allowNone ? [noneItem, ...props.items] : props.items,
    );
    const defaultSelectedItem = props.items.find(
      (item) => item.value === props.value,
    );
    const forceOverrideClosed = allowCustomInput && filteredItems.length === 0;
    const debouncedItems = useDebouncedValue(props.items, 25); // This debounce avoids race condition where prop.items updates before props.value

    const { selectItem, setInputValue, ...combobox } = useCombobox({
      id: props.name,
      defaultSelectedItem,
      items: filteredItems,
      itemToString(item) {
        return item ? (item.label ?? item.value.toString()) : '';
      },
      onInputValueChange(event) {
        const query = event.inputValue?.toLowerCase() ?? '';
        const items = allowNone ? [noneItem, ...props.items] : props.items;
        const results = items.filter((item) => {
          if (item.hidden) return false;
          const label = (item.label ?? item.value).toString().toLowerCase();
          return label.includes(query);
        });
        setFilteredItems(results);

        if (allowCustomInput) {
          if (props.number) {
            props.onChange(Number(event.inputValue) ?? null);
          } else {
            props.onChange(event.inputValue ?? '');
          }
        }
      },
      onSelectedItemChange(event) {
        const newValue =
          event.selectedItem?.value === '__NONE__'
            ? null
            : (event.selectedItem?.value ?? null);
        internalCurrentValue.current = newValue;

        // Do nothing if we're simply syncing with outside form state (this prevents us from prematurely marking a form as dirty):
        // eslint-disable-next-line @typescript-eslint/no-unsafe-enum-comparison
        if (event.type === '__function_select_item__') return;

        if (newValue === null) {
          props.onChange(null);
        } else if (props.number && typeof newValue === 'number') {
          props.onChange(newValue);
        } else if (!props.number && typeof newValue === 'string') {
          props.onChange(newValue);
        } else {
          throw new Error(
            `Combobox => Invalid value mismatch. ${props.name}, Expected type: ${
              props.number ? 'number' : 'string'
            }, Actual value type: ${typeof newValue}`,
          );
        }
      },
    });

    const onBlur: FocusEventHandler<HTMLInputElement> = (event) => {
      if (allowCustomInput) {
        if (!event.target.value) {
          setInputValue(
            internalCurrentValueBeforeFocus.current?.toString() ?? '',
          );
        }
      } else {
        setInputValue(
          combobox.selectedItem?.label ??
            combobox.selectedItem?.value.toString() ??
            '',
        );
      }

      props.onBlur && props.onBlur(event);

      onBlurTimeout.current = setTimeout(() => {
        const comboboxOnBlur = combobox.getInputProps().onBlur;
        comboboxOnBlur && comboboxOnBlur(event);
      }, 100);
    };

    const onFocus: FocusEventHandler<HTMLInputElement> = () => {
      internalCurrentValueBeforeFocus.current = combobox.getInputProps().value;

      clearTimeout(onBlurTimeout.current);

      setInputValue('');

      if (!combobox.isOpen) {
        combobox.openMenu();
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-explicit-any, @typescript-eslint/no-unnecessary-type-assertion, @typescript-eslint/no-unsafe-member-access
    const comboboxInputRef = (combobox.getInputProps() as any).ref; // This value actually exists, the types are wrong

    useEffect(() => {
      const items = allowNone ? [noneItem, ...props.items] : props.items;
      setFilteredItems(items.filter((item) => !item.hidden));
    }, [allowNone, noneItem, props.items]);

    useEffect(() => {
      const selected = debouncedItems.find(
        (item) => item.value === props.value,
      );

      if (props.value !== internalCurrentValue.current) {
        if (props.value === null && allowNone) {
          internalCurrentValue.current = null;
          selectItem(noneItem);
        } else {
          if (selected) {
            internalCurrentValue.current = selected.value;
            selectItem(selected);
          } else if (allowCustomInput) {
            internalCurrentValue.current = props.value;
            setInputValue(props.value?.toString() ?? '');
          } else {
            internalCurrentValue.current = null;
            selectItem(null);
          }
        }
      } else if (props.value !== null) {
        setInputValue(selected?.label ?? selected?.value.toString() ?? ''); // In the case of the selected item's label being updated, we need to update the input
      }
    }, [
      allowCustomInput,
      allowNone,
      noneItem,
      selectItem,
      props.value,
      debouncedItems,
      setInputValue,
    ]);

    return (
      <div
        className={s.wrapper}
        data-open={combobox.isOpen && !forceOverrideClosed}
        data-number={props.number}
        style={props.style}
      >
        <div className={s.innerWrapper}>
          <Input
            {...combobox.getInputProps()}
            assistive={props.assistive}
            error={props.error}
            iconLeft={props.icon}
            label={props.label}
            name={props.name}
            number={props.number}
            onBlur={onBlur}
            // eslint-disable-next-line @typescript-eslint/no-empty-function
            onClick={() => {}} // Ignore this library change: https://github.com/downshift-js/downshift/blob/master/src/hooks/MIGRATION_V8.md#usecombobox-input-click
            onFocus={onFocus}
            placeholder={props.placeholder}
            // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
            ref={mergeRefs([ref, comboboxInputRef])}
            right={
              <>
                <button
                  type="button"
                  className={s.toggleButton}
                  {...combobox.getToggleButtonProps()}
                >
                  <SvgIcon icon={<CaretDown weight="bold" />} />
                </button>

                <ul
                  className={s.dropdown}
                  {...combobox.getMenuProps()}
                  style={{ maxHeight: props.maxDropdownHeight }}
                >
                  {filteredItems.map((item, index) => (
                    <li
                      className={s.dropdownItem}
                      data-highlighted={combobox.highlightedIndex === index}
                      data-selected={
                        combobox.selectedItem?.value === item.value
                      }
                      key={item.value}
                      {...combobox.getItemProps({ item, index })}
                    >
                      {combobox.selectedItem?.value === item.value ? (
                        <SvgIcon
                          icon={<CheckCircle weight="duotone" />}
                          color="green-9"
                        />
                      ) : (
                        <SvgIcon
                          icon={<Circle weight="duotone" />}
                          color="sand-10"
                        />
                      )}

                      {item.label ?? item.value}
                    </li>
                  ))}

                  {filteredItems.length === 0 && (
                    <li className={s.content}>
                      <Text size="text-s">
                        {props.items.length === 0
                          ? 'No available options.'
                          : 'No matching options. Try a different search?'}
                      </Text>
                    </li>
                  )}
                </ul>
              </>
            }
            success={props.success}
          />
        </div>
      </div>
    );
  },
);
Combobox.displayName = 'Combobox';
