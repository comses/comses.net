<template>
  <c-search
    submitLabel="Archive a model"
    submitUrl="/codebases/add/"
    searchLabel="Search"
    :searchUrl="query"
  >
    <div class="card-metadata" slot="searchForm">
      <div class="title">Search</div>
      <div class="card-body">
        <span @keyup.enter="search">
          <c-input
            :required="false"
            label="Keywords"
            type="text"
            v-model="fullTextSearch"
            name="fullTextSearch"
            :errorMsgs="[]"
          >
          </c-input>
        </span>
        <c-datepicker
          v-model="startDate"
          :required="false"
          name="startDate"
          :errorMsgs="[]"
          :clearButton="true"
          label="Published After"
        >
        </c-datepicker>
        <c-datepicker
          v-model="endDate"
          :required="false"
          name="endDate"
          :errorMsgs="[]"
          :clearButton="true"
          label="Published Before"
        >
        </c-datepicker>
        <c-tagger v-model="tags" :required="false" placeholder="Type to add tags" label="Tags">
        </c-tagger>
        <div class="form-group">
          <label for="peerReviewed">Peer Review Status</label>
          <select class="form-control" id="peerReviewed" v-model="selectedPeerReviewStatus">
            <option
              :value="prOpt.value"
              :selected="prOpt.value === selectedPeerReviewStatus"
              v-for="prOpt in peerReviewOptions"
            >
              {{ prOpt.label }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </c-search>
</template>

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";
import Search from "@/components/Search.vue";
import DatePicker from "@/components/forms/datepicker";
import Input from "@/components/forms/input";
import Tagger from "@/components/tagger";
import { CodebaseAPI } from "@/api";

const api = new CodebaseAPI();

@Component({
  components: {
    "c-datepicker": DatePicker,
    "c-input": Input,
    "c-tagger": Tagger,
    "c-search": Search,
  },
})
export default class SearchCodebases extends Vue {
  public fullTextSearch: string = "";

  public startDate: string | null = null;
  public endDate: string | null = null;

  public tags: Array<{ name: string }> = [];
  public peerReviewOptions: Array<{ value: string; label: string }> = [
    { value: "reviewed", label: "Reviewed" },
    { value: "not_reviewed", label: "Not Reviewed" },
    { value: "", label: "Any" },
  ];
  public selectedPeerReviewStatus = "";
  public contributors = [];

  get query() {
    const queryObject = {
      query: this.fullTextSearch,
      published_after: this.startDate,
      published_before: this.endDate,
      tags: this.tags.map(tag => tag.name),
      peer_review_status: this.selectedPeerReviewStatus,
    };
    return api.searchUrl(queryObject);
  }

  public search() {
    window.location.href = this.query;
  }
}
</script>

<style scoped></style>
