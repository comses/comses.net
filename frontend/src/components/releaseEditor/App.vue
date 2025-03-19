<template>
  <div>
    <div class="row">
      <div class="col">
        <h1>
          <span
            v-if="!isLive"
            title="This release is currently private and unpublished."
            class="badge bg-gray"
          >
            <small><i class="fas fa-lock"></i> Private</small>
          </span>
          {{ store.release.codebase.title }}
          <span class="badge bg-gray pt-1 px-2">
            <small>v{{ store.release.versionNumber }}</small>
          </span>
        </h1>
      </div>
    </div>
    <div class="row mb-2">
      <div class="col d-flex justify-content-between">
        <span>
          <a :href="store.release.absoluteUrl">View live</a> |
          <span class="text-muted me-2">
            Review Status:
            <span class="fw-bold">{{ reviewStatus }}</span>
          </span>
          <ReviewModal button-class="btn btn-sm btn-outline-danger py-0 mb-1" />
        </span>
        <a href="//forum.comses.net/t/archiving-your-model-1-getting-started/7377">
          <i class="fas fa-question-circle"></i> Need help? Check out our archiving tutorial
        </a>
      </div>
    </div>
    <div class="row">
      <div class="col d-flex justify-content-between">
        <span>
          <CommonMetadataModal button-class="btn btn-primary me-2" :identifier="identifier" />
          <CommonImagesModal
            button-class="btn btn-primary me-2"
            :identifier="identifier"
            :files="store.files.media"
          />
        </span>
        <PublishModal :show="showPublishModal" button-class="btn btn-danger" />
      </div>
    </div>
    <hr />
    <div class="row mt-3">
      <div class="col-md-3">
        <ProgressSidebar
          v-if="isImported"
          show-files
          files-route="/package"
          files-title="Review archive"
          metadata-title="Review metadata"
          contributors-title="Review contributors"
        />
        <ProgressSidebar
          v-else
          :show-files="canEditOriginals"
          files-route="/upload"
          files-title="Upload files"
          metadata-title="Add metadata"
          contributors-title="Add contributors"
        />
      </div>
      <div class="col-md-9">
        <div>
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component"></component>
            </keep-alive>
          </router-view>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import ProgressSidebar from "@/components/releaseEditor/ProgressSidebar.vue";
import CommonImagesModal from "@/components/releaseEditor/CommonImagesModal.vue";
import CommonMetadataModal from "@/components/releaseEditor/CommonMetadataModal.vue";
import ReviewModal from "@/components/releaseEditor/ReviewModal.vue";
import PublishModal from "@/components/releaseEditor/PublishModal.vue";

const props = defineProps<{
  identifier: string;
  versionNumber: string;
  reviewStatus: string;
  isLive: boolean;
  canEditOriginals: boolean;
  isImported: boolean;
  showPublishModal: boolean;
}>();

const store = useReleaseEditorStore();

onMounted(async () => {
  await store.initialize(props.identifier, props.versionNumber);
});
</script>
