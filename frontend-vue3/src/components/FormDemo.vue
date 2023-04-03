<template>
  <FormContext :schema="schema" :initial-values="initialValues" @submit="onSubmit">
    <FormTextInput class="mb-3" name="text" label="Text" help="Enter some text" required />
    <FormTextInput class="mb-3" name="email" label="Email" help="Your primary email" />
    <FormCheckbox class="mb-3" name="terms" label="Accept terms and conditions" />
    <FormSelect
      class="mb-3"
      name="number"
      label="Your Number"
      help="Choose one"
      :options="numOptions"
    ></FormSelect>
    <FormDatePicker class="mb-3" name="date" label="Date" help="Choose a date" />
    <FormTagger class="mb-3" name="tags" label="Tags" help="Press enter to select" />
    <button type="submit" class="mb-3 btn btn-primary">Submit</button>
  </FormContext>
</template>

<script setup lang="ts">
import * as yup from "yup";
import FormContext from "@/components/form/FormContext.vue";
import FormTextInput from "@/components/form/FormTextInput.vue";
import FormSelect from "@/components/form/FormSelect.vue";
import FormCheckbox from "@/components/form/FormCheckbox.vue";
import FormDatePicker from "@/components/form/FormDatePicker.vue";
import FormTagger from "@/components/form/FormTagger.vue";
import type { SelectOptions } from "@/components/form/FormSelect.vue";

const schema = yup.object().shape({
  text: yup.string().required().label("Text o"),
  email: yup.string().email().label("Test Email"),
  terms: yup.boolean().oneOf([true], "You must accept"),
  number: yup.number().required().oneOf([2,3], "Must be 2 or 3").label("Number"),
  date: yup.date().required().label("Date"),
});

const numOptions: SelectOptions = [
  { value: 1, label: "One" },
  { value: 2, label: "Two" },
  { value: 3, label: "Three" },
  { value: 4, label: "Four" },
];

interface FieldValues {
  text: string;
  email: string;
  terms: boolean;
  number?: number;
  date?: Date;
}

const initialValues: FieldValues = {
  text: "",
  email: "",
  terms: false,
};

async function onSubmit(values: FieldValues) {
  console.log(values);
}
</script>
