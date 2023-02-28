import "@/pages/sentry";
import EditProfile from "@/components/profile/Edit.vue";

function extractParams() {
  const el = document.getElementById("app");
  const _pk = el.getAttribute("data-user-pk");
  const connectionsUrl = el.getAttribute("data-connections-url");
  console.debug("returning " + _pk);
  return { _pk, connectionsUrl };
}
new EditProfile({ propsData: extractParams() }).$mount("#app");
