import { toRef } from "vue";
import { useField } from "@vorms/core";

export function useFormField(props: any, fieldName: string) {
  /**
   * Wrapper for @vorms/core useField that provides a unique id for the field
   * Also takes care of converting to a ref
   */
  const nameRef = toRef(props, "name");
  const field = useField(nameRef);
  const id = `form-field-${fieldName}`;

  return {
    id,
    ...field,
  };
}
