declare function require(name: string): any;

declare module "*.html" {
    const content: string;
    export default content;
}

declare const process: {
    env: {
        NODE_ENV: string
    }
};

declare const __BASE_URL__: string;
declare const __BASIC_AUTH_USERNAME__: string;