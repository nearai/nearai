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
  | 'amber1'
  | 'amber2'
  | 'amber3'
  | 'amber4'
  | 'amber5'
  | 'amber6'
  | 'amber7'
  | 'amber8'
  | 'amber9'
  | 'amber10'
  | 'amber11'
  | 'amber12';

type ColorBlack =
  | 'black'
  | 'blackA1'
  | 'blackA2'
  | 'blackA3'
  | 'blackA4'
  | 'blackA5'
  | 'blackA6'
  | 'blackA7'
  | 'blackA8'
  | 'blackA9'
  | 'blackA10'
  | 'blackA11'
  | 'blackA12';

type ColorCyan =
  | 'cyan1'
  | 'cyan2'
  | 'cyan3'
  | 'cyan4'
  | 'cyan5'
  | 'cyan6'
  | 'cyan7'
  | 'cyan8'
  | 'cyan9'
  | 'cyan10'
  | 'cyan11'
  | 'cyan12';

type ColorGreen =
  | 'green1'
  | 'green2'
  | 'green3'
  | 'green4'
  | 'green5'
  | 'green6'
  | 'green7'
  | 'green8'
  | 'green9'
  | 'green10'
  | 'green11'
  | 'green12'
  | 'green-brand';

type ColorRed =
  | 'red1'
  | 'red2'
  | 'red3'
  | 'red4'
  | 'red5'
  | 'red6'
  | 'red7'
  | 'red8'
  | 'red9'
  | 'red10'
  | 'red11'
  | 'red12';

type ColorSand =
  | 'sand1'
  | 'sand2'
  | 'sand3'
  | 'sand4'
  | 'sand5'
  | 'sand6'
  | 'sand7'
  | 'sand8'
  | 'sand9'
  | 'sand10'
  | 'sand11'
  | 'sand12';

type ColorViolet =
  | 'violet1'
  | 'violet2'
  | 'violet3'
  | 'violet4'
  | 'violet5'
  | 'violet6'
  | 'violet7'
  | 'violet8'
  | 'violet9'
  | 'violet10'
  | 'violet11'
  | 'violet12'
  | 'violet-brand';

type ColorWhite =
  | 'white'
  | 'whiteA1'
  | 'whiteA2'
  | 'whiteA3'
  | 'whiteA4'
  | 'whiteA5'
  | 'whiteA6'
  | 'whiteA7'
  | 'whiteA8'
  | 'whiteA9'
  | 'whiteA10'
  | 'whiteA11'
  | 'whiteA12';

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
