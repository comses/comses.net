import DownloadRequestFormModal from "@/components/codebase/DownloadRequestFormModal.vue";

const el = document.getElementById("download-request-form");
if (el) {
  const userData = JSON.parse(el.getAttribute("data-user-data"));
  const versionNumber = el.getAttribute("data-version-number");
  const identifier = el.getAttribute("data-identifier");
  new DownloadRequestFormModal({
    propsData: {
      identifier,
      versionNumber,
      userId: userData.id,
      userAffiliation: userData.affiliation,
      userIndustry: userData.industry,
      authenticatedUser: userData.authenticated,
    },
  }).$mount(el);
}
