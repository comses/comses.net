<template>
  <div>
    <h5>Latest Events</h5>
    <div class="alert alert-danger" v-for="error in errors" :key="error">
      <h5 class="alert-heading fw-bold">Error fetching event log</h5>
      {{ error }}
    </div>
    <div v-for="event in events" :key="event.date_created">
      <div class="card mb-2">
        <div class="card-body">
          <h5 class="card-title">{{ event.date_created }}</h5>
          <p class="card-text">
            <span class="badge bg-primary">
              {{ event.action }}
            </span>
            {{ event.message }} (<em>by: </em
            ><a :href="event.author.absolute_url"> {{ event.author.name }} </a>)
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ReviewEvent } from "@/types";

export interface ReviewEventLogProps {
  events?: ReviewEvent[];
  errors?: string[];
}

const props = defineProps<ReviewEventLogProps>();
</script>
