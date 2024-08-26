# Input Textarea

```tsx
import { InputTextarea } from '~/components/lib/InputTextarea';

...

<InputTextarea label="My Label" placeholder="My Placeholder" name="myInput" />
```

## Variants & Messages

```tsx
<InputTextarea error="This input is invalid for X reason" name="myInput" />
<InputTextarea success="This input succeeded" name="myInput" />
<InputTextarea assistive="This is generic helper text to give the input more context" name="myInput" />
```
