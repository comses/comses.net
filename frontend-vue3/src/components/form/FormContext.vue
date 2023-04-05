<template>
  <form @submit="handleSubmit" @reset="handleReset">
    <slot name="default"></slot>
  </form>
</template>

<script setup lang="ts">
import { useForm } from "@vorms/core";
import { yupResolver } from "@vorms/resolvers/yup";

export type Values = Record<string, any>;

export interface FormProps {
  initialValues: Values;
  schema?: any;
}

interface FormEvent {
  (event: "submit", values: Values): void;
}

const props = defineProps<FormProps>();
const emit = defineEmits<FormEvent>();

const { handleSubmit, handleReset } = useForm({
  initialValues: props.initialValues,
  validate: yupResolver(props.schema),
  onSubmit(values) {
    emit("submit", values);
  },
});
console.log(props.initialValues);
</script>
