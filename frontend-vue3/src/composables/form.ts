import { toRef } from "vue";
import { yupResolver } from "@vorms/resolvers/yup";
import { useField as useVField, useForm as useVForm, type UseFormOptions } from "@vorms/core";

export function useField(props: any, fieldName: string) {
  /**
   * Wrapper for @vorms/core useField that provides a unique id for the field
   * Also takes care of converting to a ref
   */

  const nameRef = toRef(props, "name");
  const field = useVField(nameRef);
  console.log(nameRef.value, field.value.value);
  const id = `form-field-${nameRef.value}`;

  return {
    id,
    ...field,
  };
}

export function useForm<T>(options: UseFormOptions<Partial<T>> & { schema?: any }) {
  /**
   * Wrapper for @vorms/core useForm that handles validation with yup
   */

  return useVForm({
    ...options,
    validate: yupResolver(options.schema),
  });
}
