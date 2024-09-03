'use client';

import { FileArrowUp, Paperclip } from '@phosphor-icons/react';
import type {
  ChangeEventHandler,
  CSSProperties,
  DragEventHandler,
  FocusEventHandler,
} from 'react';
import { forwardRef, useState } from 'react';

import { useDebouncedValue } from '~/hooks/debounce';
import { formatBytes } from '~/utils/number';

import { AssistiveText } from './AssistiveText';
import s from './FileInput.module.scss';
import { SvgIcon } from './SvgIcon';
import { Text } from './Text';
import { openToast } from './Toast';

type Props = {
  // eslint-disable-next-line @typescript-eslint/ban-types
  accept: '*' | 'image/*' | 'audio/*' | 'video/*' | (string & {}); // https://stackoverflow.com/a/61048124
  className?: string;
  disabled?: boolean;
  error?: string;
  label?: string;
  maxFileSizeBytes?: number;
  multiple?: boolean;
  name: string;
  onBlur?: FocusEventHandler<HTMLInputElement>;
  onChange: (value: File[] | null) => unknown;
  style?: CSSProperties;
  value?: File[] | null | undefined;
};

export const FileInput = forwardRef<HTMLInputElement, Props>(
  (
    {
      accept,
      className = '',
      disabled,
      label,
      error,
      maxFileSizeBytes,
      multiple,
      name,
      style,
      value,
      ...props
    },
    ref,
  ) => {
    const [isDragging, setIsDragging] = useState(false);
    const isDraggingDebounced = useDebouncedValue(isDragging, 50);
    const assistiveTextId = `${name}-assistive-text`;

    const handleFileListChange = (fileList: FileList | null) => {
      let files = [...(fileList ?? [])];
      if (!multiple) {
        files = files.slice(0, 1);
      }

      const accepted = accept.split(',').map((type) => type.trim());
      const errors: string[] = [];

      const validFiles = files.filter((file) => {
        const fileTypeCategory = file.type.split('/').shift()!;
        const fileExtension = file.name.split('.').pop()!;

        const fileTypeIsValid =
          accepted.includes('*') ||
          accepted.includes(`${fileTypeCategory}/*`) ||
          accepted.includes(file.type) ||
          accepted.includes(`.${fileExtension}`);

        const fileSizeIsValid =
          !maxFileSizeBytes || file.size <= maxFileSizeBytes;

        if (!fileTypeIsValid) {
          errors.push(
            `File type not allowed: ${file.type}. Allowed file types: ${accept}`,
          );
          return false;
        }

        if (!fileSizeIsValid) {
          errors.push(
            `File size exceeds maximum of: ${formatBytes(maxFileSizeBytes)}`,
          );
          return false;
        }

        return true;
      });

      errors.forEach((error) => {
        openToast({
          type: 'error',
          title: 'Invalid File',
          description: error,
        });
      });

      props.onChange(validFiles.length > 0 ? validFiles : null);
    };

    const onChange: ChangeEventHandler<HTMLInputElement> = (event) => {
      handleFileListChange(event.target.files);
    };

    const onDragLeave: DragEventHandler<HTMLLabelElement> = () => {
      setIsDragging(false);
    };

    const onDragOver: DragEventHandler<HTMLLabelElement> = (event) => {
      event.preventDefault();
      setIsDragging(true);
    };

    const onDrop: DragEventHandler<HTMLLabelElement> = (event) => {
      event.preventDefault();
      setIsDragging(false);
      handleFileListChange(event.dataTransfer.files);
    };

    return (
      <label
        className={`${s.wrapper} ${className}`}
        style={style}
        data-dragging={isDraggingDebounced}
        data-disabled={disabled}
        data-error={!!error}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <input
          type="file"
          className={s.nativeInput}
          aria-errormessage={error ? assistiveTextId : undefined}
          aria-invalid={!!error}
          accept={accept}
          multiple={multiple}
          ref={ref}
          name={name}
          disabled={disabled}
          {...props}
          onChange={onChange}
        />

        {label && <span className={s.label}>{label}</span>}

        <div className={s.input}>
          {value && value.length > 0 && (
            <div className={s.files}>
              {value.map((file) => (
                <div className={s.file} key={file.name}>
                  {file.type.includes('image/') && (
                    <img src={URL.createObjectURL(file)} alt={file.name} />
                  )}

                  <div className={s.filename}>
                    <SvgIcon icon={<Paperclip />} size="xs" color="sand-10" />
                    <Text size="text-xs">{file.name}</Text>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className={s.cta}>
            <SvgIcon icon={<FileArrowUp />} color="violet-10" />
            <Text size="text-s" color="sand-12">
              Select or drag & drop {multiple ? 'files' : 'file'}
            </Text>
          </div>
        </div>

        <AssistiveText variant="error" message={error} id={assistiveTextId} />
      </label>
    );
  },
);

FileInput.displayName = 'FileInput';
