# Checkbox

```tsx
import { Checkbox } from '~/components/lib/Checkbox';
import { Flex } from '~/components/lib/Flex';

...

<Flex as="label" align="center" gap="s">
  <Checkbox name="myCheckbox" />
  My Checkbox
</Flex>
```

## Checkbox Group

```tsx
import { Checkbox, CheckboxGroup } from '~/components/lib/Checkbox';
import { Flex } from '~/components/lib/Flex';

...

<CheckboxGroup aria-label="My Checkbox Group">
  <Flex as="label" align="center" gap="s">
    <Checkbox name="myCheckbox1" value="1" />
    My Checkbox 1
  </Flex>

  <Flex as="label" align="center" gap="s">
    <Checkbox name="myCheckbox2" value="2" />
    My Checkbox 2
  </Flex>
</CheckboxGroup>
```

## Radio Group

To switch from checkboxes to radios, simply apply `type="radio"` to each `<Checkbox />` component (and make sure they have matching `name` attributes):

```tsx
import { Checkbox, CheckboxGroup } from '~/components/lib/Checkbox';
import { Flex } from '~/components/lib/Flex';

<CheckboxGroup aria-label="My Radio Group">
  <Flex as="label" align="center" gap="s">
    <Checkbox type="radio" name="myRadio" value="1" />
    My Radio 1
  </Flex>

  <Flex as="label" align="center" gap="s">
    <Checkbox type="radio" name="myRadio" value="2" />
    My Radio 2
  </Flex>
</CheckboxGroup>;
```
