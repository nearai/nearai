# FileInput

This component uses a native `<input type="file" />` tag underneath the hood. The [accept](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/accept) and [multiple](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/multiple) props are passed through to the input tag and behave as they would natively. We've included client side validation to make sure the `accept` and `multiple` props are respected for both selected and dropped files.

Additionally, you can pass a value for `maxFileSizeBytes` to limit the max size of each file. The default is unlimited (undefined).

```tsx
import { FileInput } from '~/components/lib/FileInput';

...

const [error, setError] = useState("");
const [disabled, setDisabled] = useState(false);

...

<FileInput
  label="Artwork"
  name="artwork"
  accept="image/*"
  error={error}
  disabled={disabled}
  maxFileSizeBytes={1_000_000}
  multiple
  onChange={(files) => console.log(files)}
/>
```

## React Hook Form

```tsx
import { Controller } from 'react-hook-form';

<Controller
  control={form.control}
  name="artwork"
  rules={{
    required: 'Please select an image',
  }}
  render={({ field, fieldState }) => (
    <FileInput
      label="Event Artwork"
      accept="image/*"
      error={fieldState.error?.message}
      {...field}
    />
  )}
/>;
```
