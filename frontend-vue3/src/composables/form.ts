import { toRef } from "vue";
import { object } from "yup";
import type { WritableComputedRef } from "vue";
import { useField } from "@vorms/core";

export function useFormField(props: any, fieldName: string) {
  /**
   * Wrapper for @vorms/core useField that provides a unique id for the field
   * Also takes care of converting to a ref
   */

  const nameRef = toRef(props, "name");
  const field = useField(nameRef);
  // const value: WritableComputedRef<any> = field.value;
  console.log(nameRef.value, field.value.value);
  const id = `form-field-${nameRef.value}`;

  return {
    id,
    ...field,
    // value
  };
}

export function useFormBuilder(fields: FormBuilderFields) {
  /**
   * extract field props, initial values and schema from field definitions
   */

  function extractProperties(fields: FormBuilderFields, property: string) {
    // FIXME: lazybones any
    return Object.keys(fields).reduce((acc, key) => {
      (acc as any)[key] = (fields as any)[key][property];
      return acc;
    }, {} as any);
  }

  const schema = object().shape(extractProperties(fields, "schema"));
  const initialValues = extractProperties(fields, "initialValue");
  const props = extractProperties(fields, "props");

  return {
    schema,
    initialValues,
    props,
  }
}

export interface FormBuilderFields {
  [key: string]: {
    props: Record<string, any>;
    initialValue?: any;
    schema?: any;
  }
}
