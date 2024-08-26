# Combobox

Built with the Downshift `useCombobox()` hook: https://www.downshift-js.com/use-combobox

```tsx
import { Combobox } from '~/components/lib/Combobox';

...

<Combobox
  label="My Combobox"
  name="myCombobox"
  items={[
    {
      value: 'Item A',
    },
    {
      value: 'Item B',
    },
    {
      value: 'Item C',
    },
  ]}
  value={myCombobox}
  onChange={setMyCombobox}
/>
```

## React Hook Form

```tsx
import { Controller } from 'react-hook-form';

<Controller
  control={form.control}
  name="myCombobox"
  rules={{
    required: 'Please select an option',
  }}
  render={({ field, fieldState }) => (
    <Combobox
      label="My Combobox"
      items={items}
      error={fieldState.error?.message}
      {...field}
    />
  )}
/>;
```
