<template>
  <FormContext :schema="schema" :initial-values="initialValues" @submit="onSubmit">
    <FormTextInput class="mb-3" v-bind="props.text" />
    <FormTextInput class="mb-3" v-bind="props.email" />
    <FormCheckbox class="mb-3" v-bind="props.terms" />
    <FormSelect class="mb-3" v-bind="props.number" />
    <FormDatePicker class="mb-3" v-bind="props.date" />
    <FormTagger class="mb-3" v-bind="props.tags" />
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
import { useFormBuilder } from "@/composables/form";
import type { Values } from "@/components/form/FormContext.vue";

const { schema, initialValues, props } = useFormBuilder({
  text: {
    props: {
      name: "text",
      label: "Text",
      help: "Enter some text",
      required: true,
    },
    initialValue: "",
    schema: yup.string().required().label("Text"),
  },
  email: {
    props: {
      name: "email",
      label: "Email",
      help: "Your primary email",
    },
    initialValue: "",
    schema: yup.string().email().label("Test Email"),
  },
  terms: {
    props: {
      name: "terms",
      label: "Accept terms and conditions",
    },
    initialValue: false,
    schema: yup.boolean().oneOf([true], "You must accept"),
  },
  number: {
    props: {
      name: "number",
      label: "Your Number",
      help: "Choose one",
      options: [
        { value: 1, label: "One" },
        { value: 2, label: "Two" },
        { value: 3, label: "Three" },
        { value: 4, label: "Four" },
      ],
    },
    schema: yup.number().required().oneOf([2, 3], "Must be 2 or 3").label("Number"),
  },
  date: {
    props: {
      name: "date",
      label: "Date",
      help: "Choose a date",
    },
    initialValue: new Date(),
    schema: yup.date().required().label("Date"),
  },
  tags: {
    props: {
      name: "tags",
      label: "Tags",
      help: "Press enter to select",
    },
    initialValue: [],
  },
});

async function onSubmit(values: Values) {
  console.log(values);
}
</script>
