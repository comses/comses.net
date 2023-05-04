<template>
  <form @submit="handleSubmit">
    <TextField class="mb-3" name="text" label="Text Input" />
    <TextField class="mb-3" name="email" label="Email" />
    <CheckboxField class="mb-3" name="terms" label="Terms and Conditions" />
    <SelectField class="mb-3" name="number" label="Your Number" :options="numberOptions" />
    <DatepickerField class="mb-3" name="date" label="Date" />
    <TaggerField class="mb-3" name="tags" label="Tags" />
    <button type="submit" class="mb-3 btn btn-primary">Submit</button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { useForm } from "@/composables/form";
import TextField from "@/components/form/TextField.vue";
import SelectField from "@/components/form/SelectField.vue";
import CheckboxField from "@/components/form/CheckboxField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";

const numberOptions = [
  { value: 1, label: "One" },
  { value: 2, label: "Two" },
  { value: 3, label: "Three" },
  { value: 4, label: "Four" },
];

const schema = yup.object({
  text: yup.string().required(),
  email: yup.string().email(),
  terms: yup.boolean().oneOf([true], "You must accept"),
  date: yup.date(),
  number: yup.number().required().oneOf([2, 3], "Must be 2 or 3").label("Number"),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
});
type DemoFields = yup.InferType<typeof schema>;

const { handleSubmit } = useForm<DemoFields>({
  initialValues: { terms: false },
  schema,
  onSubmit: values => {
    console.log(values);
  },
});
</script>
