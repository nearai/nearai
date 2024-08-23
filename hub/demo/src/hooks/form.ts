import { zodResolver } from '@hookform/resolvers/zod';
import {
  type FieldValues,
  type Path,
  type PathValue,
  useForm,
  type UseFormReturn,
} from 'react-hook-form';
import { type z } from 'zod';

export type UseZodFormParams<Schema extends z.Schema<FieldValues>> = Parameters<
  typeof useForm<z.infer<Schema>>
>[0];

export function useZodForm<Schema extends z.ZodObject<FieldValues>>(
  schema: Schema,
  props?: UseZodFormParams<Schema>,
) {
  return useForm<z.infer<Schema>>({
    ...props,
    resolver: zodResolver(schema),
  });
}

export type ZodSubmitHandler<Schema extends z.ZodObject<FieldValues>> =
  Parameters<ReturnType<typeof useZodForm<Schema>>['handleSubmit']>[0];

export function updateFields<Schema extends z.ZodObject<FieldValues>>(
  form: UseFormReturn<z.infer<Schema>>,
  schema: Schema,
  fieldsToUpdate: Partial<z.infer<Schema>>,
) {
  if (fieldsToUpdate && Object.keys(fieldsToUpdate).length > 0) {
    for (const [key, value] of Object.entries(fieldsToUpdate)) {
      if (key in schema.shape && !!value) {
        form.setValue(
          key as Path<z.infer<Schema>>,
          value as PathValue<z.infer<Schema>, Path<z.infer<Schema>>>,
        );
      }
    }
  }
}
