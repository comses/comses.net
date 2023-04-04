import { mount } from "@vue/test-utils";
import HelloWorld from "@/components/HelloWorld.vue";

describe("HelloWorld", () => {
  expect(HelloWorld).toBeTruthy();
  const wrapper = mount(HelloWorld);

  test("correctly mounts", async () => {
    expect(wrapper).toBeTruthy();
    expect(wrapper.get("h1").text()).toBe("Vue 3 Component");
  });

  test("click increment button", async () => {
    expect(HelloWorld).toBeTruthy();
    const wrapper = mount(HelloWorld);
    await wrapper.get("button").trigger("click");
    expect(wrapper.get("p").text()).toContain("count: 1");
  });
});
