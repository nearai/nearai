export type ThemeInputVariant = 'default' | 'success' | 'error';
export type ThemeIconSize = 'xxs' | 'xs' | 's' | 'm' | 'l' | 'xl';
export type ThemeGap = 'none' | 'xs' | 's' | 'm' | 'l' | 'xl' | '2xl' | '3xl';

export type ThemeBreakpointProps<T> = T & {
  phone?: T;
  tablet?: T;
};

export type ThemeColor =
  | 'current'
  | ColorAmber
  | ColorBlack
  | ColorCyan
  | ColorGreen
  | ColorRed
  | ColorSand
  | ColorViolet
  | ColorWhite;

export type ThemeFontSize =
  | 'text-xs'
  | 'text-s'
  | 'text-base'
  | 'text-l'
  | 'text-xl'
  | 'text-2xl'
  | 'text-3xl'
  | 'text-hero-m'
  | 'text-hero-l'
  | 'text-hero-xl';

type ColorAmber =
  | 'amber-1'
  | 'amber-2'
  | 'amber-3'
  | 'amber-4'
  | 'amber-5'
  | 'amber-6'
  | 'amber-7'
  | 'amber-8'
  | 'amber-9'
  | 'amber-10'
  | 'amber-11'
  | 'amber-12';

type ColorBlack =
  | 'black'
  | 'black-a1'
  | 'black-a2'
  | 'black-a3'
  | 'black-a4'
  | 'black-a5'
  | 'black-a6'
  | 'black-a7'
  | 'black-a8'
  | 'black-a9'
  | 'black-a10'
  | 'black-a11'
  | 'black-a12';

type ColorCyan =
  | 'cyan-1'
  | 'cyan-2'
  | 'cyan-3'
  | 'cyan-4'
  | 'cyan-5'
  | 'cyan-6'
  | 'cyan-7'
  | 'cyan-8'
  | 'cyan-9'
  | 'cyan-10'
  | 'cyan-11'
  | 'cyan-12';

type ColorGreen =
  | 'green-1'
  | 'green-2'
  | 'green-3'
  | 'green-4'
  | 'green-5'
  | 'green-6'
  | 'green-7'
  | 'green-8'
  | 'green-9'
  | 'green-10'
  | 'green-11'
  | 'green-12'
  | 'green-brand';

type ColorRed =
  | 'red-1'
  | 'red-2'
  | 'red-3'
  | 'red-4'
  | 'red-5'
  | 'red-6'
  | 'red-7'
  | 'red-8'
  | 'red-9'
  | 'red-10'
  | 'red-11'
  | 'red-12';

type ColorSand =
  | 'sand-0'
  | 'sand-1'
  | 'sand-2'
  | 'sand-3'
  | 'sand-4'
  | 'sand-5'
  | 'sand-6'
  | 'sand-7'
  | 'sand-8'
  | 'sand-9'
  | 'sand-10'
  | 'sand-11'
  | 'sand-12';

type ColorViolet =
  | 'violet-1'
  | 'violet-2'
  | 'violet-3'
  | 'violet-4'
  | 'violet-5'
  | 'violet-6'
  | 'violet-7'
  | 'violet-8'
  | 'violet-9'
  | 'violet-10'
  | 'violet-11'
  | 'violet-12'
  | 'violet-brand';

type ColorWhite =
  | 'white'
  | 'white-a1'
  | 'white-a2'
  | 'white-a3'
  | 'white-a4'
  | 'white-a5'
  | 'white-a6'
  | 'white-a7'
  | 'white-a8'
  | 'white-a9'
  | 'white-a10'
  | 'white-a11'
  | 'white-a12';

function breakpointCssValue(
  value: string | undefined,
  propKey: string,
  convertValue: boolean,
) {
  if (convertValue) {
    if (value) return `var(--${propKey}-${value})`;
    return undefined;
  }
  return value;
}

export function breakpointPropToCss<T>(
  props: ThemeBreakpointProps<T>,
  propKey: keyof T extends string ? keyof T : never,
  name: string,
  convertValue = false,
) {
  const variables: Record<string, string | undefined> = {};

  variables[`--${name}`] = breakpointCssValue(
    props[propKey] as string | undefined,
    propKey,
    convertValue,
  );

  variables[`--${name}-tablet`] = breakpointCssValue(
    props.tablet?.[propKey] as string | undefined,
    propKey,
    convertValue,
  );

  variables[`--${name}-phone`] = breakpointCssValue(
    props.phone?.[propKey] as string | undefined,
    propKey,
    convertValue,
  );

  return variables;
}
