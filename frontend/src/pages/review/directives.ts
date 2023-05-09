import _ from "lodash-es";

export const holder = {
  update(el, binding) {
    if (!binding.expression) {
      throw new Error("holder directive must have a value");
    }
    if (_.isNull(binding.value)) {
      el.setAttribute("src", undefined);
      el.setAttribute("data-src", "holder.js/80x80?text=No submitted image");
      Holder.run({
        images: el,
      });
    } else {
      el.setAttribute("src", binding.value);
    }
  },
};
