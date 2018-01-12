declare module "*.html" {
    const content: string;
    export default content;
}

declare const __BASE_URL__: string;
declare const __BASIC_AUTH_USERNAME__: string;

declare module 'yup';