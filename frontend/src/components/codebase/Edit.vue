<template>
  <div>
    <c-input
      v-model="title"
      name="title"
      :errorMsgs="errors.title"
      :required="config.title"
      label="Title (required)"
      help="A short title describing this computational model, limited to 300 characters."
    ></c-input>
    <c-textarea
      v-model="description"
      :errorMsgs="errors.description"
      :required="config.description"
      help="A summary description of your model similar to an abstract. There is no limit on length but it should be kept as succinct as possible. "
      name="description"
      ref="descriptionField"
      rows="3"
      label="Description (required)"
    ></c-textarea>
    <c-textarea
      v-model="replication_text"
      :errorMsgs="errors.replication_text"
      name="replication_text"
      label="Replication of an existing model? (optional)"
      help="Is this model a replication of a previously published computational model? Please enter a DOI or other permanent identifier to the model, or citation text. Separate multiple entries with newlines."
      rows="3"
      :required="config.replication_text"
    ></c-textarea>
    <c-textarea
      v-model="associated_publication_text"
      :errorMsgs="errors.associated_publication_text"
      name="associated_publication_text"
      label="Associated Publications (optional)"
      help="Is this model associated with any publications? Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      rows="3"
      :required="config.associated_publication_text"
    ></c-textarea>
    <c-textarea
      v-model="references_text"
      :errorMsgs="errors.references_text"
      name="references_text"
      label="References (optional)"
      help="Other related publications. Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      rows="3"
      :required="config.references_text"
    ></c-textarea>
    <c-tagger
      v-model="tags"
      name="tags"
      :errorMsgs="errors.tags"
      :required="config.tags"
      help="Add tags to categorize your model and make it more discoverable. Press enter after entering each tag."
      label="Tags (optional)"
    ></c-tagger>
    <c-input
      v-model="repository_url"
      :errorMsgs="errors.repository_url"
      name="repository_url"
      label="Version Control Repository URL (optional)"
      help="Is this model being developed on GitHub, BitBucket, GitLab, or other Git-based version control repository? Enter its root repository URL (e.g., https://github.com/comses/water-markets-model) for future CoMSES and Git integration."
      :required="config.repository_url"
    ></c-input>
    <c-message-display :messages="statusMessages" @clear="statusMessages = []"></c-message-display>
    <button class="btn btn-primary" type="button" @click="save()">Next</button>
  </div>
</template>

<script lang="ts">
import { Component, Prop } from 'vue-property-decorator';
import { CodebaseAPI, CodebaseReleaseAPI } from '@/api';
import Checkbox from '@/components/forms/checkbox';
import Input from '@/components/forms/input';
import Markdown from '@/components/forms/markdown';
import MessageDisplay from '@/components/messages';
import Tagger from '@/components/tagger';
import TextArea from '@/components/forms/textarea';
import { createFormValidator } from '@/pages/form';
import * as yup from 'yup';
import * as _ from 'lodash';
import {
  HandlerWithRedirect,
  HandlerShowSuccessMessage,
  DismissOnSuccessHandler,
} from '@/api/handler';
import { Upload } from '@/components/upload';

export const schema = yup.object().shape({
  title: yup.string().required(),
  description: yup.string().required(),
  latest_version_number: yup.string(),
  replication_text: yup.string(),
  associated_publication_text: yup.string(),
  references_text: yup.string(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  repository_url: yup.string().url(),
});

const api = new CodebaseAPI();
const releaseApi = new CodebaseReleaseAPI();

@Component({
  components: {
    'c-checkbox': Checkbox,
    'c-input': Input,
    'c-markdown': Markdown,
    'c-message-display': MessageDisplay,
    'c-tagger': Tagger,
    'c-textarea': TextArea,
    'c-upload': Upload,
  },
} as any)
export default class CodebaseEditForm extends createFormValidator(schema) {
  @Prop({ default: null })
  public _identifier: string;

  @Prop({ default: null })
  public redirect: string | null;

  public detailPageUrl(state) {
    this.state.identifier = state.identifier;
    const version_number = this.state.latest_version_number || '1.0.0';
    if (_.isNull(this._identifier)) {
      return releaseApi.editUrl({
        identifier: this.state.identifier,
        version_number,
      });
    } else {
      return api.detailUrl(this.state.identifier);
    }
  }

  public async initializeForm() {
    if (this._identifier) {
      const response = await api.retrieve(this._identifier);
      console.log("response: ", response);
      this.state = response.data;
    }
  }

  public refresh() {
    // FIXME: this is a pile of dirty hacks on hacks to properly display the CodeMirror content when it's initially hidden in a modal.
    // ask the description markdown component to refresh itself.
    // (this.$refs.descriptionField as any).refresh();
  }

  public created() {
    this.initializeForm();
  }

  public async createOrUpdate() {
    this.$emit('create-or-update');
    let handler;
    if (_.isNull(this.redirect)) {
      handler = new HandlerWithRedirect(this);
    } else {
      handler = new DismissOnSuccessHandler(this, this.redirect);
      // FIXME: temporary modal bug workaround
      document.getElementById("closeEditCodebaseModal").click();
    }
    if (_.isNil(this.state.identifier)) {
      return api.create(handler);
    } else {
      return api.update(this.state.identifier, handler);
    }
  }

  public async save() {
    try {
      await this.validate();
      return this.createOrUpdate();
    } catch (e) {
      console.log(e);
      if (!(e instanceof yup.ValidationError)) {
        throw e;
      }
    }
  }
}
</script>
