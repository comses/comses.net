<template>
  <ListSidebar
    :create-label="userId ? 'My profile' : 'Become a member'"
    :create-url="userId ? `/users/${userId}` : '/accounts/signup/'"
    search-label="Apply Filters"
    :search-url="query"
  >
    <template #form>
      <form @submit="handleSubmit">
        <TaggerField name="tags" label="Keywords" type="Profile" />
        <!-- consider adding full member/peer reviewer filter -->
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useProfileAPI } from "@/composables/api";

export interface ProfileListSidebarProps {
  userId?: number;
}

const props = defineProps<ProfileListSidebarProps>();

const schema = yup.object({
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
});
type SearchFields = yup.InferType<typeof schema>;

const { handleSubmit, values } = useForm<SearchFields>({
  schema,
  initialValues: { tags: [] },
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useProfileAPI();

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const query = url.get("query") ?? "";
  return searchUrl({
    query,
    tags: values.tags?.map(tag => tag.name),
  });
});
</script>
