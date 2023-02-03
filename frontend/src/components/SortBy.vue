<template>
  <form class="form-inline py-2 mx-1">
    <div class="form-group">
      <label for="ordering"><b class="title">Sort By: </b></label>
      <select v-model="selectedOptionValue" class="mx-3" id="ordering">
        <option
          v-for="sortOption in sortOptions"
          :value="sortOption.value"
          :selected="sortOption.value === selectedOptionValue"
          :key="sortOption.value"
        >
          {{ sortOption.label }}
        </option>
      </select>
    </div>
    <div class="form-check form-check-inline mx-2">
      <input
        v-model="sortByAscDesc"
        class="form-check-input"
        value="desc"
        type="radio"
        name="sort_type"
        id="sort_descending"
      />
      <label class="form-check-label" for="sort_descending">Descending</label>
    </div>
    <div class="form-check form-check-inline mx-2">
      <input
        v-model="sortByAscDesc"
        class="form-check-input"
        value="asc"
        type="radio"
        name="sort_type"
        id="sort_ascending"
        checked
      />
      <label class="form-check-label" for="sort_ascending">Ascending</label>
    </div>
    <button type="button" @click="updateSortBy" class="btn btn-secondary">Sort</button>
  </form>
</template>

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";
import * as queryString from "query-string";
import * as _ from "lodash";

@Component
export default class SortBy extends Vue {
  @Prop()
  public sortOptions: Array<{ label: string; value: string }>;

  public selectedOptionValue: string;

  public sortByAscDesc: string;

  public created() {
    const queryParams = queryString.parse(window.location.search);
    const orderingQueryParam: any = queryParams.ordering || "";
    if (orderingQueryParam === "" || orderingQueryParam.startsWith("-")) {
      this.selectedOptionValue = orderingQueryParam.slice(1);
      this.sortByAscDesc = "desc";
    } else {
      this.selectedOptionValue = _.isArray(orderingQueryParam)
        ? orderingQueryParam.join(",")
        : orderingQueryParam;
      this.sortByAscDesc = "asc";
    }
  }

  public getOrderingParam() {
    if (this.sortByAscDesc === "desc") {
      return "-" + this.selectedOptionValue;
    }
    return this.selectedOptionValue;
  }

  public updateSortBy() {
    const queryParams: any = queryString.parse(window.location.search);
    if (this.getOrderingParam() === "") {
      delete queryParams.ordering;
    } else {
      queryParams.ordering = this.getOrderingParam();
    }
    window.location.search = queryString.stringify(queryParams);
  }
}
</script>

<style scoped></style>
