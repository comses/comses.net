import type { AxiosResponse } from "axios";
import { useAxios, parseValidationError, getCookie, parseDates } from "@/composables/api/axios";

describe("detailUrl", () => {
  test("should create detail URL with ID and paths", () => {
    const { detailUrl } = useAxios("/example/");
    const result = detailUrl(42, ["comments", 3]);
    expect(result).toBe("/example/42/comments/3/");
  });

  test("should create detail URL with alternative base URL", () => {
    const { detailUrl } = useAxios("/example");
    const result = detailUrl(42, [], "/alternative");
    expect(result).toBe("/alternative/42/");
  });
});

describe("searchUrl", () => {
  test("should create search URL with query parameters", () => {
    const { searchUrl } = useAxios("/example");
    const result = searchUrl({ query: "something", page: 2 });
    expect(["/example?query=something&page=2", "/example?page=2&query=something"]).toContain(
      result
    );
  });

  test("should ignore empty (string) query parameters", () => {
    const { searchUrl } = useAxios("/example/");
    const result = searchUrl({ query: "", page: 0 });
    expect(result).toBe("/example/?page=0");
  });
});

describe("parseValidationError", () => {
  test("should parse validation error response", () => {
    const errorResponse = {
      data: {
        non_field_errors: ["Invalid email or password."],
        email: ["This field is required."],
        password: ["This field is required."],
      },
      status: 400,
      statusText: "Bad Request",
    };
    const result = parseValidationError(errorResponse as AxiosResponse);
    expect(result).toEqual([
      "Invalid email or password.",
      "email: This field is required.",
      "password: This field is required.",
    ]);
  });
});
describe("getCookie", () => {
  test("should get cookie value by name", () => {
    const cookieVal = "GS1.1.168327h_34U.4.0.ak8ej9x_jwdHU&.0.0.0";
    document.cookie = "name=test;";
    document.cookie = `session=${cookieVal};`;
    const name = getCookie("name");
    expect(name).toBe("test");
    const session = getCookie("session");
    expect(session).toBe(cookieVal);
  });

  test("should return an empty string if the cookie does not exist", () => {
    const result = getCookie("nonexistent");
    expect(result).toBe("");
  });
});

describe("parseDates", () => {
  test("should parse ISO date strings in an object", () => {
    const data = {
      createdAt: "2021-09-10T00:00:00Z",
      updatedAt: "2021-09-10T01:00:00Z",
      nested: {
        publishedAt: "2021-09-10T02:00:00Z",
      },
    };

    parseDates(data);

    expect(data.createdAt).toBeInstanceOf(Date);
    expect(data.updatedAt).toBeInstanceOf(Date);
    expect(data.nested.publishedAt).toBeInstanceOf(Date);
  });
});
