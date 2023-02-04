declare module "*.html" {
  const content: string;
  export default content;
}

declare module "*.vue" {
  import Vue from "vue";
  export default Vue;
}

declare const __BASE_URL__: string;

declare module "yup";

declare const Holder;
