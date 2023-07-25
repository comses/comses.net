import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ImageGallery from "@/components/ImageGallery.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("image-gallery", ["images", "title"]);

createApp(ImageGallery, props).mount("#image-gallery");
