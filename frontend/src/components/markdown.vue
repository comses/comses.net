<template>
    <div class="editor">
        <div class="container-fluid p-0">
            <div class="row p-0 row-eq-height">
                <div class="p-1 col-6">
                    <textarea v-bind:value="value" v-on:input="updateValue($event.target.value)"
                              debounce="300">
                    </textarea>
                </div>
                <div class="p-1 col-6">
                    <div v-html="markdown" class="preview"></div>
                </div>
            </div>
        </div>
    </div>
</template>
<style scoped>
textarea {
  border: none;
  border-right: 1px solid #ccc;
  resize: none;
  outline: none;
  background-color: #f6f6f6;
  font-size: 14px;
  font-family: 'Monaco', courier, monospace;
  padding: 20px;
  height: 100%;
  width: 100%;
  overflow: auto;
}

code {
  color: #f66;
}
</style>
<script lang="ts">
    import * as Vue from 'vue'
    import {Component, Prop} from 'vue-property-decorator'
    import * as marked from 'marked'

    @Component
    class MarkDown extends Vue {
        @Prop
        value: string;

        get markdown() {
            return marked.parse(this.value, {sanitize: true})
        }

        updateValue(value: string) {
            this.$emit('input', value);
        }
    }

    export default MarkDown;
</script>
