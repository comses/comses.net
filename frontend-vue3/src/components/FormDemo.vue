<template>
  <form @submit="handleSubmit">
    <FormTextInput class="mb-3" name="text" label="Text Input" />
    <FormTextInput class="mb-3" name="email" label="Email" />
    <FormCheckbox class="mb-3" name="terms" label="Terms and Conditions" />
    <FormSelect class="mb-3" name="number" label="Your Number" :options="numberOptions" />
    <FormDatePicker class="mb-3" name="date" label="Date" />
    <FormTagger class="mb-3" name="tags" label="Tags" />
    <button type="submit" class="mb-3 btn btn-primary">Submit</button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { useForm } from "@/composables/form";
import FormTextInput from "@/components/form/FormTextInput.vue";
import FormSelect from "@/components/form/FormSelect.vue";
import FormCheckbox from "@/components/form/FormCheckbox.vue";
import FormDatePicker from "@/components/form/FormDatePicker.vue";
import FormTagger from "@/components/form/FormTagger.vue";
import type { Tags } from "@/composables/api/tags";

interface DemoFields {
  text: string;
  email: string;
  terms: boolean;
  number: number;
  date: Date;
  tags: Tags;
}

const initialValues: Partial<DemoFields> = {
  terms: false,
};

const schema = yup.object({
  text: yup.string().required(),
  email: yup.string().email(),
  terms: yup.boolean().oneOf([true], "You must accept"),
  date: yup.date(),
  number: yup.number().required().oneOf([2, 3], "Must be 2 or 3").label("Number"),
});

const numberOptions = [
  { value: 1, label: "One" },
  { value: 2, label: "Two" },
  { value: 3, label: "Three" },
  { value: 4, label: "Four" },
];

const { handleSubmit, values } = useForm<DemoFields>({
  initialValues,
  schema,
  onSubmit: values => {
    console.log(values);
  },
});
</script>
