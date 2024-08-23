# Slider

Implemented via Radix primitives: https://www.radix-ui.com/docs/primitives/components/slider

```tsx
import { Slider } from '~/components/lib/Slider';

...

<Slider
  label="My Slider"
  name="mySlider"
  max={2}
  min={0}
  step={0.01}
  value={mySlider}
  onChange={setMySlider}
/>
```

## React Hook Form

```tsx
<Controller
  control={form.control}
  name="mySlider"
  render={({ field, fieldState }) => (
    <Slider
      label="My Slider"
      name="mySlider"
      max={2}
      min={0}
      step={0.01}
      {...field}
    />
  )}
/>
```
