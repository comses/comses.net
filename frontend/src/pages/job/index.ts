import "@/pages/sentry";
import Edit from "@/components/job/Edit.vue";

function matchUpdateUrl(pathname) {
  let match = pathname.match(/\/jobs\/([0-9]+)\/edit\//);
  if (match !== null) {
    match = match[1];
  }
  return match;
}

const _id = matchUpdateUrl(window.location.pathname);

const job = new Edit({ propsData: { _id } }).$mount("#app");
