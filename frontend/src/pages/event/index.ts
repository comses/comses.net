import "@/pages/sentry";
import EditEvent from "@/components/Edit.vue";

function matchUpdateUrl(pathname) {
  let match = pathname.match(/\/events\/([0-9]+)\/edit\//);
  if (match !== null) {
    match = match[1];
  }
  return match;
}

const _id = matchUpdateUrl(document.location.pathname);
new EditEvent({ propsData: { _id } }).$mount("#app");
