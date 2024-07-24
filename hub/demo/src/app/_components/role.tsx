"use client";

import { CaretSortIcon, CheckIcon } from "@radix-ui/react-icons";
import {
  type FieldPath,
  type FieldValues,
  type UseControllerProps,
} from "react-hook-form";

import { Button } from "~/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "~/components/ui/command";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "~/components/ui/popover";
import { ScrollArea } from "~/components/ui/scroll-area";

import { cn } from "~/lib/utils";

export interface choice {
  label: string;
  value: string;
}

export function DropDownForm<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>(
  props: UseControllerProps<TFieldValues, TName> & {
    choices: choice[];
    title: string;
  },
) {
  return (
    <FormField
      {...props}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{props.title ?? field.name}</FormLabel>
          <Popover>
            <PopoverTrigger asChild>
              <FormControl>
                <Button
                  variant="outline"
                  role="combobox"
                  className={cn(
                    "w-[200px] justify-between truncate",
                    !field.value && "text-muted-foreground",
                  )}
                >
                  {field.value
                    ? props.choices
                        .find((choice) => choice.value === field.value)
                        ?.label.split("/")
                        .pop()
                    : "Select model"}
                  <CaretSortIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </FormControl>
            </PopoverTrigger>
            <PopoverContent className="w-[300px] p-0">
              <Command>
                <CommandInput
                  placeholder="Search framework..."
                  className="h-9"
                />
                <CommandEmpty>Not found.</CommandEmpty>
                <CommandGroup>
                  <ScrollArea className="h-[400px]">
                    {props.choices.map((choice) => (
                      <CommandItem
                        value={choice.label}
                        key={choice.value}
                        onSelect={() => {
                          field.onChange(choice.value);
                        }}
                      >
                        <div className="inline-flex items-center justify-between">
                          <CheckIcon
                            className={cn(
                              "ml-auto mr-2 min-h-4 min-w-4",
                              choice.value === field.value
                                ? "opacity-100"
                                : "opacity-0",
                            )}
                          />
                          <span className="break-words">{choice.label}</span>
                        </div>
                      </CommandItem>
                    ))}
                  </ScrollArea>
                </CommandGroup>
              </Command>
            </PopoverContent>
          </Popover>
          <FormDescription>Role used for the message.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
