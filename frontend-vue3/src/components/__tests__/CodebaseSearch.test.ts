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

    const TextField = wrapper.findComponent(TextField);
    expect(TextField.exists()).toBe(true);

    const anyDatePicker = wrapper.findComponent(DatepickerField);
    expect(anyDatePicker.exists()).toBe(true);

    const TaggerField = wrapper.findComponent(TaggerField);
    expect(TaggerField.exists()).toBe(true);

    const SelectField = wrapper.findComponent(SelectField);
    expect(SelectField.exists()).toBe(true);
    expect(SelectField.props("options").length).toEqual(3);
  });

  it("updates the query computed value based on form inputs", async () => {
    const wrapper = mount(CodebaseListSidebar);

    const TextField = wrapper.findComponent(TextField);
    const TextFieldElement = TextField.find("input");
    TextFieldElement.element.value = "test keyword";
    await TextFieldElement.trigger("input");
    await wrapper.vm.$nextTick();
    const baseSearch = wrapper.findComponent(ListSidebar);
    const searchUrl = baseSearch.props("searchUrl");
    expect(searchUrl).toContain("query=test%20keyword");
  });
});
