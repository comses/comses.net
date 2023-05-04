import { mount } from "@vue/test-utils";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import ListSidebar from "@/components/ListSidebar.vue";
import TextField from "@/components/form/TextField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import SelectField from "@/components/form/SelectField.vue";

describe("CodebaseListSidebar.vue", () => {
  it("renders the form field components", async () => {
    const wrapper = mount(CodebaseListSidebar);

    const baseSearch = wrapper.findComponent(ListSidebar);
    expect(baseSearch.exists()).toBe(true);

    const textField = wrapper.findComponent(TextField);
    expect(textField.exists()).toBe(true);

    const anyDatePicker = wrapper.findComponent(DatepickerField);
    expect(anyDatePicker.exists()).toBe(true);

    const taggerField = wrapper.findComponent(TaggerField);
    expect(taggerField.exists()).toBe(true);

    const selectField = wrapper.findComponent(SelectField);
    expect(selectField.exists()).toBe(true);
    expect(selectField.props("options").length).toEqual(3);
  });

  it("updates the query computed value based on form inputs", async () => {
    const wrapper = mount(CodebaseListSidebar);

    const textField = wrapper.findComponent(TextField);
    const textFieldElement = textField.find("input");
    textFieldElement.element.value = "test keyword";
    await textFieldElement.trigger("input");
    await wrapper.vm.$nextTick();
    const baseSearch = wrapper.findComponent(ListSidebar);
    const searchUrl = baseSearch.props("searchUrl");
    expect(searchUrl).toContain("query=test%20keyword");
  });
});
