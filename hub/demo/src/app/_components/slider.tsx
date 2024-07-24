"use client";

import {
  type FieldPath,
  type FieldValues,
  type UseControllerProps,
} from "react-hook-form";

import {
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Slider } from "~/components/ui/slider";

export function SliderFormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>(
  props: UseControllerProps<TFieldValues, TName> & {
    description: string;
    defaultValue: number;
    max: number;
    min: number;
    step: number;
  },
) {
  return (
    <FormField
      {...props}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>
            {field.name} - {field.value}
          </FormLabel>
          <Slider
            defaultValue={[props.defaultValue]}
            min={props.min}
            max={props.max}
            step={props.step}
            onValueChange={(v) => {
              field.onChange(v[0]);
            }}
          />
          <FormDescription>{props.description}</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
