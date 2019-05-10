<template>
    <div>
        <a class="text-white" :href="submitUrl">
            <div class="btn btn-primary w-100" tabindex="0">
                {{ submitLabel }}
            </div>
        </a>
        <slot name="searchForm"></slot>
        <a class="text-white" :href="searchUrl">
            <div class="btn btn-primary w-100" tabindex="0">
                {{ searchLabel }}
            </div>
        </a>
    </div>
</template>
<script lang="ts">
    import {Component, Prop} from 'vue-property-decorator';
    import Vue from 'vue';

    // Tabbing is not consistent between browsers but tabbing order works as expected in
    // in Chrome, Firefox and Safari. If tabindex is placed on <a> then tabbing would not
    // work for Firefox or Safari. Pressing enter on search or submit when focused does
    // not work in Safari.
    //
    // See https://www.alexlande.com/articles/cross-browser-tabindex-woes/ for details
    @Component
    export default class Search extends Vue {
        @Prop()
        public submitLabel: string;

        @Prop()
        public submitUrl: string;

        @Prop()
        public searchLabel: string;

        @Prop()
        public searchUrl: string;
    }
</script>

