declare function require(name: string): any;

declare module "*.html" {
    const content: string;
    export default content;
}