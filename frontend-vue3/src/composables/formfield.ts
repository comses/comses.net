import { toRef } from "vue";
import type { WritableComputedRef } from "vue";
import { useField } from "@vorms/core";

export function useFormField(props: any, fieldName: string) {
  /**
   * Wrapper for @vorms/core useField that provides a unique id for the field
   * Also takes care of converting to a ref
   */
  const nameRef = toRef(props, "name");
  const field = useField(nameRef);
  const { value }: { value: WritableComputedRef<any> } = field;
  const id = `form-field-${fieldName}`;

  return {
    id,
    ...field,
    value
  };
}

// TODO: generic field props, add placeholder?
export interface FormFieldProps {

}
