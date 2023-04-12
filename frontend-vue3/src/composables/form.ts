import { toRef } from "vue";
import type { WritableComputedRef } from "vue";
import { yupResolver } from "@vorms/resolvers/yup";
import {
  useField as useVField,
  useForm as useVForm,
  type UseFormOptions,
  type UseFormReturn, // eslint-disable-line @typescript-eslint/no-unused-vars
  type UseFormRegisterReturn, // eslint-disable-line @typescript-eslint/no-unused-vars
} from "@vorms/core";

export function useField<Value>(props: any, fieldNameProp: string = "name") {
  /**
   * Wrapper for @vorms/core useField that provides a unique id for the field
   * https://vorms.mini-ghost.dev/api/use-field.html
   *
   * Registers the field in the form context and returns reactive state of the field
   *
   * Only needs to be used in the setup function of a form field component
   *
   * @param {any} props - Form field component props
   * @param {string} [fieldNameProp="name"] - Name of the prop that contains the unique field name
   *   that is used to create the id for the field. This should usually be "name" (default) with a
   *   prop on the field component: `name: string`
   * @returns {UseFormRegisterReturn<Value>} - {@link UseFormRegisterReturn}
   * @returns {string} id - Unique id attribute for the field
   */

  const nameRef = toRef(props, fieldNameProp);
  const field = useVField(nameRef);
  const value = field.value as WritableComputedRef<Value>;
  const id = `form-field-${nameRef.value}`;

  return {
    id,
    ...field,
    value,
  };
}

export type UseFormValidationOptions<Values> = UseFormOptions<Partial<Values>> & { schema?: any };

export function useForm<Values>(options: UseFormValidationOptions<Values>) {
  /**
   * Wrapper for @vorms/core useForm that handles validation with yup
   * https://vorms.mini-ghost.dev/api/use-form.html
   *
   * Creates a form context and returns handler callbacks and reactive state of the whole form
   *
   * @param {UseFormValidationOptions} options - {@link UseFormOptions}
   * @param {any} [options.schema] - yup schema to validate against
   * @returns {UseFormReturn<Values>} - {@link UseFormReturn}
   */

  return useVForm({
    ...options,
    validate: yupResolver(options.schema),
  });
}
