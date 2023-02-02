import "@/pages/sentry";
import EditCodebase from "@/components/codebase/Edit.vue";

function extractUrlParams(pathname: string) {
  const match = pathname.match(/\/codebases\/([\w-]+)\/edit\//);
  if (match !== null) {
    return { _identifier: match[1] };
  }
  return { _identifier: null };
}

const editCodebase = new EditCodebase({
  propsData: extractUrlParams(window.location.pathname),
}).$mount("#app");
