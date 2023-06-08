type ExtractedAttributes = {
  [key: string]: string | object;
};

export function extractDataParams(elementId: string, names: string[]): ExtractedAttributes {
  /**
   * Extract parameters from data attributes
   *
   * @param elementId The id of the element
   * @param names The names of the attributes to extract and return (camelCase)
   */
  const el = document.getElementById(elementId);
  if (el) {
    const attributes = names.reduce<ExtractedAttributes>((acc: any, name) => {
      const hyphenatedName = name.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
      const attrValue = el.getAttribute(`data-${hyphenatedName}`);

      if (attrValue) {
        try {
          const parsedValue = JSON.parse(attrValue);
          acc[name] = parsedValue;
        } catch (error) {
          if (attrValue === "False") {
            acc[name] = false;
          } else if (attrValue === "True") {
            acc[name] = true;
          } else {
            acc[name] = attrValue;
          }
        }
      }
      return acc;
    }, {});
    return attributes;
  } else {
    return {};
  }
}

export function parseDates(data: any, keys: string[]) {
  /**
   * Parse dates (with Date.parse) in data object
   * @param data The data object to parse
   * @param keys The keys of the data object to parse
   * @returns The data object with parsed dates
   */
  for (const key of keys) {
    const parsedDate = Date.parse(data[key]);
    if (!isNaN(parsedDate)) {
      data[key] = new Date(parsedDate);
    }
  }
}
