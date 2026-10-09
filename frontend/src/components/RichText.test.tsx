import { render, screen } from "@testing-library/react";
import { RichText } from "./RichText";

describe("RichText", () => {
  it("shows text between backticks as code", () => {
    render(<p>{<RichText>{"Use `const` instead of `var` here."}</RichText>}</p>);
    expect(screen.getByText("const").tagName).toBe("CODE");
    expect(screen.getByText("var").tagName).toBe("CODE");
    expect(screen.getByRole("paragraph")).toHaveTextContent("Use const instead of var here.");
  });

  it("leaves plain text alone", () => {
    render(<p>{<RichText>{"Nothing special."}</RichText>}</p>);
    expect(screen.getByRole("paragraph").querySelector("code")).toBeNull();
  });

  it("leaves text with an unmatched backtick alone", () => {
    render(<p>{<RichText>{"It costs 5` and more"}</RichText>}</p>);
    expect(screen.getByRole("paragraph")).toHaveTextContent("It costs 5` and more");
    expect(screen.getByRole("paragraph").querySelector("code")).toBeNull();
  });

  it("never turns markup into elements", () => {
    render(<p>{<RichText>{"<img src=x onerror=alert(1)> and `<b>`"}</RichText>}</p>);
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("b")).toBeNull();
    expect(screen.getByRole("paragraph")).toHaveTextContent("<img src=x onerror=alert(1)> and <b>");
  });
});
