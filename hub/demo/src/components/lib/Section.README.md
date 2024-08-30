# Section

This component is most useful directly inside page components. They expand the entire width of the apply a container to give the content a default max-width and flex stack gap. When multiple `<Section>` components are at the same level, a default border will be applied to help visually separate them.

```tsx
import { Section } from '~/components/lib/Section';

...

<>
  <Section></Section>
  <Section></Section>
</>
```

## Custom Background

```tsx
<Section
  style={{
    background: 'linear-gradient(to right, var(--violet-10), var(--cyan-10))',
    border: 'none',
  }}
>
  // ...
</Section>
```

## Grow

### Screen Height

Sometimes you might need a section to vertically grow to fill up the screen height. You can do that with `grow="screen-height"`. If you want to center your content, you can use a nested `<Flex>` container with `margin: auto`:

```tsx
<Section grow="screen-height" style={{ background: 'var(--cyan-4)' }}>
  <Flex gap="m" stack style={{ margin: 'auto' }}>
    <Text as="h1">My Header</Text>
    <Text>I am centered on the page!</Text>
  </Flex>
</Section>
```

It's important to note that `grow="screen-height"` will only set a minimum height. If the content inside is taller than the screen space, the section will dynamically grow in height to fit the content so that nothing is chopped off.

### Available

For smaller pages that might not have much content, you can use the alternative `grow="available"` variant to only take up any remaining screen height on larger screens:

```tsx
<>
  <Section grow="available" style={{ background: 'var(--cyan-4)' }}>
    <Flex gap="m" stack style={{ margin: 'auto' }}>
      <Text as="h1">My Header</Text>
      <Text>
        I am centered within my section and take up all the remaining vertical
        screen space!
      </Text>
    </Flex>
  </Section>

  <Section>
    <Text as="h1">My Content Below</Text>
    <Text>I am near the bottom of the page!</Text>
  </Section>
</>
```
