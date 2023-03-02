<template>
  <form>
    <c-input
      v-model="title"
      name="title"
      :errorMsgs="errors.title"
      :required="config.title"
      label="Title"
      help="A short  title describing the event"
    >
    </c-input>
    <c-input
      v-model="location"
      name="location"
      :errorMsgs="errors.location"
      :required="config.location"
      label="Location"
      help="The city and country where the event takes place"
    >
    </c-input>
    <div class="row">
      <div class="col-6">
        <c-datepicker
          v-model="start_date"
          name="start_date"
          :errorMsgs="errors.start_date"
          :required="config.start_date"
          label="Start Date"
          help="The date the event begins"
        >
        </c-datepicker>
      </div>
      <div class="col-6">
        <c-datepicker
          v-model="end_date"
          name="end_date"
          :errorMsgs="errors.end_date"
          :clearButton="true"
          :openDate="endDateOpenDate"
          :required="config.end_date"
          label="End Date"
          help="The date the event ends"
        >
        </c-datepicker>
      </div>
    </div>
    <div class="row">
      <div class="col-6 d-inline">
        <c-datepicker
          v-model="early_registration_deadline"
          name="early_registration_deadline"
          :errorMsgs="errors.early_registration_deadline"
          :clearButton="true"
          :required="config.early_registration_deadline"
          label="Early Registration Deadline"
          help="The last day for early registration of the event (inclusive)"
        >
        </c-datepicker>
      </div>
      <div class="col-6 d-inline">
        <c-datepicker
          v-model="registration_deadline"
          name="registration_deadline"
          :errorMsgs="errors.registration_deadline"
          :clearButton="true"
          :required="config.registration_deadline"
          label="Registration Deadline"
          help="The last day to register for the event (inclusive)"
        >
        </c-datepicker>
      </div>
    </div>
    <div class="row">
      <div class="col-12 d-inline">
        <c-datepicker
          v-model="submission_deadline"
          name="submission_deadline"
          :errorMsgs="errors.submission_deadline"
          :clearButton="true"
        >
          <label class="form-control-label" slot="label">Submission Deadline</label>
          <small class="form-text text-muted" slot="help"
            >The last day to make a submission for the event (inclusive)
          </small>
        </c-datepicker>
      </div>
    </div>
    <c-markdown
      v-model="description"
      :errorMsgs="errors.description"
      :required="config.description"
      help="Detailed information about the event"
      name="description"
      label="Description"
    ></c-markdown>
    <c-textarea
      v-model="summary"
      name="summary"
      :errorMsgs="errors.summary"
      :required="config.summary"
      label="Summary"
      help="A short summary of the event for display in search results. This field can be created from the description by pressing the summarize button."
    >
    </c-textarea>
    <button
      class="mt-n4 btn btn-secondary btn-sm"
      type="button"
      @click="createSummaryFromDescription"
    >
      Summarize from Description
    </button>
    <c-input
      v-model="external_url"
      name="external_url"
      :errorMsgs="errors.external_url"
      :required="config.external_url"
      label="Link to event website"
      help="Link to a more detailed website for this event"
    >
    </c-input>
    <c-tagger v-model="tags" name="tags" :errorMsgs="errors.tags" label="Tags" :required="false">
    </c-tagger>
    <small class="form-text text-muted"
      >A list of tags to associate with an event. Tags help people search for events.
    </small>
    <c-message-display :messages="statusMessages" @clear="statusMessages = []"></c-message-display>
    <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdateIfValid">
      Submit
    </button>
  </form>
</template>

<script lang="ts">
import { EventAPI } from "@/api";
import Markdown from "@/components/forms/markdown";
import TextArea from "@/components/forms/textarea";
import Tagger from "@/components/tagger";
import Input from "@/components/forms/input";
import Datepicker from "@/components/forms/datepicker";
import MessageDisplay from "@/components/messages";
import * as _ from "lodash";
import { Component, Prop } from "vue-property-decorator";
import * as yup from "yup";
import { createFormValidator } from "@/pages/form";
import { HandlerWithRedirect } from "@/api/handler";

const api = new EventAPI();

function dateAfterConstraint(before_name: string, after_name: string) {
  return (before_date, schema) => {
    if (_.isNil(before_date) || _.isNaN(before_date.getDate())) {
      return schema;
    } else {
      return schema.min(before_date, `${_.capitalize(after_name)} must be after ${before_name}`);
    }
  };
}

export const schema = yup.object().shape({
  description: yup.string().required(),
  summary: yup.string().required(),
  title: yup.string().required(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  location: yup.string().required(),
  early_registration_deadline: yup.date().nullable().label("early registration deadline"),
  registration_deadline: yup
    .date()
    .nullable()
    .label("registration deadline")
    .when(
      "early_registration_deadline",
      dateAfterConstraint("early registration deadline", "registration deadline")
    ),
  submission_deadline: yup.date().nullable().label("submission deadline"),
  start_date: yup.date().required().label("start date"),
  end_date: yup
    .date()
    .nullable()
    .when("start_date", dateAfterConstraint("start date", "end date"))
    .when("submission_deadline", dateAfterConstraint("submission_deadline", "end_date"))
    .when("registration_deadline", dateAfterConstraint("registration_deadline", "end_date"))
    .when(
      "early_registration_deadline",
      dateAfterConstraint("early_registration_deadline", "end_date")
    ),
  external_url: yup.string().url().nullable(),
});

@Component({
  components: {
    "c-markdown": Markdown,
    "c-textarea": TextArea,
    "c-message-display": MessageDisplay,
    "c-datepicker": Datepicker,
    "c-tagger": Tagger,
    "c-input": Input,
  },
} as any)
class EditEvent extends createFormValidator(schema) {
  // determine whether you are creating or updating based on wat route you are on
  // update -> grab the appropriate state from the store
  // create -> use the default store state

  @Prop()
  public _id: number | null;

  get endDateOpenDate() {
    return this.state.end_date ? new Date(this.state.end_date) : new Date(this.state.start_date);
  }

  public detailPageUrl(state) {
    this.state.id = state.id;
    return api.detailUrl(this.state.id);
  }

  public initializeForm() {
    if (this._id !== null) {
      return this.retrieve(this._id);
    }
  }

  public created() {
    this.initializeForm();
  }

  public createSummaryFromDescription() {
    (this as any).state.summary = _.truncate(this.state.description, {
      length: 200,
      omission: "[...]",
    });
  }

  public async createOrUpdateIfValid() {
    try {
      await this.validate();
      return this.createOrUpdate();
    } catch (e) {
      if (!(e instanceof yup.ValidationError)) {
        throw e;
      }
    }
  }

  public createOrUpdate() {
    if (_.isNil(this.state.id)) {
      return api.create(new HandlerWithRedirect(this));
    } else {
      return api.update(this.state.id, new HandlerWithRedirect(this));
    }
  }

  public retrieve(id: number) {
    return api.retrieve(id).then(r => (this.state = r.data));
  }
}

export default EditEvent;
</script>
